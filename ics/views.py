from rest_framework import status
from rest_framework.response import Response
from ics.models import *
from ics.serializers import *
from rest_framework import generics
from django.shortcuts import get_object_or_404, render
import django_filters
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView
 

class TaskList(generics.ListCreateAPIView):
  queryset = Task.objects.all()
  serializer_class = NestedTaskSerializer
  filter_backends = (django_filters.rest_framework.DjangoFilterBackend,OrderingFilter,)
  filter_fields = ('label', 'is_open',)

class TaskDetail(generics.RetrieveUpdateDestroyAPIView):
  queryset = Task.objects.all()
  serializer_class = NestedTaskSerializer
  filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
  filter_fields = ('label', 'is_open',)

class ItemList(generics.ListAPIView):
  queryset = Item.objects.all()
  serializer_class = NestedItemSerializer
  filter_fields = ('item_qr', 'creating_task')

class ItemDetail(generics.RetrieveUpdateDestroyAPIView):
  queryset = Item.objects.all()
  serializer_class = NestedItemSerializer
  filter_fields = ('item_qr', 'creating_task')

class ProcessList(generics.ListCreateAPIView):
  queryset = ProcessType.objects.all()
  serializer_class = ProcessTypeSerializer

class ProductList(generics.ListCreateAPIView):
  queryset = ProductType.objects.all()
  serializer_class = ProductTypeSerializer

def index(request):
  return HttpResponse("Hello, world. You're at the ics index.")

