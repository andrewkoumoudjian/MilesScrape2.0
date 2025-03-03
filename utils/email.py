import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging
from config import active_config as config

logger = logging.getLogger(__name__)

def send_email(recipient, subject, body, attachments=None):
    """
    Send an email notification with optional attachments
    
    Args:
        recipient (str): Email address of recipient
        subject (str): Email subject
        body (str): Email body
        attachments (list): List of file paths to attach
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not config.MAIL_USERNAME or not config.MAIL_PASSWORD:
        logger.error("Email credentials not configured. Cannot send email.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = config.MAIL_DEFAULT_SENDER
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={file_path.split('/')[-1]}",
                    )
                    msg.attach(part)
                except Exception as e:
                    logger.error(f"Failed to attach file {file_path}: {str(e)}")
        
        # Connect to SMTP server
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_lead_notification(user_email, lead_count, search_query, csv_url=None):
    """Send notification about new leads"""
    subject = f"LeadBot: {lead_count} new leads found"
    
    body = f"Your search for '{search_query}' found {lead_count} leads.\n\n"
    
    if csv_url:
        body += f"View or download your leads: {csv_url}\n\n"
    
    body += "Thank you for using LeadBot!"
    
    return send_email(user_email, subject, body)