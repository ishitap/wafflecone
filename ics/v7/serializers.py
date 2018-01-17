from rest_framework import serializers
from ics.models import *
from django.contrib.auth.models import User
from uuid import uuid4
from django.db.models import F, Sum, Max
from datetime import date, datetime, timedelta
from model_utils import *
import re
import string
# from ics.v7.calculated_fields_serializers import TaskFormulaAttributeSerializer

easy_format = '%Y-%m-%d %H:%M'

class AttributeSerializer(serializers.ModelSerializer):
	rank = serializers.IntegerField(read_only=True)
	process_name = serializers.CharField(source='process_type.name', read_only=True)

	class Meta:
		model = Attribute
		fields = ('id', 'process_type', 'process_name', 'name', 'rank', 'datatype')

class ProcessTypeSerializer(serializers.ModelSerializer):
	attributes = AttributeSerializer(source='getAllAttributes', read_only=True, many=True)
	created_by_name = serializers.CharField(source='created_by.username', read_only=True)
	team_created_by_name = serializers.CharField(source='team_created_by.name', read_only=True)
	icon = serializers.CharField(read_only=True)
	x = serializers.CharField(read_only=True)
	y = serializers.CharField(read_only=True)
	
	class Meta:
		model = ProcessType
		fields = ('id', 'name', 'code', 'icon', 'attributes', 'unit', 'x', 'y', 'created_by', 'output_desc', 'created_by_name', 'default_amount', 'team_created_by', 'team_created_by_name', 'is_trashed')


class AttributeDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = Attribute
		fields = ('id', 'process_type', 'name', 'rank', 'datatype', 'is_trashed')
		read_only_fields = ('id', 'process_type', 'name', 'rank', 'datatype')


class ProcessTypePositionSerializer(serializers.ModelSerializer):
	class Meta:
		model = ProcessType
		fields = ('id','x','y')


class ProductTypeSerializer(serializers.ModelSerializer):
	#last_used = serializers.SerializerMethodField(source='get_last_used', read_only=True)
	# created_by_username = serializers.CharField(source='created_by.username', read_only=True)
	username = serializers.SerializerMethodField(source='get_username', read_only=True)


	def get_last_used(self, product):
		if product.last_used is not None:
			return product.last_used.strftime(easy_format)
		else:
			return ""

	def get_username(self, product):
		print(product.created_by)
		username = product.created_by.username
		return username.split("_",1)[1] 

	class Meta:
		model = ProductType
		fields = ('id', 'name', 'code', 'created_by', 'is_trashed', 'team_created_by', 'username', 'created_at')


class ProductTypeBasicSerializer(serializers.ModelSerializer):
	#last_used = serializers.SerializerMethodField(source='get_last_used', read_only=True)
	username = serializers.SerializerMethodField(source='get_username', read_only=True)

	def get_username(self, product):
		print(product.created_by)
		username = product.created_by.username
		return username.split("_",1)[1] 

	class Meta:
		model = ProductType
		fields = ('id', 'name', 'code', 'created_by', 'is_trashed', 'team_created_by', 'username', 'created_at')

class ProductCodeSerializer(serializers.ModelSerializer):
	class Meta:
		model=ProductType
		fields = ('code',)

class UserSerializer(serializers.ModelSerializer):
	processes = ProcessTypeSerializer(many=True, read_only=True)
	products = ProductTypeSerializer(many=True, read_only=True)
	class Meta:
		model = User
		fields = ('id', 'username', 'processes', 'products')

# serializes only post-editable fields of task
class EditTaskSerializer(serializers.ModelSerializer):
	#id = serializers.IntegerField(read_only=True)
	created_at = serializers.DateTimeField(read_only=True)
	display = serializers.CharField(source='*', read_only=True)
	process_type = serializers.IntegerField(source='process_type.id', read_only=True)
	product_type = serializers.IntegerField(source='product_type.id', read_only=True)
	class Meta:
		model = Task
		fields = ('id', 'is_open', 'custom_display', 'is_trashed', 'is_flagged', 'flag_update_time', 'display', 'process_type', 'product_type', 'created_at', 'search')

class BasicItemSerializer(serializers.ModelSerializer):
	is_used = serializers.CharField(read_only=True)

	class Meta:
		model = Item
		fields = ('id', 'item_qr', 'creating_task', 'inventory', 'is_used', 'amount', 'is_virtual', 'team_inventory')



