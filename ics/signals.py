from ics.models import *
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.db.models import Count, F
from django.dispatch import receiver
from ics.async_actions import *
from ics.alerts import *

@receiver(post_save, sender=ProcessType)
def processtype_changed(sender, instance, **kwargs):
	kwargs = { 'process_type__id' : instance.id }
	update_task_search_vector(**kwargs)

@receiver(post_save, sender=ProductType)
def producttype_changed(sender, instance, **kwargs):
	kwargs = { 'product_type__id' : instance.id }
	update_task_search_vector(**kwargs)

@receiver(post_save, sender=TaskAttribute)
def taskattribute_changed(sender, instance, **kwargs):
	kwargs = { 'pk' : instance.task.id }
	update_task_search_vector(**kwargs)


@receiver(post_save, sender=Task)
def task_changed(sender, instance, **kwargs):
	kwargs = { 'pk' : instance.id }
	handle_potential_flag_status_change(**kwargs)

	#Don't create duplicate alerts after updating task search field
	if 'update_fields' not in kwargs or not kwargs['update_fields'] or 'search' not in kwargs['update_fields']:
		check_flagged_tasks_alerts(**kwargs)
	# >>> Handle Deleted Task
	previously_was_trashed = instance.tracker.previous('is_trashed')
	if previously_was_trashed is None:
		return  # This is a newly created task, yet to be saved to the DB. There's no cost to update from it.

	task_was_trashed = instance.is_trashed and not previously_was_trashed
	if task_was_trashed:
		task_deleted_update_cost(instance.id)
		return
	# >>> Handle new cost_set_by_user for Task
	previous_cost = instance.tracker.previous('cost')
	if previous_cost == None:
		previous_cost = 0.000
	previous_cost_set_by_user = instance.tracker.previous('cost_set_by_user')
	new_cost_set_by_user = instance.cost_set_by_user
	# Verify that A) user actually changed cost and B) change in cost_set_by_user actually deviates from the previous cost
	user_changed_cost = new_cost_set_by_user != previous_cost_set_by_user and new_cost_set_by_user != previous_cost
	if user_changed_cost:
		task_cost_update(instance.id, float(previous_cost), float(new_cost_set_by_user))


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
	kwargs = { 'pk' : instance.id }
	check_flagged_tasks_alerts(**kwargs)
	check_goals_alerts(**kwargs)


@receiver(post_save, sender=Item)
def item_changed(sender, instance, **kwargs):
	kwargs2 = { 'pk': instance.creating_task.id }
	check_goals_alerts(**kwargs2)

	# No costs to update if amount hasn't changed.
	previous_amount = instance.tracker.previous('amount')
	new_amount = instance.amount
	if previous_amount == new_amount:
		return
	# Don't update costs twice on create and save
	if 'created' in kwargs and kwargs['created']:
		return
	kwargs3 = {'pk': instance.creating_task.id, 'change_in_item_amount': float(new_amount) - float(previous_amount)}
	batch_size_update(**kwargs3)


# Signal mysteriously gets called twice (typically)
@receiver(post_save, sender=Input)
def input_changed(sender, instance, created, **kwargs):
	update_task_ingredient_for_new_input(instance)
	kwargs = {'taskID': instance.task.id, 'creatingTaskID': instance.input_item.creating_task.id}
	check_anomalous_inputs_alerts(**kwargs)
	if created:
		kwargs2 = get_input_kwargs(instance, added=True)
		if kwargs2:
			input_update(**kwargs2)
			handle_flag_update_after_input_add(**kwargs2)


# NOTE: We manually call update_input async in the view when a user deletes an input, deleting the input at the end.
# For a deleted task, we already handle input-deletion cost updates via task_deleted_update_cost,
# so a call to input_update is not needed.
@receiver(pre_delete, sender=Input)
def input_deleted_pre_delete(sender, instance, **kwargs):
	kwargs2 = get_input_kwargs(instance)
	if kwargs2:
		update_task_ingredient_after_input_delete(instance)


# this signal only gets called once
@receiver(post_delete, sender=Input)
def input_deleted(sender, instance, **kwargs):
	kwargs1 = { 'taskID' : instance.task.id, 'creatingTaskID' : instance.input_item.creating_task.id}
	check_anomalous_inputs_alerts(**kwargs1)

	child_task_id = instance.task.id
	parent_task_id = instance.input_item.creating_task.id
	former_parent_task_flagged_ancestors_id_string = instance.input_item.creating_task.flagged_ancestors_id_string
	handle_flag_update_after_input_delete(child_task_id, parent_task_id, former_parent_task_flagged_ancestors_id_string)


