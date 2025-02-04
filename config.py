from dotenv import load_dotenv
import os

load_dotenv()

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
NGROK_TOKEN = os.getenv("NGROK_TOKEN")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_PUBLIC_URL'),
    'user': os.getenv('MYSQLUSER'),
    'password': os.getenv('MYSQLPASSWORD'),
    'port': os.getenv('MYSQLPORT'),
    'database': os.getenv('MYSQLDATABASE')
}