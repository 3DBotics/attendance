from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
import os

TEAL_COLOR = HexColor('#0d9488')
CORAL_COLOR = HexColor('#f87171')
LIGHT_GRAY = HexColor('#f3f4f6')
DARK_GRAY = HexColor('#374151')

def calculate_sss_contribution(monthly_salary):
    """
    2025 SSS Contribution Calculation (Bracket-based)
    Total: 15% (EE: 5%, ER: 10% + EC)
    EC (Employer only): P10 for MSC up to P14,500; P30 for MSC P15,000+
    MSC ranges from P5,000 to P35,000 (2025 rates)
    Uses SSS Circular 2024-006 official brackets
    """
    SSS_BRACKETS = [
        (0, 4999.99, 5000),
        (5000, 5249.99, 5000),
        (5250, 5749.99, 5500),
        (5750, 6249.99, 6000),
        (6250, 6749.99, 6500),
        (6750, 7249.99, 7000),
        (7250, 7749.99, 7500),
        (7750, 8249.99, 8000),
        (8250, 8749.99, 8500),
        (8750, 9249.99, 9000),
        (9250, 9749.99, 9500),
        (9750, 10249.99, 10000),
        (10250, 10749.99, 10500),
        (10750, 11249.99, 11000),
        (11250, 11749.99, 11500),
        (11750, 12249.99, 12000),
        (12250, 12749.99, 12500),
        (12750, 13249.99, 13000),
        (13250, 13749.99, 13500),
        (13750, 14249.99, 14000),
        (14250, 14749.99, 14500),
        (14750, 15249.99, 15000),
        (15250, 15749.99, 15500),
        (15750, 16249.99, 16000),
        (16250, 16749.99, 16500),
        (16750, 17249.99, 17000),
        (17250, 17749.99, 17500),
        (17750, 18249.99, 18000),
        (18250, 18749.99, 18500),
        (18750, 19249.99, 19000),
        (19250, 19749.99, 19500),
        (19750, 20249.99, 20000),
        (20250, 20749.99, 20500),
        (20750, 21249.99, 21000),
        (21250, 21749.99, 21500),
        (21750, 22249.99, 22000),
        (22250, 22749.99, 22500),
        (22750, 23249.99, 23000),
        (23250, 23749.99, 23500),
        (23750, 24249.99, 24000),
        (24250, 24749.99, 24500),
        (24750, 25249.99, 25000),
        (25250, 25749.99, 25500),
        (25750, 26249.99, 26000),
        (26250, 26749.99, 26500),
        (26750, 27249.99, 27000),
        (27250, 27749.99, 27500),
        (27750, 28249.99, 28000),
        (28250, 28749.99, 28500),
        (28750, 29249.99, 29000),
        (29250, 29749.99, 29500),
        (29750, 30249.99, 30000),
        (30250, 30749.99, 30500),
        (30750, 31249.99, 31000),
        (31250, 31749.99, 31500),
        (31750, 32249.99, 32000),
        (32250, 32749.99, 32500),
        (32750, 33249.99, 33000),
        (33250, 33749.99, 33500),
        (33750, 34249.99, 34000),
        (34250, 34749.99, 34500),
        (34750, float('inf'), 35000),
    ]
    
    msc = 5000
    for lower, upper, credit in SSS_BRACKETS:
        if lower <= monthly_salary <= upper:
            msc = credit
            break
    
    employee_share = msc * 0.05
    employer_share = msc * 0.10
    
    if msc >= 15000:
        ec_contribution = 30
    else:
        ec_contribution = 10
    
    employer_share += ec_contribution
    
    return round(employee_share, 2), round(employer_share, 2)


def calculate_philhealth_contribution(monthly_salary):
    """
    2025 PhilHealth Contribution Calculation
    Total: 5% of monthly salary
    Split: 50/50 (2.5% EE / 2.5% ER)
    Floor: P10,000 (min contribution P250 each)
    Ceiling: P100,000 (max contribution P2,500 each)
    """
    FLOOR = 10000
    CEILING = 100000
    RATE = 0.05
    
    contribution_base = max(FLOOR, min(monthly_salary, CEILING))
    
    total_contribution = contribution_base * RATE
    
    employee_share = total_contribution / 2
    employer_share = total_contribution / 2
    
    return round(employee_share, 2), round(employer_share, 2)


