from django.shortcuts import render

def employees_list(request):
    return render(request, 'payroll_app/employees_list.html')

#adding empty placeholders to test lang
def create_employee(request): 
    return render(request, 'payroll_app/employees/create_employee.html') # only for testing ung mga pass it should bring up an error
def update_employee(request, pk): pass
def delete_employee(request, pk): pass
def add_overtime(request, pk): pass
def payslips_list(request): pass
def view_payslip(request, pk): pass
def create_payslip(request): pass