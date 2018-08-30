from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import Coalesce

from ics.models import *
from django.db.models import F, Count, Sum


# calculate costs for all the children of current task
def update_children(new_unit_cost, prev_unit_cost, updated_task, tasks, descendant_ingredients):
	print('UPDATE_CHILDREN')
	# calculate difference of unit costs
	unit_cost_diff = new_unit_cost - prev_unit_cost
	print('unit_cost_diff', unit_cost_diff)
	if unit_cost_diff == 0:
		return
	# iterate through each child of the updated task and propagate data
	for child in tasks[updated_task]['children']:
		if child is not None:
			child_prev_unit_cost, child_new_unit_cost = update_cost(updated_task, child, prev_unit_cost, new_unit_cost, tasks, descendant_ingredients)
			# call rec_cost() to depth-first propagate values to children of child task if it is present in tasks list
			if child in tasks:
				visited = {}  # handles tasks with circular dependencies
				rec_cost(child, child_prev_unit_cost, child_new_unit_cost, tasks, visited, descendant_ingredients)


# Iterate over each direct child in the order inputs were added, calculating how much worth they were given previously
# and how much worth they get now (post batch_size change). (These worths override update_cost's calculated worths.)
# Since we don't know if future children might return worth to the parent (ie batch_size decreases or input deleted)
# we begin the 'simulation' with parent.remaining_worth = parent.cost, and decrement as we go, recreating the order
# worth was originally assigned, but updating worth based on recent changes.
def update_children_after_batch_size_or_child_ingredient_amount_change(
				new_unit_cost,
				prev_unit_cost,
				parent_task,
				tasks,
				descendant_ingredients,
				parent_previous_batch_size,
				parent_new_batch_size,
				child_with_changed_ingredient_amount=None,
				previous_total_amount_of_ingredient_for_child=None,
				new_total_amount_of_ingredient_for_child=None,
				input_deleted=False,
				input_added=False,
				creating_task_of_changed_input=-1):

	parent = tasks[parent_task]
	parent_task_direct_children = parent['children']
	direct_children_in_input_order = get_direct_children_in_input_order(parent_task, parent_task_direct_children)

	is_changed_inputs_parent = parent_task == creating_task_of_changed_input
	an_input_was_added_from_this_parent = is_changed_inputs_parent and input_added
	an_input_was_deleted_from_this_parent = is_changed_inputs_parent and input_deleted
	print('****** NEW PARENT: %d ********' % parent_task)
	print('an_input_was_added_from_this_parent', an_input_was_added_from_this_parent, 'an_input_was_deleted_from_this_parent', an_input_was_deleted_from_this_parent)
	parent['remaining_worth'] = parent['cost']
	for direct_child in direct_children_in_input_order:
		print('____NEW DIRECT_CHILD: %d, PARENT: %d' % (direct_child, parent_task))
		is_a_deleted_input = child_is_a_deleted_input(direct_child, child_with_changed_ingredient_amount, input_deleted)
		is_a_new_input = child_is_a_new_input(direct_child, child_with_changed_ingredient_amount, input_added)
		adding_this_parent_as_input = is_a_new_input and an_input_was_added_from_this_parent
		deleting_this_parent_as_input = is_a_deleted_input and an_input_was_deleted_from_this_parent
		print('is_a_new_input', is_a_new_input, 'is_a_deleted_input', is_a_deleted_input)
		num_parents = {
			'previous': get_adjusted_num_parents(parent, direct_child, descendant_ingredients, is_a_new_input, is_a_deleted_input, previous=True),
			'now': get_adjusted_num_parents(parent, direct_child, descendant_ingredients, is_a_new_input, is_a_deleted_input),
		}

		previous_total_amount_of_ingredient = None
		new_total_amount_of_ingredient = None
		if direct_child == child_with_changed_ingredient_amount:
			# Helps handle input deletions/additions and ingredient amount changes.
			previous_total_amount_of_ingredient = previous_total_amount_of_ingredient_for_child
			new_total_amount_of_ingredient = new_total_amount_of_ingredient_for_child

		cost_previously, cost_now, parent_previous_batch_size, parent_new_batch_size = get_previous_and_new_cost_for_child(
			parent_task, direct_child, tasks, descendant_ingredients, parent_previous_batch_size, parent_new_batch_size,
			new_unit_cost, prev_unit_cost, previous_total_amount_of_ingredient, new_total_amount_of_ingredient, num_parents,
			deleting_this_parent_as_input, adding_this_parent_as_input
		)

		print('cost_previously', cost_previously, 'cost_now', cost_now, 'parent_previous_batch_size', parent_previous_batch_size,'parent_new_batch_size', parent_new_batch_size)
		parent['remaining_worth'] = float(parent['remaining_worth']) - cost_previously

		child_prev_unit_cost, child_new_unit_cost = update_cost(parent_task, direct_child, prev_unit_cost, new_unit_cost, tasks, descendant_ingredients, cost_previously=cost_previously, cost_now=cost_now, input_deleted=input_deleted)

		if direct_child in tasks:
			print('recurse with:', direct_child)
			visited = {}  # handles tasks with circular dependencies
			rec_cost(direct_child, child_prev_unit_cost, child_new_unit_cost, tasks, visited, descendant_ingredients)


