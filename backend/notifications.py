import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import requests
from config import settings

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manage email and Telegram notifications."""
    
    @staticmethod
    def send_email(subject: str, message: str) -> bool:
        """Send email notification."""
        if not settings.email_enabled:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.email_user
            msg['To'] = settings.email_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(settings.email_host, settings.email_port)
            server.starttls()
            server.login(settings.email_user, settings.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent: {subject}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    @staticmethod
    def send_telegram(message: str) -> bool:
        """Send Telegram notification."""
        if not settings.telegram_enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                logger.info("Telegram message sent")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    @staticmethod
    def notify_trade(symbol: str, side: str, quantity: float, price: float):
        """Send notification about executed trade."""
        subject = f"Trade Executed: {side} {symbol}"
        message = f"""
        Trade Execution Alert
        
        Symbol: {symbol}
        Side: {side}
        Quantity: {quantity}
        Price: {price}
        Total: {quantity * price} USDT
        """
        
        NotificationManager.send_email(subject, message)
        NotificationManager.send_telegram(f"<b>{subject}</b>\n{message}")