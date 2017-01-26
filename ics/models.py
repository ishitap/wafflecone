from __future__ import unicode_literals
from datetime import datetime  
from django.db import models

# Create your models here.

class User(models.Model):
  name = models.CharField(max_length=20)

  def __str__(self):
    return self.name


class ProcessType(models.Model):
  name = models.CharField(max_length=20)
  code = models.CharField(max_length=20)
  icon = models.CharField(max_length=50)

  def __str__(self):
    return self.name

  def getAllAttributes(self):
    return self.attribute_set.all()

class ProductType(models.Model):
  name = models.CharField(max_length=20)
  code = models.CharField(max_length=20)

  def __str__(self):
    return self.name

class Attribute(models.Model):
  process_type = models.ForeignKey(ProcessType, on_delete=models.CASCADE)
  name = models.CharField(max_length=20)
  rank = models.PositiveSmallIntegerField(default=0)

  def __str__(self):
    return self.name


class Task(models.Model):
  process_type = models.ForeignKey(ProcessType, on_delete=models.CASCADE)
  product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
  label = models.CharField(max_length=20, db_index=True)  
  label_index = models.PositiveSmallIntegerField(default=0, db_index=True)
  custom_display = models.CharField(max_length=25, blank=True)
  created_by = models.ForeignKey(User, on_delete=models.CASCADE)
  is_open = models.BooleanField(default=True)

  created_at = models.DateTimeField(auto_now_add=True, db_index=True)
  updated_at = models.DateTimeField(auto_now=True, db_index=True)

  def __str__(self):
    if self.custom_display:
      return self.custom_display
    elif self.label_index > 0:
      return "-".join([self.label, str(self.label_index)])
    else:
      return self.label



  def save(self, *args, **kwargs):
    self.setLabelAndDisplay()
    super(Task, self).save(*args, **kwargs)



  def setLabelAndDisplay(self):
    if self.pk is None:
      # get the num of tasks with the same name & made on the same date this year
      q = ( 
        Task.objects.filter(label=self.label)
          .filter(created_at__startswith=str(datetime.now().year))
          .order_by('-label_index')
        )
      numItems = len(q)

      # if there are other items with the same name, then actually get the highest label_index 
      # and set our label index to that + 1
      if numItems > 0:
        self.label_index = q[0].label_index + 1
        self.display = "-".join([self.label, str(self.label_index)])
      else:
        self.display = self.label

  def getAllItems(self):
    return self.item_set.all()

  def getInventoryItems(self):
    return self.item_set.filter(input__isnull=True)

  def getInputs(self):
    return self.input_set.all()

  def getAllAttributes(self):
    return Attribute.objects.all().filter(process_type=self.process_type)

  def getTaskAttributes(self):
    return self.taskattribute_set.all()

  # tree traversal - finds all the children of the node that this is called on
  # returns a set([<Task object>])
  def descendents(self):
    all_descendents = set([self.id])
    root_tasks = set([self])
    self.descendents_helper(all_descendents, root_tasks, 0)
    return Task.objects.filter(id__in=all_descendents)

  def descendents_helper(self, all_descendents, curr_level_tasks, depth):
    new_level_tasks = set()

    # get all the items from the current level tasks task 
    child_items = Item.objects.filter(creating_task__in=curr_level_tasks)

    # get all the tasks they were input into
    child_task_rel = Input.objects.filter(input_item__in=child_items).select_related()

    for input in child_task_rel:
      t = input.task
      if t.id not in all_descendents:
        new_level_tasks.add(input.task)
        all_descendents.add(input.task.id)

    if len(new_level_tasks) > 0:
      self.descendents_helper(all_descendents, new_level_tasks, depth+1)


  def ancestors(self):
    all_ancestors = set([self.id])
    curr_level_tasks = set([self])
    self.ancestors_helper(all_ancestors, curr_level_tasks, 0)
    return Task.objects.filter(id__in=all_ancestors)

  def ancestors_helper(self, all_ancestors, curr_level_tasks, depth):
    new_level_tasks = set()

    parent_tasks = Task.objects.filter(item__input__task__in=curr_level_tasks)

    for t in parent_tasks:
      if t.id not in all_ancestors:
        new_level_tasks.add(t)
        all_ancestors.add(t.id)

    if len(new_level_tasks) > 0:
      self.ancestors_helper(all_ancestors, new_level_tasks, depth+1)


class Item(models.Model):
  item_qr = models.CharField(max_length=100, unique=True)
  creating_task = models.ForeignKey(Task, on_delete=models.CASCADE)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return self.item_qr

class Input(models.Model):
  input_item = models.ForeignKey(Item, on_delete=models.CASCADE)
  task = models.ForeignKey(Task, on_delete=models.CASCADE)

#  def __str__(self):
#    return self.input_item

class TaskAttribute(models.Model):
  attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
  task = models.ForeignKey(Task, on_delete=models.CASCADE)
  value = models.CharField(max_length=50, blank=True)
  updated_at = models.DateTimeField(auto_now=True)