def get_adjusted_num_parents(parent_obj, child_id, descendant_ingredients, is_a_new_input=False, is_a_deleted_input=False, previous=False):
	process_type = parent_obj['process_type']
	product_type = parent_obj['product_type']
	task_ing_map = descendant_ingredients[child_id]['task_ing_map']
	num_parents = len(task_ing_map[(process_type, product_type)]['parent_tasks'])
	print('nOT adjusted NUM_PARENTS:', num_parents)
	if is_a_deleted_input:  # Delete input is calculated pre_delete, where all parents still exist.
		adjusted_num_parents = num_parents if previous else num_parents - 1
	elif is_a_new_input:  # New input is calculated post_save, where all parents exist.
		adjusted_num_parents = num_parents - 1 if previous else num_parents
	else:
		adjusted_num_parents = num_parents
	print('num parents:', adjusted_num_parents if adjusted_num_parents > 0 else 1)
	return adjusted_num_parents if adjusted_num_parents > 0 else 1


def child_is_a_deleted_input(direct_child, child_with_changed_ingredient_amount, input_deleted):
	return direct_child == child_with_changed_ingredient_amount and input_deleted


def child_is_a_new_input(direct_child, child_with_changed_ingredient_amount, input_added):
	return direct_child == child_with_changed_ingredient_amount and input_added


# Takes into account the fact that the child can only receive up to the amount the parent has remaining
# in its batch_size (that is, not already used by earlier inputs).
def get_previous_and_new_cost_for_child(updated_task, direct_child, tasks, descendant_ingredients, parent_previous_batch_size, parent_new_batch_size, new_unit_cost, prev_unit_cost, previous_total_amount_of_ingredient, new_total_amount_of_ingredient, num_parents, deleting_this_parent_as_input, adding_this_parent_as_input):
	# Calculate new/previous amount used by child
	previous_actual_amount_used_by_child = get_actual_amount_used_by_child(updated_task, direct_child, tasks, descendant_ingredients, parent_previous_batch_size, num_parents['previous'], previous_total_amount_of_ingredient)
	new_actual_amount_used_by_child = get_actual_amount_used_by_child(updated_task, direct_child, tasks, descendant_ingredients, parent_new_batch_size, num_parents['now'], new_total_amount_of_ingredient)

	if deleting_this_parent_as_input:
		new_actual_amount_used_by_child = 0
	elif adding_this_parent_as_input:
		previous_actual_amount_used_by_child = 0

	parent_previous_batch_size -= previous_actual_amount_used_by_child
	parent_new_batch_size -= new_actual_amount_used_by_child

	# Calculate new/previous costs, subtracting previous_cost from parents so update_cost knows how much worth
	# remains in the parent which can be assigned to this child.
	cost_previously = prev_unit_cost * previous_actual_amount_used_by_child
	cost_now = new_unit_cost * new_actual_amount_used_by_child
	return cost_previously, cost_now, parent_previous_batch_size, parent_new_batch_size