def calculateFormula(formula, task_obj):
	filled_in_formula = formula
	dependent_attributes = re.findall(r'(?<=\{)\d*(?=\})', formula)
	dependent_attr_map = {}
	attribute_objects = Attribute.objects.filter(id__in=dependent_attributes)

	for attribute in attribute_objects:
		if(TaskAttribute.objects.filter(attribute=attribute, task=task_obj).count() > 0):
			dependent_task_attribute = TaskAttribute.objects.filter(attribute=attribute, task=task_obj).latest('updated_at')
			dependent_attr_map[attribute.id] = dependent_task_attribute.value

	if all(value != None for value in dependent_attr_map.values()):
		# fill in the formula with all the values
		for attr_id in dependent_attr_map:
			attr_id_str = "{" + str(attr_id) + "}"
			print(attr_id_str)
			print(dependent_attr_map[attr_id])
			filled_in_formula = string.replace(filled_in_formula, attr_id_str, dependent_attr_map[attr_id])
		print("*************************************")
		print(filled_in_formula)
		if(('{' in filled_in_formula) or ('}' in filled_in_formula)):
			return None
		new_predicted_value = eval(filled_in_formula)
		return new_predicted_value
	else:
		return None


# serializes all fields of task
class BasicTaskSerializer(serializers.ModelSerializer):
	display = serializers.CharField(source='*', read_only=True)
	items = BasicItemSerializer(many=True, read_only=True)

	class Meta:
		model = Task
		fields = ('id', 'process_type', 'product_type', 'label', 'is_open', 'is_flagged', 'flag_update_time', 'created_at', 'updated_at', 'label_index', 'custom_display', 'is_trashed', 'display', 'items')

	def create(self, validated_data):
		print(validated_data)
		task = Task.objects.create(**validated_data)
		formula_attrs = FormulaAttribute.objects.filter(product_type=task.product_type, attribute__process_type=task.process_type, is_trashed=False)
		for formula_attr in formula_attrs:
			predicted_val = calculateFormula(formula_attr.formula, task)
			if (predicted_val != None):
				TaskFormulaAttribute.objects.create(formula_attribute=formula_attr, task=task, predicted_value=predicted_val)
			else:
				TaskFormulaAttribute.objects.create(formula_attribute=formula_attr, task=task)
			print("creating..........")
		return task


class NestedItemSerializer(serializers.ModelSerializer):
	creating_task = BasicTaskSerializer(many=False, read_only=True)
	#inventory = serializers.CharField(source='getInventory')

	class Meta:
		model = Item
		fields = ('id', 'item_qr', 'creating_task', 'inventory', 'amount', 'is_virtual', 'team_inventory')
		read_only_fields = ('id', 'item_qr', 'creating_task', 'inventory', 'team_inventory')

class BasicInputSerializer(serializers.ModelSerializer):
	input_task_display = serializers.CharField(source='input_item.creating_task', read_only=True)
	input_task = serializers.CharField(source='input_item.creating_task.id', read_only=True)
	input_qr = serializers.CharField(source='input_item.item_qr', read_only=True)
	input_task_n = EditTaskSerializer(source='input_item.creating_task', read_only=True)
	input_item_virtual = serializers.BooleanField(source='input_item.is_virtual', read_only=True)
	input_item_amount = serializers.DecimalField(source='input_item.amount', read_only=True, max_digits=10, decimal_places=3)
	task_display = serializers.CharField(source='task', read_only=True)

	class Meta:
		model = Input
		fields = ('id', 'input_item', 'task', 'task_display', 'input_task', 'input_task_display', 'input_qr', 'input_task_n', 'input_item_virtual', 'input_item_amount')

class NestedInputSerializer(serializers.ModelSerializer):
	input_item = NestedItemSerializer(many=False, read_only=True)

	class Meta:
		model = Input
		fields = ('id', 'input_item', 'task')

class BasicTaskAttributeSerializer(serializers.ModelSerializer):
	att_name = serializers.CharField(source='attribute.name', read_only=True)
	datatype = serializers.CharField(source='attribute.datatype', read_only=True)
	
	class Meta:
		model = TaskAttribute
		fields = ('id', 'attribute', 'task', 'value', 'att_name', 'datatype')

