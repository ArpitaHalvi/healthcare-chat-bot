# mail.py
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import List
from dotenv import load_dotenv
import os
import ssl
import requests

# Load environment variables from .env file
load_dotenv()

class EmailSender:
    def __init__(self, from_email: str):
        """
        Initialize the EmailSender with SendGrid API key from .env and sender email
        """
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            raise ValueError("SENDGRID_API_KEY not found in .env file")
            
        # Initialize SendGrid client
        session = requests.Session()
        session.verify = False
        self.client = SendGridAPIClient(api_key=api_key, http_client=session)
        self.from_email = from_email

    def send_email(self, to_emails: List[str], subject: str, content: str, is_html: bool = True) -> bool:
        """
        Send an email to one or more recipients
        """
        try:
            # Create the email message
            message = Mail(
                from_email=self.from_email,
                to_emails=to_emails,
                subject=subject,
                html_content=content if is_html else None,
                plain_text_content=None if is_html else content
            )
            
            # Send the email
            response = self.client.send(message)
            
            # Check if send was successful
            if response.status_code in [200, 201, 202]:
                print(f"✓ Email sent successfully to {', '.join(to_emails)}")
                return True
            else:
                print(f"⨯ Failed to send email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⨯ Error sending email: {str(e)}")
            return False

if __name__ == "__main__":
    try:
        # Example usage
        sender = EmailSender(
            from_email='iam@robosushie.com'
        )
        
        # Example HTML email
        html_content = """
        <h2>Test Email</h2>
        <p>This is a test email sent using SendGrid.</p>
        <p><em>Have a great day!</em></p>
        """
        
        # Send the email
        sender.send_email(
            to_emails=['ssamuel.sushant@gmail.com'],
            subject='Test Email from SendGrid',
            content=html_content,
            is_html=True
        )
    except Exception as e:
        print(f"Error: {str(e)}")