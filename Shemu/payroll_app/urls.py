from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home, name='home'),

    # employee 
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/update/<int:pk>/', views.update_employee, name='update_employee'),
    path('employees/delete/<int:pk>/', views.delete_employee, name='delete_employee'),
    path('employees/add-overtime/<int:pk>/', views.add_overtime, name='add_overtime'),
    
    # payslip
    path('payslips/', views.payslips_list, name='payslips_list'),
    path('payslips/view/<int:pk>/', views.view_payslip, name='view_payslip'),
]