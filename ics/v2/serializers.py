from rest_framework import serializers
from ics.models import *
from django.contrib.auth.models import User
from uuid import uuid4
from django.db.models import F, Sum, Max
from datetime import date, datetime, timedelta

easy_format = '%Y-%m-%d %H:%M'

class AttributeSerializer(serializers.ModelSerializer):
  class Meta:
    model = Attribute
    fields = ('id', 'process_type', 'name', 'rank', 'datatype')

class ProcessTypeSerializer(serializers.ModelSerializer):
  attributes = AttributeSerializer(source='getAllAttributes', read_only=True, many=True)
  created_by_name = serializers.CharField(source='created_by.username', read_only=True)
  team_created_by_name = serializers.CharField(source='team_created_by.name', read_only=True)
  icon = serializers.CharField(read_only=True)
  x = serializers.CharField(read_only=True)
  y = serializers.CharField(read_only=True)
  
  class Meta:
    model = ProcessType
    fields = ('id', 'name', 'code', 'icon', 'attributes', 'unit', 'x', 'y', 'created_by', 'output_desc', 'created_by_name', 'default_amount', 'team_created_by', 'team_created_by_name')

class ProcessTypePositionSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProcessType
    fields = ('id','x','y')


class ProductTypeSerializer(serializers.ModelSerializer):
  #last_used = serializers.SerializerMethodField(source='get_last_used', read_only=True)

  def get_last_used(self, product):
    if product.last_used is not None:
      return product.last_used.strftime(easy_format)
    else:
      return ""

  class Meta:
    model = ProductType
    fields = ('id', 'name', 'code', 'created_by', 'is_trashed', 'team_created_by')

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
  class Meta:
    model = Task
    fields = ('id', 'is_open', 'custom_display', 'is_trashed', 'is_flagged', 'display', 'process_type', 'created_at')

class BasicItemSerializer(serializers.ModelSerializer):
  is_used = serializers.CharField(read_only=True)

  class Meta:
    model = Item
    fields = ('id', 'item_qr', 'creating_task', 'inventory', 'is_used', 'amount', 'is_virtual', 'team_inventory')

# serializes all fields of task
class BasicTaskSerializer(serializers.ModelSerializer):
  display = serializers.CharField(source='*', read_only=True)
  items = BasicItemSerializer(many=True, read_only=True)

  class Meta:
    model = Task
    fields = ('id', 'process_type', 'product_type', 'label', 'is_open', 'is_flagged', 'created_at', 'updated_at', 'label_index', 'custom_display', 'is_trashed', 'display', 'items')

class NestedItemSerializer(serializers.ModelSerializer):
  creating_task = BasicTaskSerializer(many=False, read_only=True)
  #inventory = serializers.CharField(source='getInventory')

  class Meta:
    model = Item
    fields = ('id', 'item_qr', 'creating_task', 'inventory', 'amount', 'is_virtual', 'team_inventory')

class BasicInputSerializer(serializers.ModelSerializer):
  input_task_display = serializers.CharField(source='input_item.creating_task', read_only=True)
  input_task = serializers.CharField(source='input_item.creating_task.id', read_only=True)
  input_qr = serializers.CharField(source='input_item.item_qr', read_only=True)
  input_task_n = EditTaskSerializer(source='input_item.creating_task', read_only=True)

  class Meta:
    model = Input
    fields = ('id', 'input_item', 'task', 'input_task', 'input_task_display', 'input_qr', 'input_task_n')

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