@receiver(post_save, sender=TaskIngredient)
def ingredient_updated(sender, instance, **kwargs):
	# get the previous value
	previous_amount = instance.tracker.previous('actual_amount') and float(instance.tracker.previous('actual_amount'))
	if instance.was_amount_changed:
		kwargs = {'taskID': instance.task.id, 'process_type': instance.ingredient.process_type.id, 'product_type': instance.ingredient.product_type.id,
				  'actual_amount': float(instance.actual_amount), 'task_ing_id': instance.id, 'previous_amount': previous_amount}
		ingredient_amount_update(**kwargs)


# HELPER FUNCTIONS

# NOTE: This logic, identical to original implementation, can produce negative actual_amounts since it blindly subtracts
# the input_item's full amount, for example even if the ingredient amount for the ingredient has been reduced.
def update_task_ingredient_after_input_delete(instance, just_calculate_new_amount=False):
	similar_inputs = Input.objects.filter(task=instance.task, \
	                                      input_item__creating_task__product_type=instance.input_item.creating_task.product_type, \
	                                      input_item__creating_task__process_type=instance.input_item.creating_task.process_type)
	task_ings = get_task_ingredient_qs_for_input(instance)
	task_ings_without_recipe = task_ings.filter(ingredient__recipe=None)
	task_ings_with_recipe = task_ings.exclude(ingredient__recipe=None)
	if similar_inputs.count() <= 1:
		# if the input is the only one left for a taskingredient without a recipe, delete the taskingredient
		if task_ings_without_recipe.count() > 0:
			if task_ings_without_recipe[0].ingredient:
				if not task_ings_without_recipe[0].ingredient.recipe:
					return None if just_calculate_new_amount else task_ings_without_recipe.delete()
		# if the input is the only one left for a taskingredient with a recipe, reset the actual_amount of the taskingredient to 0
		if task_ings_with_recipe.count > 0:
			return 0 if just_calculate_new_amount else task_ings_with_recipe.update(actual_amount=0)
	else:
		# if there are other inputs left for a taskingredient without a recipe, decrement the actual_amount by the removed item's amount
		if just_calculate_new_amount:
			return task_ings_without_recipe[0].actual_amount - instance.input_item.amount
		else:
			task_ings_without_recipe.update(actual_amount=F('actual_amount') - instance.input_item.amount)


def get_task_ingredient_qs_for_input(input_object):
	return TaskIngredient.objects.filter(
		task=input_object.task,
		ingredient__product_type=input_object.input_item.creating_task.product_type,
		ingredient__process_type=input_object.input_item.creating_task.process_type
	)


def update_task_ingredient_for_new_input(new_input):
	input_creating_product = new_input.input_item.creating_task.product_type
	input_creating_process = new_input.input_item.creating_task.process_type
	matching_task_ings = TaskIngredient.objects.filter(task=new_input.task, ingredient__product_type=input_creating_product, ingredient__process_type=input_creating_process)
	if matching_task_ings.count() == 0:
		# if there isn't already a taskIngredient and ingredient for this input's creating task, then make a new one
		ing_query = Ingredient.objects.filter(product_type=input_creating_product, process_type=input_creating_process, recipe=None)
		if(ing_query.count() == 0):
			new_ing = Ingredient.objects.create(recipe=None, product_type=input_creating_product, process_type=input_creating_process, amount=0)
		else:
			new_ing = ing_query[0]
		TaskIngredient.objects.create(ingredient=new_ing, task=new_input.task, actual_amount=new_input.input_item.amount)
	else:
		# when creating an input, if there is already a corresponding task ingredient
		# if the task ingredient has a recipe, set the ingredient's actual_amount to its scaled_amount
		matching_task_ings.exclude(ingredient__recipe=None).update(actual_amount=F('scaled_amount'))
		# if the task ingredient doesn't have a recipe, add the new input's amount to the actual_amount
		matching_task_ings.filter(ingredient__recipe=None).update(actual_amount=F('actual_amount')+new_input.input_item.amount)


def source_and_target_of_input_are_not_trashed(instance):
	source_is_trashed = instance.input_item.creating_task.is_trashed
	target_is_trashed = instance.task.is_trashed
	return not (target_is_trashed or source_is_trashed)