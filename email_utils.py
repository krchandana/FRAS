import os
import ssl
import smtplib
from email.message import EmailMessage

try:
    import mail_config
except ImportError:
    mail_config = None


def get_email_settings():
    config = mail_config
    return {
        'server': os.getenv('MAIL_SERVER', getattr(config, 'MAIL_SERVER', 'smtp.gmail.com')),
        'port': int(os.getenv('MAIL_PORT', str(getattr(config, 'MAIL_PORT', 587)))),
        'username': os.getenv('MAIL_USERNAME', getattr(config, 'MAIL_USERNAME', '')).strip(),
        'password': os.getenv('MAIL_PASSWORD', getattr(config, 'MAIL_PASSWORD', '')).strip(),
        'from_email': os.getenv('MAIL_FROM', getattr(config, 'MAIL_FROM', '')).strip(),
        'use_tls': os.getenv(
            'MAIL_USE_TLS',
            str(getattr(config, 'MAIL_USE_TLS', True))
        ).strip().lower() in {'1', 'true', 'yes', 'on'},
    }


def is_email_configured():
    settings = get_email_settings()
    return bool(settings['username'] and settings['password'])


def send_email(recipient, subject, body, is_html=False):
    if not recipient:
        return False, 'Recipient email is missing'

    settings = get_email_settings()
    if not settings['username'] or not settings['password']:
        return False, 'Email settings are not configured'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings['from_email'] or settings['username']
    msg['To'] = recipient
    
    if is_html:
        msg.set_content(body, subtype='html')
    else:
        msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings['server'], settings['port']) as smtp:
            smtp.ehlo()
            if settings['use_tls']:
                smtp.starttls(context=context)
                smtp.ehlo()
            smtp.login(settings['username'], settings['password'])
            smtp.send_message(msg)
        return True, None
    except smtplib.SMTPAuthenticationError as exc:
        return False, f'Authentication failed. Check MAIL_USERNAME/MAIL_PASSWORD and use a Gmail app password if needed: {exc}'
    except Exception as exc:
        return False, str(exc)
