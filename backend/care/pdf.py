"""Render a medical record to PDF using reportlab."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


_FONT_DIR = Path(__file__).resolve().parent.parent / 'static' / 'fonts'
_FONT_REGULAR = _FONT_DIR / 'DejaVuSans.ttf'
_FONT_BOLD = _FONT_DIR / 'DejaVuSans-Bold.ttf'
if _FONT_REGULAR.exists() and _FONT_BOLD.exists():
    pdfmetrics.registerFont(TTFont('HealthSans', str(_FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont('HealthSans-Bold', str(_FONT_BOLD)))
    PDF_FONT = 'HealthSans'
    PDF_BOLD = 'HealthSans-Bold'
else:
    # Keep local/dev installs usable when the optional font files are absent.
    PDF_FONT = 'Helvetica'
    PDF_BOLD = 'Helvetica-Bold'


def _safe(value):
    return escape(str(value or '—'))


def _label_value(label, value):
    return Paragraph(
        f'<font name="{PDF_BOLD}">{_safe(label)}:</font> {_safe(value)}',
        ParagraphStyle('label', parent=getSampleStyleSheet()['BodyText'], fontName=PDF_FONT, fontSize=10, leading=14),
    )


def build_patient_health_report_pdf(patient):
    """Return a comprehensive PDF summary of a patient's health data."""
    from care.models import Alert, MedicalRecord, VitalSign

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f'Patient health report #{patient.pk}')
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('report-title', parent=styles['Title'], fontName=PDF_BOLD)
    h2 = ParagraphStyle('report-heading', parent=styles['Heading2'], fontName=PDF_BOLD,
                        textColor=colors.HexColor('#0f766e'))
    body = ParagraphStyle('report-body', parent=styles['BodyText'], fontName=PDF_FONT, fontSize=9, leading=12)
    vitals = VitalSign.objects.filter(patient=patient).order_by('-recorded_at')[:100]
    records = MedicalRecord.objects.filter(patient=patient).select_related('doctor', 'disease').order_by('-created_at')[:50]
    alerts = Alert.objects.filter(patient=patient).order_by('-created_at')[:50]
    story = [Paragraph(_safe('Health Care Monitor — Báo cáo sức khỏe tổng hợp'), h1), Spacer(1, 4 * mm)]
    story.append(Paragraph(f'<font name="{PDF_BOLD}">Bệnh nhân:</font> {_safe(patient.get_full_name() or patient.username)}', body))
    story.append(Paragraph(f'<font name="{PDF_BOLD}">Email:</font> {_safe(patient.email)}', body))
    story.extend([Spacer(1, 4 * mm), Paragraph(_safe('Sinh hiệu gần đây'), h2)])
    rows = [[_safe('Thời gian'), _safe('Nhiệt độ'), _safe('Nhịp tim'), _safe('HA'), _safe('SpO₂'), _safe('Cân nặng'), _safe('Đường huyết')]]
    for vital in vitals:
        rows.append([vital.recorded_at.strftime('%d/%m/%Y %H:%M'), vital.temperature or '—', vital.heart_rate or '—',
                     f'{vital.blood_pressure_sys or "—"}/{vital.blood_pressure_dia or "—"}', vital.oxygen_saturation or '—',
                     vital.weight_kg or '—', vital.blood_glucose or '—'])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), PDF_BOLD), ('FONTNAME', (0, 1), (-1, -1), PDF_FONT),
                               ('FONTSIZE', (0, 0), (-1, -1), 7), ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                               ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dff5ef'))]))
    story.append(table)
    story.extend([Spacer(1, 4 * mm), Paragraph(_safe('Cảnh báo'), h2)])
    story.extend(Paragraph(_safe(f'{a.created_at.strftime("%d/%m/%Y %H:%M")} — {a.title}: {a.message}'), body) for a in alerts)
    if not alerts:
        story.append(Paragraph(_safe('Không có cảnh báo.'), body))
    story.extend([Spacer(1, 4 * mm), Paragraph(_safe('Hồ sơ bệnh án'), h2)])
    for record in records:
        doctor = record.doctor.get_full_name() if record.doctor else '—'
        story.append(Paragraph(_safe(f'{record.created_at.strftime("%d/%m/%Y")} — {record.title} — Bác sĩ: {doctor}'), body))
        if record.diagnosis:
            story.append(Paragraph(_safe(f'Chẩn đoán: {record.diagnosis}'), body))
    if not records:
        story.append(Paragraph(_safe('Chưa có hồ sơ bệnh án.'), body))
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_medical_record_pdf(record):
    """Return a PDF byte string for the given MedicalRecord instance."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f'Medical record #{record.pk}',
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('title', parent=styles['Title'], fontName=PDF_BOLD)
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontName=PDF_BOLD, textColor=colors.HexColor('#0f766e'))
    body = ParagraphStyle('body', parent=styles['BodyText'], fontName=PDF_FONT, fontSize=10, leading=14, spaceAfter=4)

    patient_name = record.patient.get_full_name() or record.patient.username
    doctor_name = record.doctor.get_full_name() if record.doctor else '—'
    disease_name = record.disease.name_vi if record.disease else '—'
    created_at = record.created_at.strftime('%d/%m/%Y %H:%M')
    updated_at = record.updated_at.strftime('%d/%m/%Y %H:%M')

    info = [
        [_label_value('Bệnh nhân', patient_name), _label_value('Bác sĩ', doctor_name)],
        [_label_value('Bệnh', disease_name), _label_value('Mã hồ sơ', f'#{record.pk}')],
        [_label_value('Ngày tạo', created_at), _label_value('Cập nhật', updated_at)],
    ]
    info_table = Table(info, colWidths=[85 * mm, 85 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )

    def section(title, content):
        text = _safe(content).replace('\n', '<br/>')
        return [Spacer(1, 4 * mm), Paragraph(_safe(title), h2), Paragraph(text, body)]

    story = [
        Paragraph(_safe('Health Care Monitor — Hồ sơ bệnh án'), h1),
        Spacer(1, 4 * mm),
        Paragraph(f'<font name="{PDF_BOLD}">Tiêu đề:</font> {_safe(record.title)}', body),
        info_table,
        *section('Chẩn đoán', record.diagnosis),
        *section('Đơn thuốc', record.prescription),
        *section('Ghi chú', record.notes),
    ]
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
