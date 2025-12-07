from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime

class ActionIncidentPDFClass:
    def __init__(self):
        self.buffer = BytesIO()
        self.width, self.height = letter
        
    def generate_pdf(self, data):
        """
        Genera un PDF con el formato de Ficha de Registro de Acción/Incidente
        """
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para subtítulos
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para texto normal
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            alignment=TA_JUSTIFY,
            leading=14
        )
        
        # Título principal
        title = Paragraph("Registro de acciones e incidencias", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Información del estudiante (primera tabla)
        student_info_data = [
            ['Nombre', data.get('student_name', '')],
            ['RUT', data.get('student_rut', '')],
            ['Fecha Nacimiento', data.get('birth_date', '')],
            ['Edad', data.get('age', '')],
            ['NEE', data.get('nee', '')],
            ['Curso', data.get('course_name', 'Sin curso')],
            ['Establecimiento', data.get('school_name', '')],
        ]
        
        student_table = Table(student_info_data, colWidths=[2*inch, 5.2*inch])
        student_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(student_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Título del incidente
        incident_title = Paragraph(data.get('title', ''), subtitle_style)
        elements.append(incident_title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Información del registro (segunda tabla)
        registro_data = [
            ['Profesional registrador', data.get('professional_name', '')],
            ['Tipo', data.get('action_type_name', '')],
            ['Estado', data.get('status_name', '')],
            ['Fecha/hora', f"{data.get('incident_date', '')} {data.get('incident_time', '')}"],
        ]
        
        registro_table = Table(registro_data, colWidths=[2*inch, 5.2*inch])
        registro_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(registro_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Antecedentes
        elements.append(Paragraph("<b>Antecedentes</b>", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))
        background_text = Paragraph(data.get('background', ''), normal_style)
        elements.append(background_text)
        elements.append(Spacer(1, 0.2*inch))
        
        # Conducta
        elements.append(Paragraph("<b>Conducta</b>", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))
        conduct_text = Paragraph(data.get('conduct', ''), normal_style)
        elements.append(conduct_text)
        elements.append(Spacer(1, 0.2*inch))
        
        # Consecuencias
        elements.append(Paragraph("<b>Consecuencias</b>", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))
        consequences_text = Paragraph(data.get('consequences', ''), normal_style)
        elements.append(consequences_text)
        elements.append(Spacer(1, 0.2*inch))
        
        # Recomendaciones
        elements.append(Paragraph("<b>Recomendaciones</b>", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))
        recommendations_text = Paragraph(data.get('recommendations', ''), normal_style)
        elements.append(recommendations_text)
        elements.append(Spacer(1, 0.5*inch))
        
        # Firma del profesional (centrado)
        elements.append(Spacer(1, 0.3*inch))
        
        signature_style = ParagraphStyle(
            'Signature',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph("_____________________________", signature_style))
        elements.append(Paragraph(data.get('professional_name', ''), signature_style))
        elements.append(Paragraph(f"RUT: {data.get('professional_rut', '')}", signature_style))
        
        # Construir PDF
        doc.build(elements)
        
        # Obtener el valor del buffer
        pdf = self.buffer.getvalue()
        self.buffer.close()
        
        return pdf