def get_actual_amount_used_by_child(updated_task, direct_child, tasks, descendant_ingredients, parent_remaining_batch_size, num_parents_for_ingredient, total_amount_of_ingredient=None):
	child_desired_ingredient_amount = get_child_desired_ingredient_amount(updated_task, direct_child, tasks, descendant_ingredients, num_parents_for_ingredient, total_amount_of_ingredient)
	print(direct_child, 'parent_remaining_batch_size, child_desired_ingredient_amount')
	print(parent_remaining_batch_size, child_desired_ingredient_amount)
	return float(min(parent_remaining_batch_size, child_desired_ingredient_amount))


def get_child_desired_ingredient_amount(parent, child, tasks, descendant_ingredients, num_parents_for_ingredient, total_amount_of_ingredient=None):
	process_type = tasks[parent]['process_type']
	product_type = tasks[parent]['product_type']
	task_ing_map = descendant_ingredients[child]['task_ing_map']
	# For Ingredient Amount change or input change we need to specify previous/new ingredient amount
	total_amount_of_ingredient = total_amount_of_ingredient or task_ing_map[(process_type, product_type)]['amount']
	return float(total_amount_of_ingredient / num_parents_for_ingredient)


def get_direct_children_in_input_order(parent, direct_children):
	return Input.objects.filter(input_item__creating_task=parent, task__in=direct_children).order_by('id').values_list('task', flat=True)


# Make-shift solution: we're unable to filter out rashed tasks in Array Aggs, so we just have to skip em
def task_is_trashed(task, maps_of_non_trashed_tasks):
	for map in maps_of_non_trashed_tasks:
		if task not in map:
			return True
	return False


# updates cost and remaining worth of tasks and returns new_difference which will be passed to child task
def update_cost(parent, child, prev_unit_cost, new_unit_cost, tasks, descendant_ingredients, cost_previously=None, cost_now=None, input_deleted=False):
	parent_obj = tasks[parent]
	parent_remaining_worth = parent_obj['remaining_worth']

	if cost_now is None and cost_previously is None:
		num_parents = get_adjusted_num_parents(parent_obj, child, descendant_ingredients)
		amount_used_by_child = get_child_desired_ingredient_amount(parent, child, tasks, descendant_ingredients, num_parents)
		cost_previously = prev_unit_cost * amount_used_by_child
		cost_now = new_unit_cost * amount_used_by_child

	change_in_worth_child_uses = float(cost_now - cost_previously)
	print ('_______ UPDATING CHILD: %d ________' % child)
	print('change_in_worth_child_uses', change_in_worth_child_uses, 'parent_remaining_worth', parent_remaining_worth)
	print('cost_now', cost_now, 'cost-previously', cost_previously)
	update_cost_and_remaining_worth_of_child(child, tasks, change_in_worth_child_uses, parent_remaining_worth)
	update_remaining_worth_of_parent(parent, tasks, change_in_worth_child_uses)
	return get_prev_and_new_unit_costs_for_child(tasks[child], change_in_worth_child_uses)


def get_prev_and_new_unit_costs_for_child(child, change_in_worth_child_uses):
	cost = child['cost']
	batch_size = child['batch_size']
	prev_unit_cost = get_unit_cost(cost - change_in_worth_child_uses, batch_size)
	new_unit_cost = get_unit_cost(cost, batch_size)
	return prev_unit_cost, new_unit_cost


def parent_has_capacity_to_receive_returned_value(change_in_amount_child_uses, parent_remaining_worth, parent_cost):
	return parent_remaining_worth - parent_cost >= change_in_amount_child_uses