class NestedTaskAttributeSerializer(serializers.ModelSerializer):
	attribute = AttributeSerializer(many=False, read_only=True)

	class Meta:
		model = TaskAttribute
		fields = ('id', 'attribute', 'task', 'value')


class RecommendedInputsSerializer(serializers.ModelSerializer):
	class Meta:
		model = RecommendedInputs
		fields = ('id', 'process_type', 'recommended_input')

class MovementItemSerializer(serializers.ModelSerializer):
	class Meta:
		model = MovementItem
		fields = ('id', 'item')

class NestedMovementItemSerializer(serializers.ModelSerializer):
	class Meta:
		model = MovementItem
		fields = ('id', 'item',)
		depth = 1

class MovementListSerializer(serializers.ModelSerializer):
	items = NestedMovementItemSerializer(many=True, read_only=True)
	origin = serializers.CharField(source='team_origin.name')
	destination = serializers.CharField(source='team_destination.name')
	team_origin = serializers.CharField(source='team_origin.name')
	team_destination = serializers.CharField(source='team_destination.name')

	class Meta:
		model = Movement
		fields = ('id', 'items', 'origin', 'status', 'destination', 'timestamp', 'notes', 'team_origin', 'team_destination')

class MovementCreateSerializer(serializers.ModelSerializer):
	items = MovementItemSerializer(many=True, read_only=False)
	group_qr = serializers.CharField(default='group_qr_gen')

	class Meta:
		model = Movement
		fields = ('id', 'status', 'destination', 'notes', 'deliverable', 'group_qr', 'origin', 'items', 'team_origin', 'team_destination')

	def create(self, validated_data):
		print(validated_data)
		items_data = validated_data.pop('items')
		movement = Movement.objects.create(**validated_data)
		for item in items_data:
			MovementItem.objects.create(movement=movement, **item)
		return movement

def group_qr_gen():
	return "dande.li/g/" + str(uuid4())

class MovementReceiveSerializer(serializers.ModelSerializer):
	class Meta:
		model = Movement
		fields = ('id', 'status', 'destination', 'team_destination')

class InventoryListSerializer(serializers.ModelSerializer):
	process_id=serializers.CharField(source='creating_task__process_type', read_only=True)
	process_code=serializers.CharField(source='creating_task__process_type__code', read_only=True)
	process_icon=serializers.CharField(source='creating_task__process_type__icon', read_only=True)
	output_desc=serializers.CharField(source='creating_task__process_type__output_desc', read_only=True)
	count=serializers.CharField(read_only=True)
	unit=serializers.CharField(source='creating_task__process_type__unit', read_only=True)
	team=serializers.CharField(source='creating_task__process_type__team_created_by__name', read_only=True)
	team_id=serializers.CharField(source='creating_task__process_type__team_created_by', read_only=True)
	product_code=serializers.CharField(source='creating_task__product_type__code', read_only=True)
	product_name=serializers.CharField(source='creating_task__product_type__name', read_only=True)
	oldest = serializers.CharField(read_only=True)
	class Meta:
		model = Item
		fields = ('oldest', 'process_id', 'count', 'output_desc', 'unit', 'team', 'team_id', 'product_name', 'product_code', 'process_code', 'process_icon')


class InventoryDetailSerializer(serializers.ModelSerializer):
	items = serializers.SerializerMethodField('getInventoryItems')
	display = serializers.CharField(source='*', read_only=True)

	def getInventoryItems(self, task):
		return BasicItemSerializer(task.items.filter(inputs__isnull=True, team_inventory=task.team), many=True).data

	class Meta:
		model = Task
		fields = ('id', 'items', 'display')

class ActivityListSerializer(serializers.ModelSerializer):
	process_id=serializers.CharField(source='process_type', read_only=True)
	process_name=serializers.CharField(source='process_type__name', read_only=True)
	process_code = serializers.CharField(source='process_type__code', read_only=True)
	process_unit=serializers.CharField(source='process_type__unit', read_only=True)
	product_id=serializers.CharField(source='product_type', read_only=True)
	product_code=serializers.CharField(source='product_type__code', read_only=True)
	runs=serializers.CharField(read_only=True)
	outputs=serializers.CharField(read_only=True)
	flagged=serializers.CharField(read_only=True)

	class Meta:
		model=Task
		fields = ('runs', 'outputs', 'flagged', 'process_id', 'process_name', 'process_unit', 'product_id', 'product_code', 'process_code')

