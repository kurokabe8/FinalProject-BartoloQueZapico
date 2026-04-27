from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from .models import Employee, Payslip


def _is_admin(user):
    return user.is_staff or user.is_superuser


def _get_employee_from_user(user):
    return Employee.objects.filter(id_number=user.username).first()


def _require_admin(request):
    return _is_admin(request.user)


def _require_employee(request):
    return request.user.is_authenticated and (not _is_admin(request.user))


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    context = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        context["error"] = "Invalid username or password."

    return render(request, "payroll_app/login.html", context)


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    if _is_admin(request.user):
        return redirect("employees_list")
    return redirect("payslips_list")

# employee separator
@login_required
def employees_list(request):
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    employees = Employee.objects.all()
    return render(request, 'payroll_app/employees_list.html', {'employees': employees})

@login_required
def create_employee(request): 
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    if request.method == 'POST':
        name = request.POST.get('name')
        id_number = request.POST.get('id_number')
        rate = request.POST.get('rate')
        allowance = request.POST.get('allowance', 0)

        Employee.objects.create(
            name= name,
            id_number= id_number,
            rate=float(rate),
            allowance=float(allowance) if allowance else 0
        )
        return redirect('employees_list')
    
    return render(request, 'payroll_app/employees/create_employee.html')

@login_required
def update_employee(request, pk): # still should not work wala pa tayo pk
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.name = request.POST.get('name')
        employee.id_number = request.POST.get('id_number')
        employee.rate = float(request.POST.get('rate'))
        employee.allowance = float(request.POST.get('allowance', 0))
        employee.save()
        return redirect('employees_list')
    
    return render(request, 'payroll_app/employees/update_employee.html', {'employee': employee})

@login_required
def delete_employee(request, pk): 
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    employee = get_object_or_404(Employee, pk=pk)
    employee.delete()
    return redirect('employees_list')

@login_required
def add_overtime(request, pk): 
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        hours = float(request.POST.get('hours', 0)) # whoever makes this pls make sure hours ung nasa form 
        overtime_value = (employee.rate / 160) * 1.5 * hours 
        employee.overtime_pay = (employee.overtime_pay or 0) + overtime_value
        employee.save()
    return redirect('employees_list')

# payslip separator
@login_required
def payslips_list(request): 
    if _is_admin(request.user):
        payslips = Payslip.objects.all()
    else:
        employee = _get_employee_from_user(request.user)
        if employee is None:
            return HttpResponseForbidden("No employee record is linked to this account.")
        payslips = Payslip.objects.filter(id_number=employee)
    return render(request, 'payroll_app/payslips/payslips_list.html', {'payslips': payslips})

@login_required
def view_payslip(request, pk): 
    payslip = get_object_or_404(Payslip, pk=pk)
    if _require_employee(request):
        employee = _get_employee_from_user(request.user)
        if employee is None or payslip.id_number != employee:
            return HttpResponseForbidden("You can only view your own payslips.")
    return render(request, 'payroll_app/payslips/view_payslip.html', {'payslip': payslip})

@login_required
def create_payslip(request):
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        month = request.POST.get('month')
        year = request.POST.get('year')
        date_range = request.POST.get('date_range')
        pay_cycle = int(request.POST.get('pay_cycle'))

        employee = get_object_or_404(Employee, id_number=employee_id)

        base_rate = employee.rate / 2
        allowance = employee.allowance or 0
        overtime = employee.overtime_pay or 0

        pag_ibig = 0
        philhealth = 0
        sss = 0
        deductions_tax = 0

        # Cycle 1
        if pay_cycle == 1:
            pag_ibig = 100
            taxable_income = base_rate + allowance + overtime - pag_ibig
            deductions_tax = taxable_income * 0.20
            total_pay = taxable_income - deductions_tax

        # Cycle 2
        else:
            philhealth = employee.rate * 0.04
            sss = employee.rate * 0.045
            taxable_income = base_rate + allowance + overtime - philhealth - sss
            deductions_tax = taxable_income * 0.20
            total_pay = taxable_income - deductions_tax

        payslip = Payslip.objects.create(
            id_number=employee,
            month=month,
            year=year,
            date_range=date_range,
            pay_cycle=pay_cycle,
            rate=employee.rate,
            earnings_allowance=allowance,
            overtime=overtime,
            pag_ibig=pag_ibig,
            deductions_health=philhealth,
            sss=sss,
            deductions_tax=deductions_tax,
            total_pay=total_pay,
        )

        employee.resetOvertime()

        return redirect('payslips_list')

    return render(request, 'payroll_app/payslips/create_payslip.html')