def update_cost_and_remaining_worth_of_child(child, tasks, new_difference, parent_remaining_worth):
	new_difference = new_difference if new_difference <= parent_remaining_worth else parent_remaining_worth
	tasks[child]['remaining_worth'] = add_dollar_values(tasks[child]['remaining_worth'], new_difference)
	tasks[child]['cost'] = add_dollar_values(tasks[child]['cost'], new_difference)
	Task.objects.filter(pk=child).update(cost=tasks[child]['cost'], remaining_worth=tasks[child]['remaining_worth'])


def update_remaining_worth_of_parent(task, tasks, new_difference):
	parent = tasks[task]
	cost = parent['cost']
	parent['remaining_worth'] = add_dollar_values(parent['remaining_worth'], -1 * new_difference, upper_limit=cost)
	Task.objects.filter(pk=task).update(remaining_worth=parent['remaining_worth'])


# Returns 0 if difference makes value negative
def add_dollar_values(curr_value, new_difference_to_add, upper_limit=None):
	print('curr_value', curr_value, 'new_difference_to_add', new_difference_to_add, 'upper_limit', upper_limit)
	new_dollar_value = float(curr_value or 0) + float(new_difference_to_add)
	result = zero_or_greater(new_dollar_value)
	if upper_limit is not None:
		result = result if result <= upper_limit else upper_limit
	return result


def zero_or_greater(number):
	return number if number >= 0 else 0


# function to recursively propagate data
def rec_cost(parent, prev_unit_cost, new_unit_cost, tasks, visited, descendant_ingredients):
	for child in tasks[parent]['children']:
		if child is not None and child not in visited:
			visited[child] = child
			prev_unit_cost, new_unit_cost = update_cost(parent, child, prev_unit_cost, new_unit_cost, tasks, descendant_ingredients)
			if child in tasks:
				rec_cost(child, prev_unit_cost, new_unit_cost, tasks, visited, descendant_ingredients)


# fetch parents and children for list of related tasks
def task_details(updated_task_descendants):
	# contains task ids of descendants and ids of parents of descendants
	related_tasks = set()
	for task in list(updated_task_descendants):
		related_tasks.add(task.id)
	# for each descendant get parent id
	parents = Task.objects.filter(is_trashed=False, pk__in=related_tasks).annotate(
		task_parent_ids=ArrayAgg('inputs__input_item__creating_task__id'))

	for parent in parents:
		related_tasks = related_tasks.union(parent.task_parent_ids)

	trashed_task_ids_set = get_trashed_task_ids_set()

	related_tasks_batch_size = Task.objects.filter(is_trashed=False, pk__in=related_tasks).annotate(
		batch_size=Coalesce(Sum('items__amount'), 0))
	related_tasks_with_parents_children = Task.objects.filter(is_trashed=False, pk__in=related_tasks).annotate(
		children_list=ArrayAgg('items__inputs__task'),
		task_parent_ids=ArrayAgg('inputs__input_item__creating_task__id'),
		ingredients=ArrayAgg('task_ingredients__ingredient'))
	tasks = {}
	for x in range(0, related_tasks_with_parents_children.count()):
		tasks[related_tasks_with_parents_children[x].id] = {
			'children': set(related_tasks_with_parents_children[x].children_list) - trashed_task_ids_set,
			'process_type': related_tasks_batch_size[x].process_type_id,
			'ingredients': set(related_tasks_with_parents_children[x].ingredients),
			'product_type': related_tasks_batch_size[x].product_type_id,
			'cost': related_tasks_batch_size[x].cost,
			'parents': set(related_tasks_with_parents_children[x].task_parent_ids) - trashed_task_ids_set,
			'remaining_worth': related_tasks_batch_size[x].remaining_worth,
			'batch_size': related_tasks_batch_size[x].batch_size
		}
	return tasks


#  Not a scalable solution, but even if we doubled our task count we'd likely still have only 3k deleted tasks
def get_trashed_task_ids_set():
	return set(Task.objects.filter(is_trashed=True).values_list('pk', flat=True))