def calculate_pagibig_contribution(monthly_salary):
    """
    2025 Pag-IBIG Contribution Calculation
    For salaries over P1,500:
    - EE: 2% of monthly salary, capped at P200 (based on P10,000 salary fund max)
    - ER: 2% of monthly salary, capped at P200
    For salaries P1,500 and below:
    - EE: 1% of monthly salary, capped at P100
    - ER: 2% of monthly salary, capped at P200
    Both shares are capped independently.
    """
    MAX_EE_CONTRIBUTION = 200
    MAX_ER_CONTRIBUTION = 200
    
    if monthly_salary > 1500:
        ee_rate = 0.02
        er_rate = 0.02
    else:
        ee_rate = 0.01
        er_rate = 0.02
        MAX_EE_CONTRIBUTION = 100
    
    employee_share = min(monthly_salary * ee_rate, MAX_EE_CONTRIBUTION)
    employer_share = min(monthly_salary * er_rate, MAX_ER_CONTRIBUTION)
    
    return round(employee_share, 2), round(employer_share, 2)


def calculate_all_contributions(monthly_salary):
    """
    Calculate all 2025 Philippine statutory contributions.
    Returns dict with employee and employer shares for each.
    """
    sss_ee, sss_er = calculate_sss_contribution(monthly_salary)
    philhealth_ee, philhealth_er = calculate_philhealth_contribution(monthly_salary)
    pagibig_ee, pagibig_er = calculate_pagibig_contribution(monthly_salary)
    
    return {
        'sss': {'employee': sss_ee, 'employer': sss_er},
        'philhealth': {'employee': philhealth_ee, 'employer': philhealth_er},
        'pagibig': {'employee': pagibig_ee, 'employer': pagibig_er},
        'total_employee': sss_ee + philhealth_ee + pagibig_ee,
        'total_employer': sss_er + philhealth_er + pagibig_er
    }


