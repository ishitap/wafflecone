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
	update_task_descendents_flag_number(**kwargs)

	#Don't create duplicate alerts after updating task search field
	if 'update_fields' not in kwargs or not kwargs['update_fields'] or 'search' not in kwargs['update_fields']:
		check_flagged_tasks_alerts(**kwargs)



@receiver(pre_save, sender=Task)
def task_changed(sender, instance, **kwargs):
	print("pre_save called on Task")
	# if instance.is_trashed:
	# 	task_deleted_update_cost(instance)


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
	kwargs = { 'pk' : instance.id }
	check_flagged_tasks_alerts(**kwargs)
	check_goals_alerts(**kwargs)


@receiver(post_save, sender=Item)
def item_changed(sender, instance, **kwargs):
	previous_amount = instance.tracker.previous('amount')
	kwargs = { 'pk' : instance.creating_task.id, 'new_amount': instance.amount, 'previous_amount': previous_amount}
	check_goals_alerts(**kwargs)
	# updates costs of children when batch size changed
	batch_size_update(**kwargs)


@receiver(post_save, sender=Input)
def input_changed(sender, instance, **kwargs):
	kwargs = get_input_kwargs(instance, added=True)
	check_anomalous_inputs_alerts(**kwargs)
	input_update(**kwargs)


def pre_pre_delete_code_refactored_from_model(instance):
	# if an input's creating task is flagged, decrement the flags on the input's task and it's descendents when it's deleted
	if instance.input_item.creating_task.is_flagged or instance.input_item.creating_task.num_flagged_ancestors > 0:
		Task.objects.filter(id__in=[instance.task.id]).update(num_flagged_ancestors=F('num_flagged_ancestors') - 2)

	similar_inputs = Input.objects.filter(task=instance.task, \
	                                      input_item__creating_task__product_type=instance.input_item.creating_task.product_type, \
	                                      input_item__creating_task__process_type=instance.input_item.creating_task.process_type)
	task_ings = TaskIngredient.objects.filter(task=instance.task, \
	                                          ingredient__product_type=instance.input_item.creating_task.product_type, \
	                                          ingredient__process_type=instance.input_item.creating_task.process_type)
	task_ings_without_recipe = task_ings.filter(ingredient__recipe=None)
	task_ings_with_recipe = task_ings.exclude(ingredient__recipe=None)
	if similar_inputs.count() <= 1:
		# if the input is the only one left for a taskingredient without a recipe, delete the taskingredient
		if task_ings_without_recipe.count() > 0:
			if task_ings_without_recipe[0].ingredient:
				if not task_ings_without_recipe[0].ingredient.recipe:
					print('Weee, deleting TaskIngredients w/out a recipe: ')
					for ti in task_ings_without_recipe:
						print(ti.id)
					task_ings_without_recipe.delete()
		# if the input is the only one left for a taskingredient with a recipe, reset the actual_amount of the taskingredient to 0
		if task_ings_with_recipe.count > 0:
			task_ings_with_recipe.update(actual_amount=0)
	else:
		# if there are other inputs left for a taskingredient without a recipe, decrement the actual_amount by the removed item's amount
		task_ings_without_recipe.update(actual_amount=F('actual_amount') - instance.input_item.amount)


@receiver(pre_delete, sender=Input)
def input_deleted_pre_delete(sender, instance, **kwargs):
	kwargs2 = get_input_kwargs(instance)
	print('pre_delete', kwargs2)
	input_update(**kwargs2)

	pre_pre_delete_code_refactored_from_model(instance)
	kwargs = { 'pk' : instance.task.id }
	unflag_task_descendants(**kwargs)
	check_anomalous_inputs_alerts(**kwargs2)


# this signal only gets called once whereas all the others get called twice
@receiver(post_delete, sender=Input)
def input_deleted(sender, instance, **kwargs):
	kwargs = { 'pk' : instance.task.id }
	unflag_task_descendants(**kwargs)
	kwargs2 = get_input_kwargs(instance)
	check_anomalous_inputs_alerts(**kwargs2)


@receiver(post_save, sender=TaskIngredient)
def ingredient_updated(sender, instance, **kwargs):
	# get the previous value
	previous_amount = instance.tracker.previous('actual_amount')
	if instance.was_amount_changed:
		kwargs = {'taskID': instance.task.id, 'ingredientID': instance.ingredient_id,
				  'actual_amount': instance.actual_amount, 'task_ing_id': instance.id, 'previous_amount': previous_amount}
		ingredient_amount_update(**kwargs)