# returns ingredient used by each descendant
def descendant_ingredient_details(updated_task_descendants, tasks):
	descendant_ingredients = {}
	# populate task_ing_map with taskingredients along with all the parents contributing that ingredient for each descendant
	for task in updated_task_descendants:
		key = task.id
		descendant_ingredients[key] = {}
		task_ing_map = {}
		for task_ing in tasks[key]['ingredients']:
			if task_ing is None:
				continue
			ingredient_details = TaskIngredient.objects.filter(task_id=key, ingredient_id=task_ing).values('actual_amount',
																						'ingredient__process_type', 'ingredient__product_type')[0]
			process_type = ingredient_details['ingredient__process_type']
			product_type = ingredient_details['ingredient__product_type']
			task_ing_map[(process_type, product_type)] = {'amount': ingredient_details['actual_amount'], 'parent_tasks': set()}

		for parent in tasks[key]['parents']:
			if task_is_trashed(parent, [tasks]):
				continue
			process_type = tasks[parent]['process_type']
			product_type = tasks[parent]['product_type']
			task_ing_map[(process_type, product_type)]['parent_tasks'].add(parent)
		descendant_ingredients[key]['task_ing_map'] = task_ing_map
	return descendant_ingredients


def get_non_trashed_descendants(task):
	return Task.descendants(task).filter(is_trashed=False)


# BATCH SIZE UPDATE HELPERS

def get_prev_and_new_unit_costs(task, kwargs):
	new_batch_size = task['batch_size']
	amount_diff = kwargs['new_amount'] - kwargs['previous_amount']
	old_batch_size = new_batch_size - amount_diff
	cost = task['cost']
	prev_unit_cost = get_unit_cost(cost, old_batch_size)
	new_unit_cost = get_unit_cost(cost, new_batch_size)
	print('prev_unit_cost, new_unit_cost')
	print(prev_unit_cost, new_unit_cost)
	return prev_unit_cost, new_unit_cost


def get_unit_cost(cost, batch_size):
	print('cost, batch_size')
	print(cost, batch_size)
	return float(cost) / float(batch_size)


# DELETED TASK HELPERS:

def update_children_of_deleted_task(deleted_task):
	return
	# # fetch all the descendants of deleted task
	# deleted_task_descendants = get_non_trashed_descendants(Task.objects.filter(pk=deleted_task)[0])
	# if not deleted_task_descendants:
	# 	print ("No descendents")
	# 	return
	# tasks = task_details(deleted_task_descendants)
	# descendant_ingredients = descendant_ingredient_details(deleted_task_descendants, tasks)
	# if tasks[deleted_task]['children'] != {None}:
	# 	batch_size = tasks[deleted_task]['batch_size']
	# 	cost = tasks[deleted_task]['cost']
	# 	prev_unit_cost = get_unit_cost(cost, batch_size)
	# 	new_unit_cost = 0
	# 	update_children(new_unit_cost, prev_unit_cost, deleted_task, tasks, descendant_ingredients)


def update_parents_of_deleted_task(updated_task_id):
	return
	# # get all the ids of ingredients used and parents who contribute those ingredients
	# qs = Task.objects.filter(is_trashed=False, pk=updated_task_id).annotate(
	# 	task_parent_ids=ArrayAgg('inputs__input_item__creating_task__id'),
	# 	ingredients=ArrayAgg('task_ingredients__ingredient')
	# )
	# if qs.count() != 1 or qs[0].ingredients == [None]:
	# 	return
	# updated_task = qs[0]
	# parent_ids = updated_task.task_parent_ids
	# updated_task_parents = Task.objects.filter(pk__in=set(parent_ids)).annotate(
	# 	batch_size=Coalesce(Sum('items__amount'), 0))
	#
	# if updated_task_parents.count() == 0:
	# 	return
	#
	# # map ingredients with parents
	# ingredients_to_parents_map = {}
	# print(updated_task.ingredients)
	# for ingredient_id in updated_task.ingredients:
	# 	ingredient = Ingredient.objects.get(pk=ingredient_id)
	# 	parents_contributing_ingredient = {}
	# 	for x in range(0, len(set(parent_ids))):
	# 		if updated_task_parents[x].process_type_id == ingredient.process_type_id and \
	# 						updated_task_parents[x].product_type_id == ingredient.product_type_id:
	# 			parents_contributing_ingredient[updated_task_parents[x].id] = updated_task_parents[x]
	# 	ingredients_to_parents_map[ingredient.id] = parents_contributing_ingredient
	#
	# # iterate over each ingredient
	# print(ingredients_to_parents_map)
	# for ingredient_id, parents_contributing_ingredient in ingredients_to_parents_map.iteritems():
	# 	old_amount = TaskIngredient.objects.filter(ingredient_id=ingredient_id).values('actual_amount')[0]['actual_amount']
	# 	new_amount = 0
	# 	num_parents = len(parents_contributing_ingredient)
	# 	update_parents_for_ingredient(parents_contributing_ingredient, old_amount, new_amount)


