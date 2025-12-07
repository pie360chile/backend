import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailClass:
    def __init__(self):
        # Configuración SMTP - Gmail
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "pie360chile@gmail.com"
        self.sender_password = "ebpp etlh zgpf ohcv"
        
    def send_meeting_notification(self, meeting_data):
        """
        Envía notificación de reunión a pie360chile@gmail.com
        """
        try:
            receiver_email = "pie360chile@gmail.com"
            
            # Determinar el horario según schedule_id
            schedule_id = meeting_data.get('schedule_id')
            if schedule_id == 1:
                horario = "Mañana"
            elif schedule_id == 2:
                horario = "Tarde"
            else:
                horario = f"Schedule ID: {schedule_id}"
            
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Nueva Solicitud de Reunión de {meeting_data.get('names', '')} {meeting_data.get('lastnames', '')}"
            message["From"] = self.sender_email
            message["To"] = receiver_email
            
            # Contenido del correo en texto plano
            text = f"""
Nueva Solicitud de Reunión

Nombres: {meeting_data.get('names', 'N/A')}
Apellidos: {meeting_data.get('lastnames', 'N/A')}
Email: {meeting_data.get('email', 'N/A')}
Teléfono: {meeting_data.get('celphone', 'N/A')}
Horario: {horario}

Motivo:
{meeting_data.get('reason', 'Sin motivo especificado')}

---
Este es un correo automático del sistema PIE360.
"""
            
            # Contenido del correo en HTML
            html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
      <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
        Nueva Solicitud de Reunión
      </h2>
      
      <div style="margin: 20px 0;">
        <p><strong>Nombres:</strong> {meeting_data.get('names', 'N/A')}</p>
        <p><strong>Apellidos:</strong> {meeting_data.get('lastnames', 'N/A')}</p>
        <p><strong>Email:</strong> {meeting_data.get('email', 'N/A')}</p>
        <p><strong>Teléfono:</strong> {meeting_data.get('celphone', 'N/A')}</p>
        <p><strong>Horario:</strong> {horario}</p>
      </div>
      
      <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #2c3e50;">Motivo:</h3>
        <p style="white-space: pre-wrap;">{meeting_data.get('reason', 'Sin motivo especificado')}</p>
      </div>
      
      <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
      
      <p style="font-size: 12px; color: #7f8c8d; text-align: center;">
        Este es un correo automático del sistema PIE360.
      </p>
    </div>
  </body>
</html>
"""
            
            # Adjuntar las partes del mensaje
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Enviar correo
            print("=" * 50)
            print("ENVIANDO CORREO:")
            print(f"De: {self.sender_email}")
            print(f"Para: {receiver_email}")
            print(f"Asunto: {message['Subject']}")
            print("=" * 50)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, receiver_email, message.as_string())
            
            print("Correo enviado exitosamente!")
            print("=" * 50)
            
            return {
                "status": "success",
                "message": "Notificación enviada correctamente"
            }
            
        except Exception as e:
            print(f"Error enviando correo: {str(e)}")
            return {
                "status": "error",
                "message": f"Error al enviar notificación: {str(e)}"
            }
