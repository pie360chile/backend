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
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      
      <!-- Logo Header -->
      <div style="background-color: #2c3e50; padding: 30px 20px; text-align: center;">
        <img src="https://pie-360-chile-frontend.web.app/logo.webp" 
             alt="PIE360 Logo" 
             style="max-width: 150px; height: auto;">
      </div>
      
      <!-- Content -->
      <div style="padding: 30px 20px;">
        <h2 style="color: #2c3e50; margin-top: 0; margin-bottom: 20px; font-size: 24px;">
          Nueva Solicitud de Reunión
        </h2>
        
        <div style="margin: 20px 0; background-color: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 4px solid #3498db;">
          <p style="margin: 10px 0;"><strong style="color: #2c3e50;">Nombres:</strong> {meeting_data.get('names', 'N/A')}</p>
          <p style="margin: 10px 0;"><strong style="color: #2c3e50;">Apellidos:</strong> {meeting_data.get('lastnames', 'N/A')}</p>
          <p style="margin: 10px 0;"><strong style="color: #2c3e50;">Email:</strong> {meeting_data.get('email', 'N/A')}</p>
          <p style="margin: 10px 0;"><strong style="color: #2c3e50;">Teléfono:</strong> {meeting_data.get('celphone', 'N/A')}</p>
          <p style="margin: 10px 0;"><strong style="color: #2c3e50;">Horario:</strong> {horario}</p>
        </div>
        
        <div style="background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
          <h3 style="margin-top: 0; color: #856404; font-size: 18px;">Motivo de la Reunión:</h3>
          <p style="white-space: pre-wrap; color: #856404; margin-bottom: 0;">{meeting_data.get('reason', 'Sin motivo especificado')}</p>
        </div>
      </div>
      
      <!-- Footer -->
      <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
        <p style="font-size: 12px; color: #7f8c8d; margin: 0;">
          Este es un correo automático del sistema PIE360
        </p>
        <p style="font-size: 11px; color: #95a5a6; margin: 5px 0 0 0;">
          © {datetime.now().year} PIE360 - Todos los derechos reservados
        </p>
      </div>
      
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