def update_parents_for_ingredient(updated_child, parents_contributing_ingredient, old_amount, new_amount, input_added=False, input_deleted=False, creating_task_of_changed_input=-1):
	for parent_tuple in parents_contributing_ingredient:
		parent_id = parent_tuple[0]
		parent_batch_size = parent_tuple[1]
		parent_cost = parent_tuple[2]
		if parent_cost is None:
			continue
		update_creating_task_and_all_its_children(
			updated_child,
			parent_id,
			float(parent_batch_size),
			previous_total_amount_of_ingredient_for_child=old_amount,
			new_total_amount_of_ingredient_for_child=new_amount,
			input_deleted=input_deleted,
			input_added=input_added,
			creating_task_of_changed_input=creating_task_of_changed_input,
		)


# UPDATE INPUT HELPERS

# This is nearly identical to async_action.py/ingredient_amount_update(...), except with special flags to handle
# special cases of introducing or exiting an input, since one is done post_save and the other pre_delete.
def handle_input_change_with_no_recipe(kwargs, updated_task_id):
	creating_task_of_changed_input_id = kwargs['creatingTaskID']
	input_added = kwargs['added']
	task_ingredient__actual_amount = kwargs['task_ingredient__actual_amount']
	process_type = kwargs['process_type']
	product_type = kwargs['product_type']
	creating_task_of_changed_input = get_creating_task_of_changed_input(creating_task_of_changed_input_id)

	if not creating_task_of_changed_input or creating_task_of_changed_input.cost is None:
		return

	# Adding inputs adds its batch size.
	# Deleting inputs subtracts its batch size. Note: can produce negative amounts in special cases, matching codebase.
	old_amount, new_amount = get_amounts(task_ingredient__actual_amount, creating_task_of_changed_input.batch_size, input_added)
	update_parents_for_ingredient_and_then_child(
		updated_task_id,
		old_amount,
		new_amount,
		process_type,
		product_type,
		creating_task_of_changed_input=creating_task_of_changed_input.id,
		input_added=input_added,
		input_deleted=not input_added,  # Function is only ever called with input add/delete
	)


def get_creating_task_of_changed_input(creating_task_of_changed_input_id):
	query_set = Task.objects.filter(is_trashed=False, pk=creating_task_of_changed_input_id).annotate(
		batch_size=Coalesce(Sum('items__amount'), 0))
	return False if query_set.count() == 0 else query_set[0]  # It's possible the parent is a deleted tasks.


def get_amounts(task_ingredient__actual_amount, creating_task_batch_size, input_added):
	print('input_added', input_added)
	if input_added:  # which happens post_save
		new_amount_of_ingredient = task_ingredient__actual_amount  # we've already updated TaskIngredient
		old_amount_of_ingredient = new_amount_of_ingredient - creating_task_batch_size  # New inputs add full batch_size
	else:  # Input Deleted, which happens pre_delete (so the TaskIngredient still exists)
		old_amount_of_ingredient = task_ingredient__actual_amount  # We've yet to update TaskIngredient
		new_amount_of_ingredient = old_amount_of_ingredient - creating_task_batch_size  # Deleting subtracts full batch_size
	return old_amount_of_ingredient, new_amount_of_ingredient


