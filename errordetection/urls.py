from django.contrib import admin
from django.urls import path, include
from detect import views as vs

urlpatterns = [
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('auth/login/', vs.AuthLogin.as_view()), # general login url filter by user_type (0 => manager, 1 => employee, 2 => customer)
    path('materials/', vs.MaterialOptions.as_view()), # corporation materials [GET, PUT] access only manager 
    path('materials/<int:pk>/', vs.MaterialOptions.as_view()), # corporation delete material
    path('emps/', vs.EmployeeOptions.as_view()), # corporation employee [PUT, GET] access with manager
    path('emps/<int:pk>/', vs.EmployeeOptions.as_view()), # corporation employee [PATCH, DELETE] (patch => access employee, delete => access manager)
    path('customers/', vs.CustomerOptions.as_view()), # corporation customer [PUT, GET] access with manager
    path('customers/<int:pk>/', vs.CustomerOptions.as_view()), # corporation customer [PATCH, DELETE] (patch => access customer, delete => access manager)
    path('issues/', vs.CustomerIssueOptions.as_view()), # [PUT, GET] customer can PUT new issue, manager can GET issues
    path('issues/<int:pk>/', vs.CustomerIssueReport.as_view()),
    path('cst_internal/', vs.CustomerInternalOptions.as_view()), # [GET] customer only access
    path('cst_profile/', vs.CustomerProfileOptions.as_view()), # [GET, POST] customer profile informations
    path('cst_updateloc/', vs.CustomerLocationOptions.as_view()),
    path('emp_internal/<int:pk>/', vs.EmployeeInternalOptions.as_view()), # [PATCH] employee patch used_materials on job 
    path('emp_internal/', vs.EmployeeInternalOptions.as_view()), # [GET] employee get issues
    path('emp_updateloc/', vs.EmployeeLocationOptions.as_view()),
    path('cst_devopts/', vs.CustomerDeviceOptions.as_view()),
    path('cstiss_opt/', vs.CorporationIssueOptions.as_view()), # [GET, PUT, POST] manager attach issue to employee manuel
    path('admin_statistics/', vs.AdminPanelStatistics.as_view()),
    path('cst_facilities/', vs.CustomerFacilityOptions.as_view()),
    path('customerdebts/<int:pk>/', vs.CustomerDebts.as_view()),
    path('customerdebthistory/<int:pk>/', vs.CustomerDebtPayHistory.as_view()),
    path('customerdebtsdetail/<int:pk>/', vs.CustomerDebtDetail.as_view()),
    path('customerdebtpayed/', vs.CustomerDebtPayedMaterials.as_view()),
    path('customerlimit/<int:pk>/', vs.CustomerLimitOptions.as_view()),
    path('patchused/', vs.UpdateUsedMaterials.as_view()),
    path('patchused/<int:pk>/', vs.UpdateUsedMaterials.as_view()),
    path('emprefuse/', vs.EmployeeRefuseJob.as_view()),
    path('admin_addissue/', vs.AdminCustomerAdd.as_view()),
    path('updateemps/', vs.AdminUpdateEmployees.as_view()),
    path('customercsv/<int:pk>/', vs.CustomerCsvHistory.as_view()),
    path('fachistory/<int:pk>/', vs.FacilityHistoricalOptions.as_view()),
    path('empcheck/', vs.EmployeeHeartBeat.as_view())
]
