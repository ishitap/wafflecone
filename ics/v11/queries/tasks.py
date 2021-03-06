from django.db.models import Case, DecimalField, F, OuterRef, Q, Subquery, Sum, Value, When
from django.contrib.postgres.search import SearchQuery
from ics.models import *
import datetime
import pytz
from rest_framework.exceptions import APIException


def filter_by_created_at_range(query_params, queryset):
	start = query_params.get('start', None)
	end = query_params.get('end', None)
	if start is not None and end is not None:
		dt = datetime.datetime
		start_date = pytz.utc.localize(dt.strptime(start, constants.DATE_FORMAT))
		end_date = pytz.utc.localize(dt.strptime(end, constants.DATE_FORMAT))
		return queryset.filter(created_at__range=(start_date, end_date))
	return queryset


def tasks(query_params):
	queryset = Task.objects.filter(is_trashed=False).order_by('process_type__x').annotate(
		total_amount=Sum(Case(
			When(items__is_virtual=True, then=Value(0)),
			default=F('items__amount'),
			output_field=DecimalField()
		))          
	  )

	# filter according to various parameters
	team = query_params.get('team', None)
	if team is not None:
		queryset = queryset.filter(process_type__team_created_by=team)

	pipe_delimited_task_ids_string = query_params.get('pipe_delimited_task_ids_string', '')  # ie '|id1|id2|...|idn|'
	task_ids = [int(task_id) for task_id in pipe_delimited_task_ids_string.split('|') if task_id]
	if task_ids:
		queryset = queryset.filter(pk__in=task_ids)

	label = query_params.get('label', None)
	dashboard = query_params.get('dashboard', None)
	if label is not None and dashboard is not None:
		queryset = queryset.filter(Q(keywords__icontains=label) | Q(search=SearchQuery(label)) | Q(label__istartswith=label) | Q(custom_display__istartswith=label))
	elif label is not None:
		queryset = queryset.filter(Q(label__istartswith=label) | Q(custom_display__istartswith=label))

	parent = query_params.get('parent', None)
	if parent is not None:
		# if you want it to raise an exception if there is a cycle instead, set the parameter to True
		queryset = Task.objects.get(pk=parent).descendants(breakIfCycle=False)
		if queryset == None:
			raise APIException("Descendants contains cycles. Could not calculate.")

	child = query_params.get('child', None)
	if child is not None:
		# if you want it to raise an exception if there is a cycle instead, set the parameter to True
		queryset = Task.objects.get(pk=child).ancestors(breakIfCycle=False)
		if queryset == None:
			raise APIException("Ancestors contains cycles. Could not calculate.")

	inv = query_params.get('team_inventory', None)
	if inv is not None:
		queryset = queryset.filter(items__isnull=False, items__inputs__isnull=True).distinct()

	processes = query_params.get('processes', None)
	if processes is not None:
		processes = processes.strip().split(',')
		queryset = queryset.filter(process_type__in=processes)

	products = query_params.get('products', None)
	if products is not None:
		products = products.strip().split(',')
		queryset = queryset.filter(product_type__in=products)

	flagged = query_params.get('flagged', None)
	if flagged and flagged.lower() == 'true':
		queryset = queryset.filter(is_flagged=True)

	queryset = filter_by_created_at_range(query_params, queryset)


	# make sure that we get at least one input unit and return it along with the task
	i = Input.objects.filter(task=OuterRef('id')).order_by('id')
	queryset = queryset.annotate(input_unit=Subquery(i.values('input_item__creating_task__process_type__unit')[:1]))
	return queryset \
		.select_related('process_type', 'product_type', 'process_type__created_by', 'product_type__created_by',
						'process_type__team_created_by', 'product_type__team_created_by', 'recipe') \
		.prefetch_related('process_type__attribute_set', 'attribute_values', 'attribute_values__attribute',
					'items', 'inputs', 'inputs__input_item',
					'inputs__input_item__creating_task', 'inputs__input_item__creating_task__process_type',
					'inputs__input_item__creating_task__product_type', 'task_ingredients',
					      'task_ingredients__ingredient')


def taskSearch(query_params):
	queryset = Task.objects.filter(is_trashed=False)

	team = query_params.get('team', None)
	if team is not None:
		queryset = queryset.filter(process_type__team_created_by=team)

	label = query_params.get('label', None)
	dashboard = query_params.get('dashboard', None)
	if label is not None and dashboard is not None:
		queryset = queryset.filter(Q(keywords__icontains=label))
	elif label is not None:
		query = SearchQuery(label)
		# queryset.annotate(rank=SearchRank(F('search'), query)).filter(search=query).order_by('-rank')
		queryset = queryset.filter(Q(search=query) | Q(label__istartswith=label) | Q(custom_display__istartswith=label))
		# queryset = queryset.filter(Q(label__istartswith=label) | Q(custom_display__istartswith=label) | Q(items__item_qr__icontains=label))
	return queryset\
		.select_related('process_type', 'product_type', 'process_type__created_by', 'product_type__created_by', 'process_type__team_created_by', 'product_type__team_created_by')\
		.prefetch_related('process_type__attribute_set', 'attribute_values', 'attribute_values__attribute', 'items', 'inputs', 'inputs__input_item', 'inputs__input_item__creating_task', 'inputs__input_item__creating_task__process_type', 'inputs__input_item__creating_task__product_type')\
		.order_by('-updated_at')


def simpleTaskSearch(query_params):
	queryset = Task.objects.filter(is_trashed=False)

	team = query_params.get('team', None)
	if team is not None:
		queryset = queryset.filter(process_type__team_created_by=team)

	tags = query_params.get('tags', None)
	if tags is not None:
		tag_names = tags.strip().split(',')
		queryset = queryset.filter(process_type__tags__name__in=tag_names) | \
		           queryset.filter(product_type__tags__name__in=tag_names)

	label = query_params.get('label', None)
	dashboard = query_params.get('dashboard', None)
	if label is not None and dashboard is not None:
		queryset = queryset.filter(Q(keywords__icontains=label))
	elif label is not None:
		query = SearchQuery(label)
		queryset = queryset.filter(Q(search=query) | Q(label__istartswith=label) | Q(custom_display__istartswith=label))
	return queryset\
		.order_by('-updated_at').select_related('process_type', 'product_type').prefetch_related('items')


def taskDetail():
	return Task.objects.filter(
		is_trashed=False
	).annotate(
		total_amount=Sum(Case(
			When(items__is_virtual=True, then=Value(0)),
			default=F('items__amount'),
			output_field=DecimalField()
		))
	).select_related('process_type', 'product_type', 'process_type__created_by', 'product_type__created_by') \
		.prefetch_related('attribute_values', 'attribute_values__attribute', 'items', 'inputs__input_item',
	                      'inputs__input_item__creating_task', 'inputs__input_item__creating_task__process_type',
	                      'inputs__input_item__creating_task__product_type')
