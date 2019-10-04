from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.timezone import now
import uuid
from datetime import datetime
# Create your models here.

class Corporation(models.Model):
	name = models.CharField(max_length=512)
	device_limit = models.IntegerField(blank=True)
	expire_date = models.DateTimeField()

class Employee(models.Model):
	# kurumun calisanlari is_manager = mudur
	corp = models.ForeignKey(Corporation, on_delete=models.CASCADE)
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user") # OneToOne
	tc_no = models.CharField(max_length=11)
	dev_uuid = models.CharField(max_length=256, blank=True) # if user first connect from 1 device set otherwise return false
	# dev_uuid = models.UUIDField(default=uuid.uuid4) # if user first connect from 1 device set otherwise return false
	is_manager = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	last_location_lat = models.FloatField(default=0, blank=True)
	last_location_lon = models.FloatField(default=0, blank=True)
	is_busy = models.BooleanField(default=False)

class Customer(models.Model):
	# kurumun musterileri
	corp = models.ForeignKey(Corporation, on_delete=models.CASCADE, related_name="admin1")
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin")
	tc_no = models.CharField(max_length=11)
	facility = models.TextField(blank=True)
	limit = models.FloatField(default=0)
	facility_location_lat = models.FloatField(default=0, blank=True)
	facility_location_lon = models.FloatField(default=0, blank=True)
	dev_uuid = models.CharField(max_length=256, blank=True) # if user first connect from 1 device set otherwise return false
	payed = models.FloatField(default=0)
	unpayed = models.FloatField(default=0)

class CustomerDebtHistory(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_debt")
	payed_date = models.DateTimeField(auto_now=True)
	payed_amount = models.FloatField()

class CustomerFacilities(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_facility")
	facility_tag = models.CharField(max_length=256)
	facility_location_lat = models.FloatField(default=0, blank=True)
	facility_location_lon = models.FloatField(default=0, blank=True)

class Materials(models.Model):
	# kurumun malzemeleri
	corp = models.ForeignKey(Corporation, on_delete=models.CASCADE)
	material = models.CharField(max_length=256)
	price = models.FloatField(blank=True)
	created_date = models.DateTimeField(auto_now=True)

class CustomerIssue(models.Model):
	# musteri issue eklediginde 
	corp = models.ForeignKey(Corporation, on_delete=models.CASCADE)
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer")
	customer_fac = models.ForeignKey(CustomerFacilities, on_delete=models.CASCADE, related_name="custfacility")
	title = models.CharField(max_length=256)
	content = models.TextField(blank=True)
	date = models.DateTimeField(auto_now=True)
	issue_emergency = models.IntegerField(blank=True) # 1 = ACIL , 2 = COK ACIL, 0 = ACIL DEGIL
	is_done = models.BooleanField(default=False)
	is_attached = models.BooleanField(default=False)

class UsedMaterials(models.Model):
	# kullanilan malzemeler
	corp = models.ForeignKey(Corporation, on_delete=models.CASCADE)
	material = models.ForeignKey(Materials, on_delete=models.CASCADE)
	mat_name = models.CharField(max_length=256)
	mat_price = models.FloatField(blank=True)
	count = models.FloatField(blank=True)
	date = models.DateTimeField(auto_now=True)
	# payed = models.BooleanField(default=False)

class CorporationIssues(models.Model):
	# issue yu calisana atama
	corp = models.ForeignKey(Corporation, on_delete=models.CASCADE, related_name="corp")
	issue = models.ForeignKey(CustomerIssue, on_delete=models.CASCADE, related_name="issue")
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee")
	date = models.DateTimeField(auto_now=True)
	finish_date = models.DateTimeField(null=True)
	used_materials = models.ManyToManyField(UsedMaterials, blank=True)
	employee_refuse = models.BooleanField(default=False)
	refuse_description = models.CharField(max_length=1024, blank=True)