class ActivityListDetailSerializer(serializers.ModelSerializer):
	outputs=serializers.CharField(read_only=True)

	class Meta:
		model=Task
		fields = ('id', 'label', 'label_index', 'custom_display', 'outputs')



## ONLY USED AS LOGINSERIALIZER ##
class UserDetailSerializer(serializers.ModelSerializer):
	team_name = serializers.CharField(source='userprofile.team.name')
	team = serializers.CharField(source='userprofile.team.id', read_only=True)
	account_type = serializers.CharField(source='userprofile.account_type', read_only=True)
	profile_id = serializers.CharField(source='userprofile.id')
	user_id = serializers.CharField(source='userprofile.user.id')
	has_gauth_token = serializers.SerializerMethodField('hasGauthToken')
	gauth_email = serializers.CharField(source='userprofile.gauth_email')
	email = serializers.CharField(source='userprofile.email')
	username_display = serializers.CharField(source='userprofile.get_username_display')
	send_emails = serializers.BooleanField(source='userprofile.send_emails')
	last_seen = serializers.DateTimeField(source='userprofile.last_seen')

	def hasGauthToken(self, user):
		return bool(user.userprofile.gauth_access_token)

	class Meta:
		model = User
		fields = ('user_id', 'profile_id', 'username', 'username_display', 'first_name', 'last_name', 'team', 'account_type', 'team_name', 'has_gauth_token', 'gauth_email', 'email', 'send_emails', 'last_seen')


class UserProfileEditSerializer(serializers.ModelSerializer):
	class Meta:
		model = UserProfile
		fields = ('id', 'account_type', 'send_emails', 'email')

class UserProfileSerializer(serializers.ModelSerializer):
	team_name = serializers.CharField(source='team.name', read_only=True)
	team = serializers.CharField(source='team.id', read_only=True)
	profile_id = serializers.CharField(source='id', read_only=True)
	user_id = serializers.CharField(source='user.id', read_only=True)
	username = serializers.CharField(source='user.username', read_only=True)
	username_display = serializers.CharField(source='get_username_display', read_only=True)
	first_name = serializers.CharField(source='user.first_name')
	last_name = serializers.CharField(source='user.last_name')

	class Meta:
		model = UserProfile
		fields = ('user_id', 'id', 'profile_id', 'username', 'username_display', 'first_name', 'last_name', 'team', 'account_type', 'team_name', 'gauth_access_token', 'gauth_email', 'email', 'send_emails', 'last_seen')

class UserProfileCreateSerializer(serializers.ModelSerializer):
	username = serializers.CharField(source='user.username')
	password = serializers.CharField(source='user.password')
	first_name = serializers.CharField(source='user.first_name')
	team_name = serializers.CharField(source='team.name', read_only=True)
	profile_id = serializers.CharField(source='id', read_only=True)
	username_display = serializers.CharField(source='get_username_display', read_only=True)

	def create(self, validated_data):
		team = validated_data['team']
		data = validated_data['user']
		long_username = data['username'] + '_' + team.name

		# create the user 
		user = User.objects.create(username=long_username, first_name=data['first_name'])
		user.set_password(data.get('password'))
		user.save()

		# create the userprofile
		account_type = validated_data.get('account_type', '')
		userprofile = UserProfile.objects.create(
			user=user, 
			gauth_access_token="", 
			gauth_refresh_token="", 
			token_type="", 
			team=team,
			account_type=account_type,
		)
		return userprofile

	class Meta:
		model = UserProfile
		extra_kwargs = {'account_type': {'write_only': True}, 'password': {'write_only': True}}
		fields = ('id', 'profile_id', 'username', 'password', 'first_name', 'team', 'account_type', 'team_name', 'gauth_email', 'email', 'username_display')


class TeamSerializer(serializers.ModelSerializer):
	processes = serializers.SerializerMethodField('getProcesses')
	products = serializers.SerializerMethodField('getProducts')
	users = UserProfileSerializer(source='userprofiles', many=True, read_only=True)


	def getProcesses(self, team):
		return ProcessTypeSerializer(team.processes.filter(is_trashed=False), many=True).data

	def getProducts(self, team):
		return ProductTypeSerializer(team.products.filter(is_trashed=False), many=True).data


	class Meta:
		model = Team
		fields = ('id', 'name', 'users', 'products', 'processes')