# serializes all fields of the task, with nested items, inputs, and attributes
class NestedTaskSerializer(serializers.ModelSerializer):
  items = BasicItemSerializer(many=True)
  inputs = BasicInputSerializer(many=True, read_only=True)
  input_unit = serializers.CharField(read_only=True)
  #inputUnit = serializers.SerializerMethodField('getInputUnit')
  attribute_values = BasicTaskAttributeSerializer(read_only=True, many=True)
  product_type = ProductTypeSerializer(many=False, read_only=True)
  process_type = ProcessTypeSerializer(many=False, read_only=True)
  display = serializers.CharField(source='*')
  total_amount = serializers.CharField(read_only=True)

  def getInputUnit(self, task):
    input = task.inputs.first()
    if input is not None:
      return input.input_item.creating_task.process_type.unit
    else: 
      return ''

  def getItems(self, task):
    if self.context.get('team_inventory', None) is not None:
      return BasicItemSerializer(task.items.all().filter(input__isnull=True), many=True).data
    else:
      return BasicItemSerializer(task.items.all().annotate(is_used=F('input__task')), many=True).data

  class Meta:
    model = Task
    fields = (
      'id', 
      'total_amount', 
      'process_type', 
      'product_type', 
      'label', 
      'input_unit', 
      'is_open', 
      'is_flagged', 
      'created_at', 
      'updated_at', 
      'label_index', 
      'custom_display', 
      'items', 
      'inputs', 
      'attribute_values', 
      'display',
      'is_trashed'
    )


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
    return BasicItemSerializer(task.items.filter(input__isnull=True, team_inventory=task.team), many=True).data

  class Meta:
    model = Task
    fields = ('id', 'items', 'display')

class ActivityListSerializer(serializers.ModelSerializer):
  process_id=serializers.CharField(source='process_type', read_only=True)
  process_name=serializers.CharField(source='process_type__name', read_only=True)
  process_unit=serializers.CharField(source='process_type__unit', read_only=True)
  product_id=serializers.CharField(source='product_type', read_only=True)
  product_code=serializers.CharField(source='product_type__code', read_only=True)
  runs=serializers.CharField(read_only=True)
  outputs=serializers.CharField(read_only=True)
  flagged=serializers.CharField(read_only=True)

  class Meta:
    model=Task
    fields = ('runs', 'outputs', 'flagged', 'process_id', 'process_name', 'process_unit', 'product_id', 'product_code')

class ActivityListDetailSerializer(serializers.ModelSerializer):
  outputs=serializers.CharField(read_only=True)

  class Meta:
    model=Task
    fields = ('id', 'label', 'label_index', 'custom_display', 'outputs')


class BasicGoalSerializer(serializers.ModelSerializer):
  actual = serializers.SerializerMethodField(source='get_actual', read_only=True)
  process_name = serializers.CharField(source='process_type.name', read_only=True)
  process_unit = serializers.CharField(source='process_type.unit', read_only=True)
  product_code = serializers.CharField(source='product_type.code', read_only=True)

  def get_actual(self, goal):
    base = date.today()
    start = datetime.combine(base - timedelta(days=base.weekday()), datetime.min.time())
    end = datetime.combine(base + timedelta(days=1), datetime.min.time())

    return Item.objects.filter(
      creating_task__process_type=goal.process_type, 
      creating_task__product_type=goal.product_type,
      creating_task__is_trashed=False,
      creating_task__created_at__range=(start, end)
    ).count()

  class Meta:
    model = Goal
    fields = ('id', 'process_type', 'product_type', 'goal', 'actual', 'process_name', 'process_unit', 'product_code')

class UserProfileSerializer(serializers.ModelSerializer):
  username = serializers.CharField(source='user.username')
  password = serializers.CharField(source='user.password')
  team_name = serializers.CharField(source='team.name')
  team = serializers.CharField(read_only=True)

  def create(self, validated_data):
    print(validated_data)
    data = validated_data.get('user')
    user = User.objects.create(**data)
    user.set_password(data.get('password'))
    user.save()

    team_name = validated_data.get('team').get('name', '')
    account_type = validated_data.get('account_type', '')
    team = Team.objects.filter(name=team_name)[0]
    userprofile = UserProfile.objects.create(user=user, gauth_access_token="", gauth_refresh_token="", token_type="", team=team)
    return userprofile

  class Meta:
    model = UserProfile
    extra_kwargs = {'team_name': {'write_only': True}, 'account_type': {'write_only': True} }
    fields = ('username', 'password', 'team', 'account_type', 'team_name', )


class TeamSerializer(serializers.ModelSerializer):
  processes = ProcessTypeSerializer(many=True, read_only=True)
  products = ProductTypeSerializer(many=True, read_only=True)

  class Meta:
    model = Team
    fields = ('id', 'name', 'processes', 'products')

