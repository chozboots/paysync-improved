from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging
from flask import current_app

    
logger = logging.getLogger(__name__)
        
def construct_email(to_emails: list, template_id: str, template_data: dict) -> Mail:
    from_email = (current_app.config['SUPPORT_EMAIL'], current_app.config['COMPANY_NAME'])
    message = Mail(
        from_email=from_email,
        to_emails=to_emails,
        is_multiple=True
    )
    message.template_id = template_id
    message.dynamic_template_data = template_data
    return message

def send_email(message: Mail) -> None:
    try:
        sendgrid_client = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
        sendgrid_client.send(message)
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