def generate_payslip_pdf(payroll_data, employee_data, period_data, deductions):
    """
    Generate a professional PDF payslip with 3DBotics branding.
    
    Args:
        payroll_data: dict with payroll record info (locked_daily_rate, days_worked, etc.)
        employee_data: dict with employee info (name, position, etc.)
        period_data: dict with period info (name, start_date, end_date)
        deductions: list of deduction items
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=TEAL_COLOR,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_GRAY,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=white,
        backColor=TEAL_COLOR,
        spaceAfter=6,
        spaceBefore=12,
        leftIndent=6,
        rightIndent=6
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=DARK_GRAY
    )
    
    bold_style = ParagraphStyle(
        'CustomBold',
        parent=styles['Normal'],
        fontSize=9,
        textColor=black,
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    logo_paths = ['static/3dbotics_logo.png', 'static/logo.png', 'attached_assets/3DBotics_LOGO_new_1766017505888.png']
    logo_loaded = False
    for logo_path in logo_paths:
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.8*inch, height=1.8*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                logo_loaded = True
                break
            except:
                continue
    
    if not logo_loaded:
        elements.append(Spacer(1, 0.5*inch))
    
    elements.append(Paragraph("3DBotics\u00ae", title_style))
    elements.append(Paragraph("3D Printing | AI | Robotics", subtitle_style))
    
    elements.append(Spacer(1, 0.1*inch))
    
    payslip_title = ParagraphStyle(
        'PayslipTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=TEAL_COLOR,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    elements.append(Paragraph("PAYSLIP", payslip_title))
    elements.append(Paragraph(f"Pay Period: {period_data['name']}", subtitle_style))
    elements.append(Paragraph(f"{period_data['start_date']} to {period_data['end_date']}", subtitle_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    emp_info = [
        ['Employee Name:', f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}", 
         'Employee ID:', employee_data.get('employee_id', '')],
        ['Position:', employee_data.get('position', 'N/A'), 
         'Branch:', employee_data.get('branch_name', 'N/A')],
        ['Daily Rate:', f"P{payroll_data['locked_daily_rate']:,.2f}", 
         'Days Worked:', f"{payroll_data['days_worked']:.2f}"],
    ]
    
    emp_table = Table(emp_info, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
    emp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK_GRAY),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
    ]))
    elements.append(emp_table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    regular_pay = payroll_data.get('regular_pay', 0)
    overtime_pay = payroll_data.get('overtime_pay', 0)
    holiday_pay = payroll_data.get('holiday_pay', 0)
    gross_pay = payroll_data.get('gross_pay', 0)
    
    tardiness_ded = payroll_data.get('tardiness_deduction', 0)
    undertime_ded = payroll_data.get('undertime_deduction', 0)
    
    sss_ee = 0
    philhealth_ee = 0
    pagibig_ee = 0
    sss_er = 0
    philhealth_er = 0
    pagibig_er = 0
    
    for ded in deductions:
        name = ded['deduction_name'].upper()
        if 'SSS' in name:
            sss_ee = ded['employee_amount']
            sss_er = ded['employer_amount']
        elif 'PHILHEALTH' in name or 'PHIL' in name:
            philhealth_ee = ded['employee_amount']
            philhealth_er = ded['employer_amount']
        elif 'PAG' in name or 'IBIG' in name:
            pagibig_ee = ded['employee_amount']
            pagibig_er = ded['employer_amount']
    
    total_statutory_ee = sss_ee + philhealth_ee + pagibig_ee
    total_deductions = total_statutory_ee + tardiness_ded + undertime_ded
    net_pay = gross_pay - total_deductions
    
    earnings_data = [
        ['EARNINGS', 'Amount'],
        ['Basic Pay (Regular)', f"P{regular_pay:,.2f}"],
        ['Overtime Pay', f"P{overtime_pay:,.2f}"],
        ['Holiday Pay', f"P{holiday_pay:,.2f}"],
        ['', ''],
        ['GROSS PAY', f"P{gross_pay:,.2f}"],
    ]
    
    deductions_data = [
        ['DEDUCTIONS', 'Amount'],
        ['SSS (EE Share)', f"P{sss_ee:,.2f}"],
        ['PhilHealth (EE Share)', f"P{philhealth_ee:,.2f}"],
        ['Pag-IBIG (EE Share)', f"P{pagibig_ee:,.2f}"],
        ['Tardiness', f"P{tardiness_ded:,.2f}"],
        ['TOTAL DEDUCTIONS', f"P{total_deductions:,.2f}"],
    ]
    
    col_width = 3.4*inch
    
    earnings_table = Table(earnings_data, colWidths=[col_width*0.6, col_width*0.4])
    earnings_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), TEAL_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#d1fae5')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
    ]))
    
    deductions_table = Table(deductions_data, colWidths=[col_width*0.6, col_width*0.4])
    deductions_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), CORAL_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fee2e2')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
    ]))
    
    two_column_table = Table([[earnings_table, deductions_table]], colWidths=[col_width, col_width])
    two_column_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(two_column_table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    net_pay_table = Table([
        ['NET PAY', f"P{net_pay:,.2f}"]
    ], colWidths=[5*inch, 2*inch])
    net_pay_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BACKGROUND', (0, 0), (-1, -1), TEAL_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, -1), white),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(net_pay_table)
    
    elements.append(Spacer(1, 0.4*inch))
    
    total_employer = sss_er + philhealth_er + pagibig_er
    
    company_title = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=HexColor('#4f46e5'),
        fontName='Helvetica-Bold',
        spaceBefore=12,
        spaceAfter=8,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("COMPANY CONTRIBUTIONS", company_title))
    
    company_subtitle = ParagraphStyle(
        'CompanySubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=DARK_GRAY,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    elements.append(Paragraph("(Employer Share - Paid by Company, NOT Deducted from Employee)", company_subtitle))
    
    employer_data = [
        ['Contribution Type', 'Amount'],
        ['SSS (ER Share + EC)', f"P{sss_er:,.2f}"],
        ['PhilHealth (ER Share)', f"P{philhealth_er:,.2f}"],
        ['Pag-IBIG (ER Share)', f"P{pagibig_er:,.2f}"],
        ['TOTAL COMPANY CONTRIBUTION', f"P{total_employer:,.2f}"],
    ]
    
    employer_table = Table(employer_data, colWidths=[5*inch, 2*inch])
    employer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#e0e7ff')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
    ]))
    elements.append(employer_table)
    
    elements.append(Spacer(1, 0.5*inch))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#9ca3af'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph("This is a computer-generated payslip. No signature required.", footer_style))
    elements.append(Paragraph("For questions, please contact HR or Payroll Department.", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
