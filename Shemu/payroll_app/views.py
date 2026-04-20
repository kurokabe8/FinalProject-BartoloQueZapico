from django.shortcuts import render, get_object_or_404, redirect
from .models import Employee, Payslip

# employee separator
def employees_list(request):
    employees = Employee.objects.all()
    return render(request, 'payroll_app/employees_list.html', {'employees': employees})

def create_employee(request): 
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

def update_employee(request, pk): # still should not work wala pa tayo pk
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.name = request.POST.get('name')
        employee.id_number = request.POST.get('id_number')
        employee.rate = float(request.POST.get('rate'))
        employee.allowance = float(request.POST.get('allowance', 0))
        employee.save()
        return redirect('employees_list')
    
    return render(request, 'payroll_app/employees/update_employee.html')

def delete_employee(request, pk): 
    employee = get_object_or_404(Employee, pk=pk)
    employee.delete()
    return redirect('employees_list')

def add_overtime(request, pk): 
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        hours = float(request.POST.get('hours', 0)) # whoever makes this pls make sure hours ung nasa form 
        overtime_value = (employee.rate / 160) * 1.5 * hours 
        employee.overtime_pay = (employee.overtime_pay or 0) + overtime_value
        employee.save()
    return redirect('employees_list')

# payslip separator
def payslips_list(request): 
    payslips = Payslip.objects.all()
    return render(request, 'payroll_app/payslips/payslips_list.html', {'payslip': payslips})

def view_payslip(request, pk): 
    payslip = get_object_or_404(Payslip, pk=pk)
    return render(request, 'payroll_app/payslips/view_payslip.html', {'payslip': payslip})

def create_payslip(request):
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
