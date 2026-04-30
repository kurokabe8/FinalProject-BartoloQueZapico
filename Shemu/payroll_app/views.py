from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, When
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from .models import Employee, Payslip
from django.contrib.auth.models import User


def _is_admin(user):
    return user.is_staff or user.is_superuser


def _get_employee_from_user(user):
    return Employee.objects.filter(id_number=user.username).first()


def _require_admin(request):
    return _is_admin(request.user)


def _require_employee(request):
    return request.user.is_authenticated and (not _is_admin(request.user))

def _apply_payslip_sorting(queryset, sort_by, sort_order):
    month_case = Case(
        When(month="January", then=1),
        When(month="February", then=2),
        When(month="March", then=3),
        When(month="April", then=4),
        When(month="May", then=5),
        When(month="June", then=6),
        When(month="July", then=7),
        When(month="August", then=8),
        When(month="September", then=9),
        When(month="October", then=10),
        When(month="November", then=11),
        When(month="December", then=12),
        output_field=IntegerField(),
    )

    direction = "-" if sort_order == "desc" else ""
    if sort_by == "id_number":
        return queryset.order_by(f"{direction}id_number__id_number", f"{direction}year", f"{direction}pay_cycle")
    if sort_by == "date":
        return queryset.annotate(month_index=month_case).order_by(
            f"{direction}year",
            f"{direction}month_index",
            f"{direction}pay_cycle",
            f"{direction}id_number__id_number",
        )
    return queryset.order_by("-pk")


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
    context = {}
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        id_number = request.POST.get('id_number', '').strip()
        rate = request.POST.get('rate', '').strip()
        allowance = request.POST.get('allowance', 0)
        password = request.POST.get('password', '')

        existing_employee = Employee.objects.filter(id_number=id_number).exists()
        existing_user = User.objects.filter(username=id_number).first()

        if existing_employee:
            context["error"] = "ID Number already exists in employees list."
            return render(request, 'payroll_app/employees/create_employee.html', context)
        # Backward compatibility: old deleted employees may have orphaned auth users.
        if existing_user:
            existing_user.delete()

        try:
            rate_value = float(rate)
            allowance_value = float(allowance) if allowance else 0
            if rate_value < 0 or allowance_value < 0:
                context["error"] = "Rate and allowance cannot be negative."
                return render(request, 'payroll_app/employees/create_employee.html', context)

            with transaction.atomic():
                Employee.objects.create(
                    name=name,
                    id_number=id_number,
                    rate=rate_value,
                    allowance=allowance_value
                )

                user = User.objects.create_user(
                    username=id_number,
                    password=password,
                    first_name=name.split()[0] if name else "",
                    last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else ""
                )

                user.is_staff = False
                user.is_superuser = False
                user.save()
        except (IntegrityError, ValueError):
            context["error"] = "Unable to create employee. Please check inputs and try again."
            return render(request, 'payroll_app/employees/create_employee.html', context)
        
        return redirect('employees_list')
    
    return render(request, 'payroll_app/employees/create_employee.html', context)

@login_required
def update_employee(request, pk): # still should not work wala pa tayo pk
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    employee = get_object_or_404(Employee, pk=pk)
    context = {'employee': employee}
    if request.method == 'POST':
        employee.name = request.POST.get('name', '').strip()
        rate_raw = request.POST.get('rate', '').strip()
        allowance_raw = request.POST.get('allowance', '').strip()
        try:
            rate_value = float(rate_raw)
            allowance_value = float(allowance_raw) if allowance_raw else 0
        except ValueError:
            context['error'] = "Rate and allowance must be valid numbers."
            return render(request, 'payroll_app/employees/update_employee.html', context)

        if rate_value < 0 or allowance_value < 0:
            context['error'] = "Rate and allowance cannot be negative."
            return render(request, 'payroll_app/employees/update_employee.html', context)

        #employee.id_number = request.POST.get('id_number') no need since this field should b locked
        employee.rate = rate_value
        employee.allowance = allowance_value
        employee.save()
        return redirect('employees_list')
    
    return render(request, 'payroll_app/employees/update_employee.html', context)

