from django.core.management.base import BaseCommand, CommandError
from ics.models import *
from django.db.models import Sum
from ics.v9.serializers import InventoryList2Serializer


class Command(BaseCommand):
	help = 'Adds an adjustment to any inventory value that was changed by the switch to TaskIngredients.'

	def handle(self, *args, **options):
		adjustment_count = {}

		for team in Team.objects.all():
			adjustment_count[team.name] = 0
			inventories = Item.active_objects.exclude(creating_task__process_type__code__in=['SH','D'])\
				.filter(team_inventory=team) \
				.values(
				'creating_task__process_type',
				'creating_task__process_type__name',
				'creating_task__process_type__unit',
				'creating_task__process_type__code',
				'creating_task__process_type__icon',
				'creating_task__product_type',
				'creating_task__product_type__name',
				'creating_task__product_type__code',
				'team_inventory'
			).annotate(
				total_amount=Sum('amount'),
			).order_by('creating_task__process_type__name', 'creating_task__product_type__name')

			ser = InventoryList2Serializer()
			for item_summary in inventories:
				old = ser.old_get_adjusted_amount(item_summary)
				new = ser.get_adjusted_amount(item_summary)
				if new != old:
					adjustment_count[team.name] += 1
					Adjustment.objects.create(
						userprofile=team.userprofiles.first(), #Should set to user with a generic name that won't be deleted
						process_type=ProcessType.objects.get(pk=item_summary['creating_task__process_type']),
						product_type=ProductType.objects.get(pk=item_summary['creating_task__product_type']),
						amount=old,
						explanation='This adjustment was auto-generated by Polymer during a software update.'
					)

		print 'Adjustments created per team'
		for w in sorted(adjustment_count, key=adjustment_count.get, reverse=True):
			print w, adjustment_count[w]

