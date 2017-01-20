from rest_framework import serializers
from ics.models import *

class UserSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ('id', 'name')

class ProcessTypeSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProcessType
    fields = ('id', 'name', 'code', 'icon')


class ProductTypeSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProductType
    fields = ('id', 'name', 'code')

class BasicTaskSerializer(serializers.ModelSerializer):
  class Meta:
    model = Task
    fields = ('id', 'process_type', 'product_type', 'label', 'created_by', 'is_open', 'created_at', 'updated_at', 'label_index', 'custom_display')

class BasicItemSerializer(serializers.ModelSerializer):
  class Meta:
    model = Item
    fields = ('id', 'item_qr', 'creating_task')

class NestedItemSerializer(serializers.ModelSerializer):
  creating_task = BasicTaskSerializer(many=False, read_only=True)

  class Meta:
    model = Item
    fields = ('id', 'item_qr', 'creating_task')

class BasicInputSerializer(serializers.ModelSerializer):
  class Meta:
    model = Input
    fields = ('id', 'input_item', 'task')

class NestedInputSerializer(serializers.ModelSerializer):
  input_item = NestedItemSerializer(many=False, read_only=True)

  class Meta:
    model = Input
    fields = ('id', 'input_item', 'task')

class AttributeSerializer(serializers.ModelSerializer):
  class Meta:
    model = Attribute
    fields = ('id', 'process_type', 'name')

class BasicTaskAttributeSerializer(serializers.ModelSerializer):
  class Meta:
    model = TaskAttribute
    fields = ('id', 'attribute', 'task', 'value')

class NestedTaskAttributeSerializer(serializers.ModelSerializer):
  attribute = AttributeSerializer(many=False, read_only=True)

  class Meta:
    model = TaskAttribute
    fields = ('id', 'attribute', 'task', 'value')

class NestedTaskSerializer(serializers.ModelSerializer):
  items = BasicItemSerializer(source='getItems', read_only=True, many=True)
  inputs = BasicInputSerializer(source='getInputs', read_only=True, many=True)
  attributes = NestedTaskAttributeSerializer(source='getTaskAttributes', read_only=True, many=True)

  class Meta:
    model = Task
    fields = ('id', 'process_type', 'product_type', 'label', 'created_by', 'is_open', 'created_at', 'updated_at', 'label_index', 'custom_display', 'items', 'inputs', 'attributes')