@login_required
def delete_employee(request, pk): 
    if not _require_admin(request):
        return HttpResponseForbidden("Only admins can access this page.")
    employee = get_object_or_404(Employee, pk=pk)
    with transaction.atomic():
        User.objects.filter(username=employee.id_number).delete()
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
    selected_id = request.GET.get("id_number", "all")
    selected_cycle = request.GET.get("pay_cycle", "all")
    sort_by = request.GET.get("sort_by", "date")
    sort_order = request.GET.get("sort_order", "desc")
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"
    if sort_by not in {"id_number", "date"}:
        sort_by = "date"

    if not _require_admin(request):
        employee = _get_employee_from_user(request.user)
        if employee is None:
            return HttpResponseForbidden("No employee record is linked to this account.")
        payslips = Payslip.objects.filter(id_number=employee)
        if selected_cycle in {"1", "2"}:
            payslips = payslips.filter(pay_cycle=int(selected_cycle))
        payslips = _apply_payslip_sorting(payslips, sort_by, sort_order)
        return render(request, 'payroll_app/payslips/payslips_list.html', {
            'payslips': payslips,
            'selected_id': employee.id_number,
            'selected_cycle': selected_cycle,
            'sort_by': sort_by,
            'sort_order': sort_order,
        })

    payslips = Payslip.objects.all()
    employees = Employee.objects.all()
    if selected_id != "all":
        payslips = payslips.filter(id_number__id_number=selected_id)
    if selected_cycle in {"1", "2"}:
        payslips = payslips.filter(pay_cycle=int(selected_cycle))
    payslips = _apply_payslip_sorting(payslips, sort_by, sort_order)

    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        month = request.POST.get('month')
        year = request.POST.get('year')
        pay_cycle = int(request.POST.get('pay_cycle'))

        if employee_id == "all":
            targets = employees
        else:
            targets = [get_object_or_404(Employee, id_number=employee_id)]

        errors = []
        for employee in targets:
            exists = Payslip.objects.filter(
                id_number=employee,
                month=month,
                year=year,
                pay_cycle=pay_cycle).exists()
            if exists:
                errors.append(f"Payslip already exists for {employee.id_number}, {month} {year}, cycle {pay_cycle}")
                continue 

            # Base values
            base_rate = employee.rate / 2
            allowance = employee.allowance or 0
            overtime = employee.overtime_pay or 0

            pag_ibig = 0
            philhealth = 0
            sss = 0
            deductions_tax = 0

            if pay_cycle == 1:
                pag_ibig = 100
                taxable_income = base_rate + allowance + overtime - pag_ibig
            else:
                philhealth = employee.rate * 0.04
                sss = employee.rate * 0.045
                taxable_income = base_rate + allowance + overtime - philhealth - sss

            deductions_tax = taxable_income * 0.20
            total_pay = taxable_income - deductions_tax

            if pay_cycle == 1:
                date_range = "1-15"
            else:
                date_range = "16-30"

            Payslip.objects.create(
                id_number=employee,
                month=month,
                year=year,
                date_range=date_range, #request.POST.get('date_range', ''), optional
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

        return render(request, 'payroll_app/payslips/payslips_list.html', {
            'payslips': _apply_payslip_sorting(Payslip.objects.all(), sort_by, sort_order),
            'employees': employees,
            'errors': errors,
            'selected_id': selected_id,
            'selected_cycle': selected_cycle,
            'sort_by': sort_by,
            'sort_order': sort_order,
        })

    return render(request, 'payroll_app/payslips/payslips_list.html', {
        'payslips': payslips,
        'employees': employees,
        'selected_id': selected_id,
        'selected_cycle': selected_cycle,
        'sort_by': sort_by,
        'sort_order': sort_order,
    })

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

        if pay_cycle == 1:
            date_range = "1-15"
        else:
            date_range = "16-30"

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