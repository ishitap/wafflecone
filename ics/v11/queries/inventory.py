from ics.models import *
from django.db.models.functions import Coalesce
from django.db.models import Sum, Func, Case, When, Value, DecimalField
from ics.constants import BEGINNING_OF_TIME, END_OF_TIME


def inventory_amounts(process_type, product_type, start, end):
	if start is None:
		start = BEGINNING_OF_TIME

	if end is None:
		end = END_OF_TIME

	created_amount = Item.active_objects.filter(
		creating_task__process_type=process_type,
		creating_task__product_type=product_type,
		created_at__range=(start, end),
		creating_task__is_trashed=False
	) \
		.aggregate(amount=Coalesce(Sum('amount'), 0))['amount']

	used_amount = TaskIngredient.objects \
		.filter(ingredient__process_type=process_type,
	            ingredient__product_type=product_type,
	            task__created_at__range=(start, end),
	            task__is_trashed=False
	            ) \
		.aggregate(amount=Coalesce(Sum('actual_amount'), 0))['amount']

	return {
		'created_amount': created_amount,
		'used_amount': used_amount,
	}

def old_inventory_created_amount(items_query):
	return items_query.aggregate(amount=Sum('amount'))['amount'] or 0

def old_inventory_used_amount(items_query):
	fully_used_amount = (items_query.filter(inputs__isnull=False, inputs__amount__isnull=True).distinct().aggregate(amount=Sum('amount'))['amount'] or 0)
	partially_used_amount = (items_query.filter(inputs__isnull=False, inputs__amount__isnull=False).aggregate(amount=Sum('inputs__amount'))['amount'] or 0)
	return fully_used_amount + partially_used_amount

def get_adjusted_item_amount(process_type, product_type):
	start_time = None
	starting_amount = 0
	latest_adjustment = Adjustment.objects \
		.filter(process_type=process_type, product_type=product_type) \
		.order_by('-created_at').first()

	if latest_adjustment:
		start_time = latest_adjustment.created_at
		starting_amount = latest_adjustment.amount

	data = inventory_amounts(process_type, product_type, start_time, None)
	return starting_amount + data['created_amount'] - data['used_amount']

def get_adjusted_item_cost(process_type, product_type):
	cost = 0
	actual_amount = get_adjusted_item_amount(process_type, product_type)

	item = Item.objects \
		.filter(
			creating_task__is_trashed=False,
			creating_task__process_type=process_type,
			creating_task__product_type=product_type,
		).annotate(
			cost=Coalesce(F('creating_task__remaining_worth'), 0),
		).annotate(
			# Item amount plus all items' amounts that come after it
			# (most recent item will have the smallest cumulative_amount)
			cumulative_amount=Func(
				Sum('amount'),
				template='%(expressions)s OVER (ORDER BY %(order_by)s)',
				order_by='ics_item.created_at DESC'
			),
			# Cost of task plus all tasks that come after it
			# (most recent task will have the smallest cumulative_cost)
			cumulative_cost=Func(
				Sum('cost'),
				template='%(expressions)s OVER (ORDER BY %(order_by)s)',
				order_by='ics_item.created_at DESC'
			),
		).annotate(
			# Difference between the actual amount and the cumulative_amount
			amount_diff=actual_amount-F('cumulative_amount'),
		).annotate(
			amount_diff_abs=Func(F('amount_diff'), function='ABS'),
			gt_zero = Case(
				When(amount_diff__gt=0, then=Value(1)),
				default=Value(0),
				output_field=DecimalField()
			)
		# This order_by().first() will select the item whos cumulative_amount is closest to the actual amount
		# It will sort first by those whos amount_diff is negative and then by the amount_diff_abs that is closest to zero
		# Doing this will give us the most accurate cost estimate possible
		).order_by('gt_zero', 'amount_diff_abs').first()

	# cost_offset is what needs to be added to the item's cumulative_cost in order to account for the remaining inventory amount
	# if amount_diff is positive, then use the cumulative cost per unit rather than this individual item's cost per unit
	if item.amount_diff > 0:
		if item.cumulative_amount > 0:
			cumulative_cost_per_unit = item.cumulative_cost / item.cumulative_amount
		else:
			cumulative_cost_per_unit = 0
		cost_offset = item.amount_diff*cumulative_cost_per_unit
	else:
		if item.amount > 0:
			cost_per_unit = item.cost / item.amount
		else:
			cost_per_unit = 0
		cost_offset = item.amount_diff*cost_per_unit

	#total_cumulative_cost = item.cumulative_cost + item.cumulative_cost_offset
	total_cumulative_cost = item.cumulative_cost + cost_offset

	# Do not return negative costs when inventory has negative amounts
	if total_cumulative_cost < 0:
		return 0

	return total_cumulative_cost
	