class BasicGoalSerializer(serializers.ModelSerializer):
	actual = serializers.SerializerMethodField(source='get_actual', read_only=True)
	process_name = serializers.CharField(source='process_type.name', read_only=True)
	process_unit = serializers.CharField(source='process_type.unit', read_only=True)
	product_code = serializers.SerializerMethodField('get_product_types')
	userprofile = UserProfileSerializer(many=False, read_only=True)

	def get_product_types(self, goal):
		return ProductTypeSerializer(ProductType.objects.filter(goal_product_types__goal=goal), many=True).data

	def get_actual(self, goal):
		base = date.today()
		start = datetime.combine(base - timedelta(days=base.weekday()), datetime.min.time())
		end = datetime.combine(base + timedelta(days=1), datetime.min.time())

		if goal.timerange == 'w':
			start = datetime.combine(base - timedelta(days=base.weekday()), datetime.min.time())
		elif goal.timerange == 'd':
			start = datetime.combine(base, datetime.min.time())
		elif goal.timerange == 'm':
			start = datetime.combine(base.replace(day=1), datetime.min.time())

		product_types = ProductType.objects.filter(goal_product_types__goal=goal)
		
		return Item.objects.filter(
			creating_task__process_type=goal.process_type, 
			creating_task__product_type__in=product_types,
			creating_task__is_trashed=False,
			creating_task__created_at__range=(start, end),
			is_virtual=False,
		).aggregate(amount_sum=Sum('amount'))['amount_sum']

	class Meta:
		model = Goal
		fields = ('id', 'all_product_types', 'process_type', 'product_type', 'goal', 'actual', 'process_name', 'process_unit', 'product_code', 'userprofile', 'timerange', 'rank', 'is_trashed', 'trashed_time')

class GoalCreateSerializer(serializers.ModelSerializer):
	process_name = serializers.CharField(source='process_type.name', read_only=True)
	process_unit = serializers.CharField(source='process_type.unit', read_only=True)
	product_code = serializers.SerializerMethodField('get_product_types')
	input_products = serializers.CharField(write_only=True, required=False)
	rank = serializers.IntegerField(read_only=True)
	all_product_types = serializers.BooleanField(read_only=True)

	def get_product_types(self, goal):
		return ProductTypeSerializer(ProductType.objects.filter(goal_product_types__goal=goal), many=True).data

	def create(self, validated_data):
		userprofile = validated_data.get('userprofile', '')
		inputprods = validated_data.get('input_products', '')
		goal_product_types = None

		goal = Goal.objects.create(
			userprofile=validated_data.get('userprofile', ''),
			process_type=validated_data.get('process_type', ''),
			goal=validated_data.get('goal', ''),
			timerange=validated_data.get('timerange', ''),
			all_product_types=(inputprods == "ALL")
		)

		# if we didn't mean to put all product types in this goal:
		if (inputprods and inputprods != "ALL"):
			goal_product_types = inputprods.strip().split(',')	

		# if we did mean to put all product types in this goal:	
		if not goal_product_types:
			team = UserProfile.objects.get(pk=userprofile.id).team
			goal_product_types_objects = ProductType.objects.filter(is_trashed=False, team_created_by=team)
			goal_product_types = []
			for gp in goal_product_types_objects:
				goal_product_types.append(gp.id)

		for gp in goal_product_types:
			GoalProductType.objects.create(product_type=ProductType.objects.get(pk=gp), goal=goal)
		return goal

	class Meta:
		model = Goal
		fields = ('id', 'all_product_types', 'process_type', 'input_products', 'goal', 'process_name', 'process_unit', 'product_code', 'userprofile', 'timerange', 'rank', 'is_trashed', 'trashed_time')
		extra_kwargs = {'input_products': {'write_only': True} }

class BasicAccountSerializer(serializers.ModelSerializer):
	created_at = serializers.DateTimeField(read_only=True)

	class Meta:
		model = Account
		fields = ('id', 'team', 'name', 'created_at',)

