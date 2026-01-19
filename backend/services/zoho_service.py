"""
Zoho Mail Service - IMAP/SMTP integration
"""
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import ssl
from typing import List, Dict, Optional, Tuple
import uuid

from config import settings


class ZohoMailService:
    """Service for interacting with Zoho Mail via IMAP and SMTP"""

    def __init__(self, email: str = None, app_password: str = None):
        self.email = email or settings.ZOHO_EMAIL
        self.app_password = app_password or settings.ZOHO_APP_PASSWORD
        self.imap_server = settings.IMAP_SERVER
        self.imap_port = settings.IMAP_PORT
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server"""
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, ssl_context=context)
        mail.login(self.email, self.app_password)
        return mail

    def connect_smtp(self) -> smtplib.SMTP_SSL:
        """Connect to SMTP server"""
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
        server.login(self.email, self.app_password)
        return server

    def fetch_emails(self, count: int = 100, folder: str = "INBOX") -> List[Dict]:
        """Fetch emails from Zoho Mail

        Args:
            count: Number of emails to fetch
            folder: Folder to fetch from (default: INBOX)

        Returns:
            List of email dictionaries
        """
        emails = []
        try:
            mail = self.connect_imap()
            mail.select(folder)

            # Search for all emails
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()

            # Get the most recent emails
            email_ids = email_ids[-count:] if len(email_ids) > count else email_ids

            for email_id in reversed(email_ids):
                try:
                    # Fetch the email
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue

                    # Parse the email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Extract email data
                    email_data = self._parse_email(msg, str(email_id, 'utf-8'))
                    emails.append(email_data)

                except Exception as e:
                    print(f"Error parsing email {email_id}: {e}")
                    continue

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"Error fetching emails: {e}")

        return emails

    def _parse_email(self, msg, zoho_id: str) -> Dict:
        """Parse email message

        Args:
            msg: Email message object
            zoho_id: Zoho email ID

        Returns:
            Parsed email dictionary
        """
        # Extract subject
        subject = ""
        if msg["Subject"]:
            subject_parts = decode_header(msg["Subject"])
            subject = ""
            for part, encoding in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or "utf-8", errors="ignore")
                else:
                    subject += part

        # Extract sender
        from_address = msg.get("From", "")
        from_name = ""
        if "<" in from_address:
            from_name = from_address.split("<")[0].strip().strip('"')
            from_address = from_address.split("<")[1].strip(">")

        # Extract recipient
        to_address = msg.get("To", "")

        # Extract date
        date_str = msg.get("Date", "")
        received_at = datetime.utcnow()
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str)
        except:
            pass

        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except:
                        try:
                            body = part.get_payload(decode=True).decode("gbk", errors="ignore")
                        except:
                            pass
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except:
                body = str(msg.get_payload())

        return {
            "zoho_id": zoho_id,
            "from_address": from_address,
            "from_name": from_name or from_address.split("@")[0],
            "to_address": to_address,
            "subject": subject,
            "body": body,
            "received_at": received_at
        }

    def send_email(self, to_address: str, subject: str, body: str, in_reply_to: str = None) -> bool:
        """Send an email via SMTP

        Args:
            to_address: Recipient email address
            subject: Email subject
            body: Email body
            in_reply_to: Message-ID of the email being replied to

        Returns:
            True if successful
        """
        try:
            server = self.connect_smtp()

            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_address
            msg["Subject"] = subject
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Send
            server.sendmail(self.email, to_address, msg.as_string())
            server.quit()

            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """Test the connection to Zoho Mail

        Returns:
            Tuple of (success, message)
        """
        try:
            mail = self.connect_imap()
            mail.select("INBOX")
            mail.close()
            mail.logout()
            return True, "Successfully connected to Zoho Mail"
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg:
                return False, "Authentication failed: Invalid email or app password. Please check:\n1. Email address is correct\n2. You're using the App Password (not login password)\n3. App Password is copied correctly (16 characters with dashes)"
            return False, f"IMAP error: {error_msg}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_email_count(self, folder: str = "INBOX") -> int:
        """Get the number of emails in a folder

        Args:
            folder: Folder to check

        Returns:
            Number of emails
        """
        try:
            mail = self.connect_imap()
            mail.select(folder)
            status, messages = mail.search(None, "ALL")
            mail.close()
            mail.logout()

            if status == "OK":
                return len(messages[0].split())
            return 0

        except Exception as e:
            print(f"Error getting email count: {e}")
            return 0


def create_zoho_service(email: str = None, app_password: str = None) -> ZohoMailService:
    """Factory function to create ZohoMailService instance"""
    return ZohoMailService(email, app_password)
