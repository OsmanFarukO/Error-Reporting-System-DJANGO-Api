# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
Django Modules
"""
from django.contrib.auth.models import User
from django.shortcuts import *
from django.template import RequestContext
from django.http import *
from django.utils import timezone
from .models import *
from django.core.exceptions import ObjectDoesNotExist
from errordetection.settings import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
from django.db.models import Q, F
import pytz
import datetime
import itertools
from django.db.models import Count
from django.contrib.auth import authenticate, login
from django.core import serializers
"""
REST Api Modules
"""
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.views.mixins import OAuthLibMixin
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.models import get_access_token_model, AccessToken

from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes

from math import sin, cos, sqrt, atan2, radians
import json
from random import randint

def isEmployeeManager(uid):
    emp = Employee.objects.get(user_id=uid)
    if emp.is_manager:
        return True
    else:
        return False

def isCustomer(uid):
    try:
        cst = Customer.objects.get(user_id=uid)
        return True
    except ObjectDoesNotExist:
        return False

def getCorpId(uid):
    return Employee.objects.get(user_id=uid).corp_id

class AuthLogin(OAuthLibMixin, APIView):
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS
    authentication_classes = []
    permission_classes = []

    def post(self, request, format=None):
        url = None
        url, headers, body, status = self.create_token_response(request)
        if url != None:
            self._purge_tokens(request)
        if status == 200:
            access_token = json.loads(body).get("access_token")
            if access_token is not None:
                token = get_access_token_model().objects.get(
                    token=access_token)
            username = request.data.get('username', None)
            password = request.data.get('password', None)
            try:
                user_simple_auth = authenticate(username=username, password=password)
                login(request, user_simple_auth)
                usr = User.objects.get(username=username)
                if request.data["user_type"] == 0:
                    employee = Employee.objects.get(user_id=usr.id)
                    if employee.is_manager == 0:
                        status = 400
                elif request.data["user_type"] == 1:
                    employee = Employee.objects.get(user_id=usr.id)
                    if employee.is_manager == 1:
                        status = 400
                else:
                    cst = Customer.objects.get(user_id=usr.id)
                    devid = request.data.get('devid', None)
                    if cst.dev_uuid != devid:
                        cst.dev_uuid = devid
                        cst.save()
            except ObjectDoesNotExist:
                status = 400
        response = Response(body, status=status)
        for k, v in headers.items():
            response[k] = v
        return response

    def _purge_tokens(self, r):
        username = r.data.get('username', None)
        try:
            usr = User.objects.get(username=username)
            AccessToken.objects.filter(user_id=usr.id)[:-1].delete()
        except:
            pass

########## MANAGER CONTROL-PANEL APIs ##########

class MaterialOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        try:
            emp = Employee.objects.get(user_id=request.user.id)
            user_materials = Materials.objects.filter(corp_id=emp.corp_id)
            data = [{"material_name": mtr.material, "material_price": mtr.price, "material_created_date": mtr.created_date, "material_id": mtr.id, "value": mtr.material} for mtr in user_materials]
        except:
            data = []
        return Response(data, status=200)

    def put(self, request, format=None):
        if isEmployeeManager(request.user.id):
            try:
                Materials.objects.get(material=request.data['name'])
            except:
                emp = Employee.objects.get(user_id=request.user.id)
                mtr = Materials()
                mtr.material = request.data['name']
                mtr.price = request.data['price']
                mtr.corp_id = emp.corp_id
                mtr.save()
                return Response({'status':'true','message':'Created Successfully'}, status = 200)
            return Response({'status':'false','message':'Bad Request'}, status = 400)
        else:
            return Response(status=401)

    def delete(self, request, pk, format=None):
        if isEmployeeManager(request.user.id):
            try:
                mtr = Materials.objects.get(id=pk)
                mtr.delete()
            except Exception:
                return Response(status=400)
            return Response(status=200)
        else:
            return Response(status=401)

class AdminPanelStatistics(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        corp = getCorpId(request.user.id)

        cst_issues_dates = CustomerIssue.objects.filter(corp_id=corp).values('date').values('date').order_by('-date')
        group_byday = itertools.groupby(cst_issues_dates, lambda d: d.get('date').strftime('%m-%d'))
        cst_issue_count_day = [{"date": day, "count": len(list(this_day))} for day, this_day in group_byday]
        
        corp_issues_dates = CorporationIssues.objects.filter(Q(corp_id=corp) & ~Q(finish_date=None)).values('date').values('date').order_by('-date')
        grouped_byday = itertools.groupby(corp_issues_dates, lambda d: d.get('date').strftime('%m-%d'))
        attached_byday = [{"date": day, "count": len(list(this_day))} for day, this_day in grouped_byday]

        corp_dev_limit = Corporation.objects.get(id=corp).device_limit
        corporation_emps = Employee.objects.filter(corp_id=corp)
        corporation_customers = Customer.objects.filter(corp_id=corp)
        used_from_limit = len(corporation_emps) + len(corporation_customers)

        res = {
            "cst_issue_count_day": cst_issue_count_day,
            "attached_byday": attached_byday,
            "cst_count": self._customers_with_worth(corp),
            "materials_with_count": self._used_materials_with_count(corp),
            "emp_with_done": self._employees_with_done_jobs(corp),
            "deviceoptions": [corp_dev_limit ,used_from_limit]
        }
        return Response(res, status=200)

    def _customers_with_worth(self, corp):
        custs_count_obj = CustomerIssue.objects.filter(corp_id=corp).values('customer_id').annotate(total=Count('customer_id')).order_by()
        res = []
        for cst_c in custs_count_obj:
            cst = Customer.objects.get(id=cst_c["customer_id"])
            res.append({
                "username": cst.user.first_name + " " + cst.user.last_name,
                "count": cst_c["total"]
            })
        return res

    def _used_materials_with_count(self, corp):
        corporation_materials = Materials.objects.filter(corp_id=corp)
        res = []
        for mat in corporation_materials:
            mat.total = 0
            used = UsedMaterials.objects.filter(material_id=mat.id)
            for mt in used:
                mat.total += mt.count
            res.append({
                "mat_name": mat.material,
                "total": mat.total
            })
        return res

    def _employees_with_done_jobs(self, corp):
        corporation_employees = Employee.objects.filter(Q(corp_id=corp) & Q(is_manager=False))
        res = []
        for emp in corporation_employees:
            emp.done_jobs = 0
            jobs = CorporationIssues.objects.filter(Q(employee_id=emp.id) & ~Q(finish_date=None))
            emp.done_jobs += len(jobs)
            emp.full_name = emp.user.first_name + " " + emp.user.last_name
            res.append({
                "fullname": emp.full_name,
                "done_jobs": emp.done_jobs
            })
        return res

class EmployeeOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, format=None):
        manager_id = request.user.id
        if isEmployeeManager(manager_id):
            manager = Employee.objects.get(user_id=manager_id)
            corporation = Corporation.objects.get(id=manager.corp_id)
            corporation_emps = Employee.objects.filter(corp_id=manager.corp_id)
            corporation_customers = Customer.objects.filter(corp_id=manager.corp_id)
            if len(corporation_emps) + len(corporation_customers) + 1 > corporation.device_limit:
                status = 400
            else:
                new_uuid = self.generateUserID()
                user = User.objects.create_user(
                    username=str(new_uuid),
                    email=request.data["email"],
                    password=request.data["password"],
                    first_name=request.data["first_name"],
                    last_name=request.data["last_name"],
                )
                saved_user = User.objects.get(username=str(new_uuid), email=request.data["email"])
                emp = Employee()
                emp.corp_id = manager.corp_id
                emp.user_id = saved_user.id
                emp.tc_no = request.data["tc_no"]
                emp.save()
                status = 200
            return Response(status=status)
        else:
            return Response(status=401)

    def get(self, request, format=None):
        if isEmployeeManager(request.user.id):
            emp = Employee.objects.get(user_id=request.user.id)
            corp_emps = Employee.objects.filter(Q(corp_id=emp.corp_id) & ~Q(user_id=request.user.id))
            data = []
            if len(corp_emps) != 0:
                for employee in corp_emps:
                    userself = "Boşta"
                    content = ""
                    if employee.is_busy:
                        emp_job = CorporationIssues.objects.filter(Q(employee_id=employee.id) & Q(employee_refuse=False)).last()
                        cst_issue = CustomerIssue.objects.get(id=emp_job.issue_id)
                        cst = Customer.objects.get(id=cst_issue.customer_id)
                        usr = User.objects.get(id=cst.user_id)
                        content = cst_issue.title + " " + cst_issue.content
                        userself = usr.first_name + " " + usr.last_name + " müşterisinin " + content + " hata raporuyla meşgul"
                    data.append({
                        "emp_name": employee.user.username,
                        "emp_fname": employee.user.first_name,
                        "emp_lname": employee.user.last_name,
                        "emp_tc": employee.tc_no,
                        "emp_lat": employee.last_location_lat,
                        "emp_lon": employee.last_location_lon,
                        "emp_id": employee.id,
                        "emp_isbusy": employee.is_busy,
                        "emp_active": employee.is_active,
                        "emp_userself": userself,
                        "emp_content": content
                    })
            return Response(data, status=200)
        else:
            return Response(status=401)

    def delete(self, request, pk, format=None):
        if isEmployeeManager(request.user.id):
            try:
                emp = Employee.objects.get(id=pk)
                usr = User.objects.get(id=emp.user_id)
                usr.delete()
                emp.delete()
            except:
                return Response(status=400)
            return Response(status=200)
        else:
            return Response(status=401)

    def generateUserID(self):
        try:
            last_emp = Employee.objects.last().user_id
            last_customer = Customer.objects.last().user_id
            if last_emp >= last_customer:
                last_saved_fucked = last_emp
            else:
                last_saved_fucked = last_customer

            username = User.objects.get(id=last_saved_fucked).username
            try:
                int_userid = int(username)
                return int_userid + randint(100, 1000)
            except ValueError:
                return randint(100, 1000)
        except Exception:
            return randint(100, 1000)

class AdminUpdateEmployees(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        if isEmployeeManager(request.user.id):
            emp_list = request.data['emps']
            for emp in emp_list:
                emp_obj = Employee.objects.get(id=emp["emp_id"])
                emp_obj.is_active = emp["emp_active"]
                emp_obj.save()
            return Response(status=200)
        else:
            return Response(status=401)

class CustomerLimitOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, format=None):
        cst = Customer.objects.get(id=pk)
        cst.limit = request.data['_newlimit']
        cst.save()
        return Response(status=200)

class CustomerOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, format=None):
        manager_id = request.user.id
        if isEmployeeManager(manager_id):
            manager = Employee.objects.get(user_id=manager_id)
            corporation = Corporation.objects.get(id=manager.corp_id)
            corporation_customers = Customer.objects.filter(corp_id=manager.corp_id)
            corporation_employees = Employee.objects.filter(corp_id=manager.corp_id)
            if len(corporation_customers) + len(corporation_employees) + 1 > corporation.device_limit:
                status = 400
            else:
                new_user = self.generateUserID()
                user = User.objects.create_user(
                    username=str(new_user),
                    email=request.data["email"],
                    password=request.data["password"],
                    first_name=request.data["first_name"],
                    last_name=request.data["last_name"],
                )
                saved_user = User.objects.get(username=str(new_user), email=request.data["email"])
                cst = Customer()
                cst.corp_id = manager.corp_id
                cst.user_id = saved_user.id
                cst.tc_no = request.data["tc_no"]
                cst.facility = request.data["facility"]
                cst.limit = request.data["limit"]
                cst.facility_location_lat = 0
                cst.facility_location_lon = 0
                cst.save()
                status = 200
            return Response(status=status)
        else:
            return Response(status=401)

    def get(self, request, format=None):
        emp = Employee.objects.get(user_id=request.user.id)
        corp_customers = Customer.objects.filter(Q(corp_id=emp.corp_id))
        data = []
        if len(corp_customers) != 0:
            for cst in corp_customers:
                customer_locations = CustomerFacilities.objects.filter(customer_id=cst.id)
                """
                customer_issues = CustomerIssue.objects.filter(corp_id=emp.corp_id, customer_id=cst.id)
                payed = 0
                unpayed = 0
                for cst_iss in customer_issues:
                    try:
                        corp_iss = CorporationIssues.objects.get(issue_id=cst_iss.id)
                        all_used = corp_iss.used_materials.all()
                        _payed, _unpayed = self._materials_debt_calculate(all_used)
                        payed += _payed
                        unpayed += _unpayed
                    except Exception:
                        pass
                """
                customer_information = {
                    "cst_name": cst.user.username,
                    "cst_fname": cst.user.first_name,
                    "cst_lname": cst.user.last_name,
                    "cst_tc": cst.tc_no,
                    "cst_lat": cst.facility_location_lat,
                    "cst_lon": cst.facility_location_lon,
                    "cst_id": cst.id,
                    "facilities": [],
                    "payed": cst.payed,
                    "unpayed": cst.unpayed,
                    "limit": cst.limit
                }
                for loc in customer_locations:
                    customer_information["facilities"].append({
                        "tag": loc.facility_tag,
                        "facility_location_lat": loc.facility_location_lat,
                        "facility_location_lon": loc.facility_location_lon
                    })
                data.append(customer_information)

        return Response(data, status=200)

    def delete(self, request, pk, format=None):
        try:
            cst = Customer.objects.get(id=pk)
            usr = User.objects.get(id=cst.user_id)
            usr.delete()
            cst.delete()
        except:
            return Response(status=400)
        return Response(status=200)

    def generateUserID(self):
        try:
            last_emp = Employee.objects.last().user_id
            last_customer = Customer.objects.last().user_id
            if last_emp >= last_customer:
                last_saved_fucked = last_emp
            else:
                last_saved_fucked = last_customer

            username = User.objects.get(id=last_saved_fucked).username
            try:
                int_userid = int(username)
                return int_userid + randint(100, 1000)
            except ValueError:
                return randint(100, 1000)
        except Exception:
            return randint(100, 1000)

    def _materials_debt_calculate(self, mats):
        payed_tl = 0
        unpayed_tl = 0
        for mat in mats:
            if mat.payed:
                payed_tl += mat.mat_price * mat.count
            else:
                unpayed_tl += mat.mat_price * mat.count
        return payed_tl, unpayed_tl

class CustomerDebtPayHistory(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        customer_defined_issues = CustomerDebtHistory.objects.filter(customer_id=pk).order_by('-payed_date')
        if customer_defined_issues:
            serialized_obj = serializers.serialize('json', customer_defined_issues)
            serialized_obj = json.loads(serialized_obj)
            if len(serialized_obj) != 0:
                status = 200
                data = serialized_obj
        else:
            status = 400
            data = []
        return Response(data, status)

class CustomerDebts(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        emp = Employee.objects.get(user_id=request.user.id)
        customer_defined_issues = CustomerIssue.objects.filter(corp_id=emp.corp_id, customer_id=pk).order_by('-date')
        if customer_defined_issues:
            serialized_obj = serializers.serialize('json', customer_defined_issues)
            serialized_obj = json.loads(serialized_obj)
            if len(serialized_obj) != 0:
                status = 200
                data = self._get_cost(serialized_obj)
        else:
            status = 400
            data = []
        return Response(data, status)

    def _get_cost(self, csts):
        for cst in csts:
            corp_iss = CorporationIssues.objects.filter(issue_id=cst["pk"]).last()
            cst["cost"] = 0
            try:
                usd_mats = corp_iss.used_materials.all().annotate(prod=F('count') * F('mat_price'))
                for mat in usd_mats:
                    cst["cost"] += mat.prod
            except Exception:
                pass

        return csts

class CustomerDebtDetail(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        corp_iss = CorporationIssues.objects.filter(issue_id=pk).last()
        usd_mats = corp_iss.used_materials.all()
        data = serializers.serialize('json', usd_mats)
        return Response(json.loads(data))

class CustomerDebtPayedMaterials(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        usedmaterials = request.data['_fuckyou']
        for mat in usedmaterials:
            mat_obj = UsedMaterials.objects.get(id=mat["pk"])
            mat_obj.payed = mat['fields']['payed']
            mat_obj.save()
        return Response(True)

    def patch(self, request, format=None):
        try:
            for cst in request.data["_pays"]:
                if cst["_pay"] != 0:
                    temp_cst = Customer.objects.get(id=cst["_id"])
                    temp_cst.payed += cst["_pay"]
                    temp_cst.unpayed -= cst["_pay"]
                    temp_cst.save()
                    history_add = CustomerDebtHistory()
                    history_add.customer_id = cst["_id"]
                    history_add.payed_amount = cst["_pay"]
                    history_add.save()
            stat = 200
        except Exception:
            stat = 400
        return Response(status=stat)

class UpdateUsedMaterials(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        materials = request.data['_fuck']
        issue_id = request.data["_all_fucked"]
        corp_iss = CorporationIssues.objects.get(id=issue_id)
        iss_id = CustomerIssue.objects.get(id=corp_iss.issue_id)
        customer = Customer.objects.get(id=iss_id.customer_id)
        for mat in materials:
            mat_obj = UsedMaterials.objects.get(id=mat['_id'])
            if mat_obj.mat_price != mat['mat_price']:
                if mat_obj.mat_price > float(mat['mat_price']):
                    customer.unpayed -= (mat_obj.mat_price * mat_obj.count) - (float(mat['mat_price']) * mat_obj.count)
                elif mat_obj.mat_price < float(mat['mat_price']):
                    customer.unpayed += (float(mat['mat_price']) * mat_obj.count) - (mat_obj.mat_price * mat_obj.count)
                customer.save()
                mat_obj.mat_price = mat['mat_price']
                mat_obj.save()
        return Response(True)

    def patch(self, request, pk, format=None):
        issue = CorporationIssues.objects.get(id=pk)
        customer_iss = CustomerIssue.objects.get(id=issue.issue_id)
        customer = Customer.objects.get(id=customer_iss.customer_id)

        emp = Employee.objects.get(user_id=request.user.id)
        material = Materials.objects.get(id=request.data["material_id"])
        used = UsedMaterials()
        used.corp_id = emp.corp_id
        used.material_id = request.data["material_id"]
        used.mat_name = material.material
        used.mat_price = material.price
        used.count = request.data["material_count"]
        used.save()
        customer.unpayed += material.price * float(request.data["material_count"])
        customer.save()
        issue.used_materials.add(used)

        return Response(True)

class CustomerDeviceOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        cst = Customer.objects.get(user_id=request.user.id)
        return Response(status=200)

class CustomerIssueOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, format=None):
        # customer new issue add
        customer_id = request.user.id
        try:
            customer = Customer.objects.get(user_id=customer_id)
            new_issue = CustomerIssue()
            new_issue.customer_id = customer.id
            new_issue.corp_id = customer.corp_id
            new_issue.customer_fac_id = request.data["erroratwhere"]["_id"]
            new_issue.title = request.data["title"]
            new_issue.content = request.data["content"]
            new_issue.issue_emergency = request.data["issue_emergency"] # models deki derecelendirmeye uyulacak
            new_issue.save()
        except:
            return Response(status=400)
        return Response(status=200)

    def get(self, request, format=None):
        # admin panel get corporation issues
        emp = Employee.objects.get(user_id=request.user.id)
        corp_issues = CustomerIssue.objects.filter(corp_id=emp.corp_id).order_by('-date')
        data = []
        if len(corp_issues) != 0:
            for issue in corp_issues:
                cst = Customer.objects.get(id=issue.customer_id)
                expired = cst.unpayed >= cst.limit
                corp_iss = CorporationIssues.objects.filter(issue_id=issue.id).last()
                if corp_iss != None:
                    is_refused = corp_iss.employee_refuse
                    reason = corp_iss.refuse_description
                else:
                    is_refused = 0
                    reason = ""
                data.append({
                    "cst_name": cst.user.username,
                    "cst_fname": cst.user.first_name,
                    "cst_lname": cst.user.last_name,
                    "iss_title": issue.title,
                    "iss_content": issue.content,
                    "iss_emergency": issue.issue_emergency,
                    "iss_date": issue.date,
                    "iss_id": issue.id,
                    "iss_done": issue.is_done,
                    "is_attached": issue.is_attached,
                    "is_refused": is_refused,
                    "reason": reason,
                    "expired": expired
                })
        return Response(data, status=200)

class CustomerIssueReport(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        corp_issue = CorporationIssues.objects.filter(issue_id=pk).last()
        all_used_in_case = corp_issue.used_materials.all()
        data = []
        for mat in all_used_in_case:
            data.append({"mat_name": mat.mat_name, "mat_price": mat.mat_price, "count": mat.count})
        return Response(data, status=200)

class CustomerCsvHistory(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        all_cstiss = CustomerIssue.objects.filter(Q(customer_id=pk) & Q(is_done=True))
        all_corp_iss = []
        for iss in all_cstiss:
            iss = CorporationIssues.objects.filter(issue_id=iss.id).last()
            all_corp_iss.append(iss)

        all_corp_iss = self._report_corp(all_corp_iss)
        customer_debt_history = self._debt_payed_history(pk)
        report = all_corp_iss + customer_debt_history
        report = sorted(report, key=lambda k: k['Tarih'])
        cst = Customer.objects.get(id=pk)
        cst_serialize = {
            'name': cst.user.first_name,
            'surname': cst.user.last_name,
            'limit': cst.limit,
            'payed': cst.payed,
            'unpayed': cst.unpayed
        }
        report = [cst_serialize, report]
        return Response(report, status=200)

    def _debt_payed_history(self, cst):
        history = CustomerDebtHistory.objects.filter(customer_id=cst)
        serialized_history = []
        if history != None:
            for pay in history:
                serialized_history.append({
                    'Tarih': pay.payed_date,
                    'Tutar': pay.payed_amount,
                    'Açıklama': 'ÖDEME'
                })
        return serialized_history

    def _report_corp(self, isslist):
        serialized_list = []
        for iss in isslist:
            if iss.finish_date != None:
                mats = iss.used_materials.all()
                debt = self._debtcalculate(mats)
                description = self._descofjob(iss.issue_id)
                serialized_list.append({
                    'Tarih': iss.finish_date,
                    'Tutar': debt,
                    'Açıklama': description + ' --service'
                })
        return serialized_list

    def _debtcalculate(self, mts):
        debt = 0
        if mts != None:
            for mat in mts:
                debt += float(mat.count) * float(mat.mat_price)
        return debt

    def _descofjob(self, issid):
        return CustomerIssue.objects.get(id=issid).title

########## EMPLOYEE APIs ##########

class FacilityHistoricalOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        corp = Employee.objects.get(user_id=request.user.id).corp_id
        fachistory = CustomerIssue.objects.filter(Q(customer_fac_id=pk) & Q(corp_id=corp)).order_by('-date')
        return Response(serializers.serialize('json', fachistory))

class EmployeeHeartBeat(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        emp = Employee.objects.get(user_id=request.user.id)
        return Response(emp.is_busy)


class EmployeeInternalOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        # employee gets has jobs
        data = []
        emp = Employee.objects.get(user_id=request.user.id)
        emp_jobs = CorporationIssues.objects.filter(employee_id=emp.id).order_by('-date')
        if emp_jobs:
            for jb in emp_jobs:
                all_used_in_case = jb.used_materials.all()
                used_mat = []
                if all_used_in_case:
                    for mat in all_used_in_case:
                        material = Materials.objects.get(id=mat.material_id)
                        used_mat.append({"mat_name": material.material, "mat_price": material.price, "count": mat.count})

                iss = CustomerIssue.objects.get(id=jb.issue_id)
                customer = Customer.objects.get(id=iss.customer_id)
                erroratfacility = CustomerFacilities.objects.get(id=iss.customer_fac_id)
                customer_lo = [erroratfacility.facility_location_lat, erroratfacility.facility_location_lon]
                data.append({
                    "used_mat": used_mat,
                    "finish": jb.finish_date,
                    "_refused": jb.employee_refuse,
                    "_fuckin_id": jb.id,
                    "customer": {
                        "cst_name": customer.user.username,
                        "cst_fname": customer.user.first_name,
                        "cst_lname": customer.user.last_name,
                        "cst_location": customer_lo, # [customer.facility_location_lat, customer.facility_location_lon],
                        "cst_location_id": iss.customer_fac_id,
                        "cst_id": customer.id
                    },
                    "issue": {
                        "iss_title": iss.title,
                        "iss_content": iss.content,
                        "iss_emergency": iss.issue_emergency,
                        "iss_date": iss.date,
                        "iss_id": jb.id,
                        "iss_done": iss.is_done
                    }
                })
        return Response(data, status=200)

    def post(self, request, pk, format=None):
        emp = Employee.objects.get(user_id=request.user.id)
        job = CorporationIssues.objects.get(Q(employee_id=emp.id) & Q(id=pk))
        job.finish_date = timezone.now()
        job.save()
        iss = CustomerIssue.objects.get(id=job.issue_id)
        iss.is_attached = False
        iss.is_done = True
        iss.save()
        emp.is_busy = False
        emp.save()
        return Response(status=200)

    def patch(self, request, pk, format=None):
        # issue used_materials update
        issue = CorporationIssues.objects.get(id=pk)
        customer_iss = CustomerIssue.objects.get(id=issue.issue_id)
        customer = Customer.objects.get(id=customer_iss.customer_id)
        try:
            value = int(request.data["used_count"])
            if value < 0:
                return Response(status=400)
        except ValueError:
            return Response(status=400)
        emp = Employee.objects.get(user_id=request.user.id)
        material = Materials.objects.get(id=request.data["material_id"])
        used = UsedMaterials()
        used.corp_id = emp.corp_id
        used.material_id = request.data["material_id"]
        used.mat_name = material.material
        used.mat_price = material.price
        used.count = request.data["used_count"]
        used.save()
        customer.unpayed += material.price * float(request.data["used_count"])
        customer.save()
        issue.used_materials.add(used)
        employee = Employee.objects.get(id=issue.employee_id)
        employee.is_busy = False
        employee.save()
        
        return Response(status=200)

class AdminCustomerAdd(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, format=None):
        cst_fac = request.data["cst_fac"]
        cst_id = request.data["cst_id"]
        cst_fac = CustomerFacilities.objects.filter(Q(customer_id=cst_id) & Q(facility_tag=cst_fac)).last().id
        titleNew = request.data["titleNew"]
        content = request.data["content"]
        selectImportant = request.data["selectImportant"]

        try:
            customer = Customer.objects.get(id=cst_id)
            new_issue = CustomerIssue()
            new_issue.customer_id = customer.id
            new_issue.corp_id = customer.corp_id
            new_issue.customer_fac_id = cst_fac
            new_issue.title = titleNew
            new_issue.content = content
            new_issue.issue_emergency = selectImportant
            new_issue.save()
        except:
            return Response(status=400)
        return Response(status=200)

class EmployeeRefuseJob(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        _id_iss = request.data['_fuckin_id']
        _desc_refuse = request.data['_fuckin_description']
        corp_iss = CorporationIssues.objects.get(id=_id_iss)
        corp_iss.employee_refuse = True
        corp_iss.finish_date = timezone.now()
        corp_iss.refuse_description = _desc_refuse
        corp_iss.save()
        customer_iss = CustomerIssue.objects.get(id=corp_iss.issue_id)
        customer_iss.is_attached = False
        customer_iss.is_done = False
        customer_iss.save()
        employee = Employee.objects.get(id=corp_iss.employee_id)
        employee.is_busy = False
        employee.save()
        return Response(True)

class CustomerFacilityOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, format=None):
        try:
            cst = Customer.objects.get(user_id=request.user.id)
            customer_new_facility = CustomerFacilities(
                customer_id = cst.id,
                facility_tag = request.data["tag"],
                facility_location_lat = request.data["latitude"],
                facility_location_lon = request.data["longitude"]
            )
            customer_new_facility.save()
            status = 200
        except Exception:
            status = 400
        return Response(status=status)

    def post(self, request, format=None):
        try:
            cst = Customer.objects.get(id=request.data["cst_id"])
            customer_new_facility = CustomerFacilities(
                customer_id = cst.id,
                facility_tag = request.data["tag"],
                facility_location_lat = request.data["latitude"],
                facility_location_lon = request.data["longitude"]
            )
            customer_new_facility.save()
            status = 200
        except Exception:
            status = 400
        return Response(status=status)

    def get(self, request, format=None):
        uid = request.user.id
        try:
            cst = Customer.objects.get(user_id=uid)
            customer_facilities = [{"_id": fac.id, "value": fac.facility_tag, "tag": fac.facility_tag, "location": [fac.facility_location_lat, fac.facility_location_lon]} for fac in CustomerFacilities.objects.filter(customer_id=cst.id)]
            return Response(customer_facilities, status=200)
        except Exception:
            return Response(status=400)

class CustomerInternalOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        # old or live issues 
        cst = Customer.objects.get(user_id=request.user.id)
        customer_issues = CustomerIssue.objects.filter(customer_id=cst.id).order_by('-date')
        issues = []
        if customer_issues:
            for ciss in customer_issues:
                try:
                    iss = CorporationIssues.objects.filter(issue_id=ciss.id).last()
                    if iss != None:
                        iss_employee = Employee.objects.get(id=iss.employee_id)
                        iss_employee_obj = {
                            "username": iss_employee.user.username,
                            "first_name": iss_employee.user.first_name,
                            "last_name": iss_employee.user.last_name
                        }
                    else:
                        iss_employee_obj = {
                            "username": "",
                            "first_name": "",
                            "last_name": ""
                        }
                    waiting = False
                except ObjectDoesNotExist:
                    waiting = True
                if waiting:
                    # admin doesnt attach this issue to employee (waiting = true)
                    issues.append({
                        "iss_detail": {
                            "waiting": True
                        },
                        "iss_generic": {
                            "title": ciss.title,
                            "content": ciss.content,
                            "is_done": ciss.is_done
                        }
                    })
                else:
                    # attached issue to employee (waiting = false)
                    used_mat = []
                    issue_date = ""
                    issue_finish = ""
                    if iss != None:
                        all_used_in_case = iss.used_materials.all()
                        if all_used_in_case:
                            for mat in all_used_in_case:
                                material = Materials.objects.get(id=mat.material_id)
                                used_mat.append({"mat_name": material.material, "mat_price": material.price, "count": mat.count})
                        issue_date = iss.date
                        issue_finish = iss.finish_date
                    issues.append({
                        "iss_employee": iss_employee_obj,
                        "iss_detail": {
                            "iss_date": issue_date,
                            "iss_finish": issue_finish,
                            "used_mat": used_mat
                        },
                        "iss_generic": {
                            "title": ciss.title,
                            "content": ciss.content,
                            "is_done": ciss.is_done
                        }
                    })
        return Response(issues, status=200)

class CustomerProfileOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        try:
            data = self.getuserinformaiton(request.user.id)
            status = 200
        except ObjectDoesNotExist:
            data = {}
            status = 400
        return Response(data, status=status)

    def post(self, request, format=None):
        try:
            cst = Customer.objects.get(user_id=request.user.id)
            user = User.objects.get(id=request.user.id)
            if request.data["username"]:
                user.username = request.data["username"]
            if request.data["first_name"]:
                user.first_name = request.data["first_name"]
            if request.data["last_name"]:
                user.last_name = request.data["last_name"]
            if request.data["email"]:
                user.email = request.data["email"]
            if request.data["password"]:
                user.set_password(request.data["password"])
            user.save()

            if request.data["tc"]:
                cst.tc_no = request.data["tc"]
            if request.data["facility"]:
                cst.facility = request.data["facility"]
            cst.save()
            status = 200
            _updatedprofile = self.getuserinformaiton(request.user.id)
        except ObjectDoesNotExist:
            _updatedprofile = {}
            status = 400
        return Response(_updatedprofile, status=status)

    def getuserinformaiton(self, uid):
        cst = Customer.objects.get(user_id=uid)
        user = User.objects.get(id=uid)
        data = {
            "cst": {
                "tc": cst.tc_no,
                "facility": cst.facility,
                "location": [cst.facility_location_lat, cst.facility_location_lon]
            },
            "user": {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email
            }
        }
        return data

class CustomerLocationOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        try:
            cst = Customer.objects.get(user_id=request.user.id)
            cst.facility_location_lon = request.data["facility_location_lon"]
            cst.facility_location_lat = request.data["facility_location_lat"]
            cst.save()
        except:
            return Response(status=400)
        return Response(status=200)

class EmployeeLocationOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        if isEmployeeManager(request.user.id) == False:
            try:
                emp = Employee.objects.get(user_id=request.user.id)
                emp.last_location_lon = request.data["location_lon"]
                emp.last_location_lat = request.data["location_lat"]
                emp.save()
            except:
                return Response(status=400)
            return Response(status=200)
        else:
            return Response(status=401)

class CorporationIssueOptions(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        emp = Employee.objects.get(user_id=request.user.id)
        corp_issues = CorporationIssues.objects.filter(corp_id=emp.corp_id).order_by('-date')
        data = []
        for _is in corp_issues:
            customer_issue = CustomerIssue.objects.get(id=_is.issue_id)
            emp_in_case = Employee.objects.get(id=_is.employee_id)
            customer = Customer.objects.get(id=customer_issue.customer_id)
            all_used_in_case = _is.used_materials.all()
            used_mat = []
            if all_used_in_case:
                for mat in all_used_in_case:
                    # material = Materials.objects.get(id=mat.material_id)
                    used_mat.append({"_id": mat.id, "mat_name": mat.mat_name, "mat_price": mat.mat_price, "count": mat.count})
            data.append({
                "_id": _is.id,
                "issue_information": {
                    "title": customer_issue.title,
                    "content": customer_issue.content,
                    "issue_emergency": customer_issue.issue_emergency,
                    "is_done": customer_issue.is_done,
                    "is_attached": customer_issue.is_attached
                },
                "employee_information": {
                    "user": {
                        "username": emp_in_case.user.username,
                        "first": emp_in_case.user.first_name,
                        "last": emp_in_case.user.last_name,
                        "mail": emp_in_case.user.email
                    },
                    "location": [emp_in_case.last_location_lat, emp_in_case.last_location_lon],
                    "is_busy": emp_in_case.is_busy
                },
                "customer_information": {
                    "user": {
                        "username": customer.user.username,
                        "first": customer.user.first_name,
                        "last": customer.user.last_name,
                        "mail": customer.user.email
                    },
                    "facility": customer.facility,
                    "facility_location": [customer.facility_location_lat, customer.facility_location_lon]
                }, 
                "created_date": _is.date,
                "finish_date": _is.finish_date,
                "refuse": _is.employee_refuse,
                "refuse_desc": _is.refuse_description,
                "used_mat": used_mat
            })
        return Response(data, status=200)


    def put(self, request, format=None):
        try:
            manager = Employee.objects.get(user_id=request.user.id)
            iss_id = request.data["iss_id"]
            new_corporation_issue = CorporationIssues(
                corp_id = manager.corp_id,
                issue_id = iss_id,
                employee_id = request.data["emp_id"],
            )
            new_corporation_issue.save()
            issue = CustomerIssue.objects.get(id=iss_id)
            issue.is_attached = True
            issue.save()
            emp = Employee.objects.get(id=request.data["emp_id"])
            emp.is_busy = True
            emp.save()
            status = 200
        except ObjectDoesNotExist:
            status = 400
        return Response(status=status)

    def post(self, request, format=None):
        try:
            manager = Employee.objects.get(user_id=request.user.id)
            iss_id = request.data["iss_id"]
            if not request.data["check_busy"]:
                corp_emps = Employee.objects.filter(Q(corp_id=manager.corp_id) & ~Q(user_id=request.user.id) & Q(is_busy=False) & Q(is_manager=False) & Q(is_active=True))
            else:
                corp_emps = Employee.objects.filter(Q(corp_id=manager.corp_id) & ~Q(user_id=request.user.id) & Q(is_manager=False) & Q(is_active=True))
            issue = CustomerIssue.objects.get(id=iss_id)
            customer = CustomerFacilities.objects.get(id=issue.customer_fac_id)
            R = 6373.0
            lat1 = radians(customer.facility_location_lat)
            lon1 = radians(customer.facility_location_lon)
            distances = []
            for emp in corp_emps:
                lat2 = radians(emp.last_location_lat)
                lon2 = radians(emp.last_location_lon)
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                distances.append({
                    "emp_id": emp.id,
                    "distance": R * c
                })
            try:
                near_emp = sorted(distances, key=lambda d: sorted(d.items()))[0]
            except:
                return Response({"error": "all_emps_in_cases"}, status=400)
            new_corporation_issue = CorporationIssues(
                corp_id = manager.corp_id,
                issue_id = iss_id,
                employee_id = near_emp["emp_id"],
            )
            new_corporation_issue.save()
            issue = CustomerIssue.objects.get(id=iss_id)
            issue.is_attached = True
            issue.save()
            emp = Employee.objects.get(id=near_emp["emp_id"])
            emp.is_busy = True
            emp.save()
            emp_usr_ins = User.objects.get(id=emp.user_id)
            return Response(emp_usr_ins.first_name + " " + emp_usr_ins.last_name , status=200)
        except ObjectDoesNotExist:
            return Response({"error": "obj_not_found"}, status=400)