class BasicContactSerializer(serializers.ModelSerializer):
	created_at = serializers.DateTimeField(read_only=True)
	account = BasicAccountSerializer()

	class Meta:
		model = Contact
		fields = ('id', 'account', 'name', 'phone_number', 'email', 'shipping_addr', 'billing_addr', 'created_at',)

class EditContactSerializer(serializers.ModelSerializer):
	created_at = serializers.DateTimeField(read_only=True)

	class Meta:
		model = Contact
		fields = ('id', 'account', 'name', 'phone_number', 'email', 'shipping_addr', 'billing_addr', 'created_at',)

class BasicOrderSerializer(serializers.ModelSerializer):
	created_at = serializers.DateTimeField(read_only=True)
	ordered_by = BasicContactSerializer()

	class Meta:
		model = Order
		fields = ('id', 'status', 'ordered_by', 'created_at',)

class EditOrderSerializer(serializers.ModelSerializer):
	created_at = serializers.DateTimeField(read_only=True)

	class Meta:
		model = Order
		fields = ('id', 'status', 'ordered_by', 'created_at',)


def reorder(instance, validated_data, dataset):
	old_rank = instance.rank
	new_rank = validated_data.get('new_rank', instance.rank)
	if old_rank <= new_rank:
		values = range(old_rank+1, new_rank+1)
		attrs = dataset.filter(rank__in=values)
		attrs.update(rank=F('rank') - 1)
	else:
		values = range(new_rank, old_rank)
		attrs = dataset.filter(rank__in=values)
		attrs.update(rank=F('rank') + 1)
	instance.rank = new_rank
	instance.save()
	return instance


class ReorderAttributeSerializer(serializers.ModelSerializer):
	new_rank = serializers.IntegerField(write_only=True)

	def update(self, instance, validated_data):
		return reorder(
			instance, 
			validated_data, 
			Attribute.objects.filter(is_trashed=False, process_type=instance.process_type)
		)
		# old_rank = instance.rank
		# new_rank = validated_data.get('new_rank', instance.rank)
		# if old_rank <= new_rank:
		# 	values = range(old_rank+1, new_rank+1)
		# 	attrs = Attribute.objects.filter(is_trashed=False, process_type=instance.process_type, rank__in=values)
		# 	attrs.update(rank=F('rank') - 1)
		# else:
		# 	values = range(new_rank, old_rank)
		# 	attrs = Attribute.objects.filter(is_trashed=False, process_type=instance.process_type, rank__in=values)
		# 	attrs.update(rank=F('rank') + 1)
		# instance.rank = new_rank
		# instance.save()
		# return instance

	class Meta:
		model = Attribute
		fields = ('id', 'new_rank')
		extra_kwargs = {'new_rank': {'write_only': True} }

class ReorderGoalSerializer(serializers.ModelSerializer):
	new_rank = serializers.IntegerField(write_only=True)

	def update(self, instance, validated_data):
		return reorder(
			instance, 
			validated_data, 
			Goal.objects.filter(userprofile=instance.userprofile, timerange=instance.timerange)
		)

	class Meta:
		model = Goal
		fields = ('id', 'new_rank')
		extra_kwargs = {'new_rank': {'write_only': True} }


class AlertSerializer(serializers.ModelSerializer):
	created_at = serializers.DateTimeField(read_only=True)

	class Meta:
		model = Alert
		fields = ('id', 'alert_type', 'variable_content', 'is_displayed', 'userprofile', 'created_at')

class UpdateUserProfileLastSeenSerializer(serializers.ModelSerializer):
	team_name = serializers.CharField(source='team.name', read_only=True)
	team = serializers.CharField(source='team.id', read_only=True)
	profile_id = serializers.CharField(source='id', read_only=True)
	user_id = serializers.CharField(source='user.id', read_only=True)
	username = serializers.CharField(source='user.username', read_only=True)
	username_display = serializers.CharField(source='get_username_display', read_only=True)
	first_name = serializers.CharField(source='user.first_name', read_only=True)
	last_name = serializers.CharField(source='user.last_name', read_only=True)

	def update(self, instance, validated_data):
		instance.last_seen = datetime.now()
		instance.save()
		return instance

	class Meta:
		model = UserProfile
		fields = ('user_id', 'id', 'profile_id', 'username', 'username_display', 'first_name', 'last_name', 'team', 'account_type', 'team_name', 'gauth_access_token', 'gauth_email', 'email', 'send_emails', 'last_seen')