# Used on each parent contributing to an ingredient type. Basically a prep-er/wrapper function.
def update_creating_task_and_all_its_children(updated_task, creating_task_of_changed_input_id, creating_task_batch_size, previous_total_amount_of_ingredient_for_child, new_total_amount_of_ingredient_for_child, input_deleted, input_added, creating_task_of_changed_input=-1):
	updated_task_descendants = get_non_trashed_descendants(Task.objects.filter(pk=creating_task_of_changed_input_id)[0])
	tasks = task_details(updated_task_descendants)
	descendant_ingredients = descendant_ingredient_details(updated_task_descendants, tasks)
	cost = tasks[creating_task_of_changed_input_id]['cost']
	unit_cost = get_unit_cost(cost, creating_task_batch_size)

	update_children_after_batch_size_or_child_ingredient_amount_change(
			unit_cost,
			unit_cost,
			creating_task_of_changed_input_id,
			tasks,
			descendant_ingredients,
			creating_task_batch_size,
			creating_task_batch_size,
			child_with_changed_ingredient_amount=updated_task,
			previous_total_amount_of_ingredient_for_child=previous_total_amount_of_ingredient_for_child,
			new_total_amount_of_ingredient_for_child=new_total_amount_of_ingredient_for_child,
			input_deleted=input_deleted,
			input_added=input_added,
			creating_task_of_changed_input=creating_task_of_changed_input,
	)


def handle_input_change_with_recipe(kwargs, updated_task_id):
	print('Input change with recipe', kwargs['recipe'])


# UPDATE INGREDIENT HELPERS

def get_parents_contributing_ingredient(updated_task_id, process_type, product_type):
	parents_in_input_order = Input.objects.filter(
		task=updated_task_id,
		input_item__creating_task__process_type=process_type,
		input_item__creating_task__product_type=product_type
	) \
		.annotate(batch_size=Coalesce(Sum('input_item__creating_task__items__amount'), 0)) \
		.annotate(cost=F('input_item__creating_task__cost')) \
		.order_by('id').values_list('input_item__creating_task__id', 'batch_size', 'cost')

	return make_unique(parents_in_input_order)


def make_unique(my_list):
	new_list = []
	for item in my_list:
		if item not in new_list:
			new_list.append(item)
	return new_list


def update_parents_for_ingredient_and_then_child(updated_task_id, old_amount, new_amount, process_type, product_type, creating_task_of_changed_input=-1, input_added=False, input_deleted=False):
	parents_contributing_ingredient = get_parents_contributing_ingredient(updated_task_id, process_type, product_type)
	old_updated_task_cost = Task.objects.get(is_trashed=False, pk=updated_task_id).cost
	update_parents_for_ingredient(updated_task_id, parents_contributing_ingredient, old_amount, new_amount, input_added, input_deleted, creating_task_of_changed_input)

	update_children_after_amount_update(updated_task_id, old_updated_task_cost)


def remove_trashed_tasks(task_ids, trashed_task_ids_set):
	return list(set(task_ids) - trashed_task_ids_set)


def update_children_after_amount_update(updated_task_id, old_updated_task_cost):
	print('update_children_after_amount_update')
	updated_task_descendants = get_non_trashed_descendants(Task.objects.filter(pk=updated_task_id)[0])
	if updated_task_descendants.count() == 0:
		return
	tasks = task_details(updated_task_descendants)
	descendant_ingredients = descendant_ingredient_details(updated_task_descendants, tasks)

	updated_task = tasks[updated_task_id]
	batch_size = updated_task['batch_size']
	new_updated_task_cost = updated_task['cost']

	prev_unit_cost = get_unit_cost(old_updated_task_cost, batch_size)
	new_unit_cost = get_unit_cost(new_updated_task_cost, batch_size)

	update_children(new_unit_cost, prev_unit_cost, updated_task_id, tasks, descendant_ingredients)