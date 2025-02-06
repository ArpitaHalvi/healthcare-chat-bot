from fastapi import FastAPI, Request, Response

from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, Content

from typing import List
import json

from db import init_db, db_manager
from config import GOOGLE_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, SENDGRID_API_KEY

# Initialize database
init_db()

app = FastAPI()

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize LangChain with Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.7
)

MEDICAL_QUESTIONS = [
    "What is your name?",
    "What is your age?",
    "What is your blood group?",
    "Do you have any known allergies? If yes, please list them.",
    "What symptoms are you currently experiencing?",
    "How long have you been experiencing these symptoms?",
    "Are you currently taking any medications? If yes, please list them.",
    "Do you have any previous medical conditions or surgeries?",
    "Have you experienced these symptoms before?",
    "Do you have an email address? If yes, please enter you email address, else enter no/No"
]

class EmailService:
    def __init__(self, api_key: str, from_email: str):
        self.from_email = from_email
        self.client = SendGridAPIClient(api_key=api_key)

    async def send_email(self, to_emails: List[str], subject: str, content: str) -> bool:
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=[To(email) for email in to_emails],
                subject=subject,
                html_content=Content("text/html", content)
            )
            
            response = self.client.send(message)
            
            if response.status_code not in [200, 201, 202]:
                print(f"Email send failed with status code: {response.status_code}")
                return False
                
            print(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

class ChatSession:
    def __init__(self):
        self.current_question = 0
        self.answers = {}
        self.conversation_end = False
        self.clarification_asked = set()
        self.messages = [
            SystemMessage(content="""You are a medical consultation chatbot. 
            Your role is to gather information from patients and provide initial 
            assessments while maintaining a professional and caring demeanor.""")
        ]

    async def validate_answer(self, question: str, answer: str) -> tuple[bool, str]:
        if question in self.clarification_asked and answer.strip():
            return True, ""

        if not answer.strip():
            return False, "Please provide a response."

        try:
            if question == "What's your age?":
                if not answer.replace('years', '').replace('old', '').strip().isdigit():
                    if question not in self.clarification_asked:
                        self.clarification_asked.add(question)
                        return False, "Please provide your age in years."
                    return True, ""

            elif question == "What symptoms are you currently experiencing?":
                if len(answer.split()) < 2 and question not in self.clarification_asked:
                    self.clarification_asked.add(question)
                    return False, "Please briefly describe what health issues you're experiencing."
                return True, ""

            response = await llm.ainvoke(
                self.messages + [HumanMessage(content=f"""
                Quick check - is this answer somewhat relevant to the question: "{question}"
                Answer: "{answer}"
                If it's completely irrelevant, respond with #INCORRECT#.
                Otherwise respond with #VALID#.
                Keep it simple, no explanations needed.
                """)]
            )
            
            is_valid = "#VALID#" in response.content.upper()
            if not is_valid and question not in self.clarification_asked:
                self.clarification_asked.add(question)
                return False, f"Please provide a relevant answer to: {question}"
            return True, ""

        except Exception:
            return True, ""

    async def generate_summary(self) -> str:
        try:
            response = await llm.ainvoke(
                self.messages + [HumanMessage(content=f"""
                Based on this consultation, provide:
                1. Brief summary of condition
                2. Basic recommendations
                3. Whether immediate medical attention is needed
                
                Details: {json.dumps(self.answers, indent=2)}
                
                Keep it simple and clear.
                """)]
            )
            return response.content
        except Exception:
            return "Unable to generate summary. Please contact medical support."

    async def generate_doctor_summary(self, patient_summary: str) -> str:
        try:
            response = await llm.ainvoke(
                self.messages + [HumanMessage(content=f"""
                Create a clinical summary:
                1. Patient condition overview
                2. Key symptoms and duration
                3. Relevant medical history
                4. Recommendations
                
                Patient Details: {json.dumps(self.answers, indent=2)}
                Patient Summary: {patient_summary}
                """)]
            )
            return response.content
        except Exception:
            return "Error generating medical summary."

# In-memory storage for chat sessions
chat_sessions = {}

# Initialize email service
email_service = EmailService(
    api_key=SENDGRID_API_KEY,
    from_email='iam@robosushie.com'
)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        form_data = await request.form()
        # print(form_data)
        incoming_msg = form_data.get('Body', '').strip()
        sender = form_data.get('From', '').replace('whatsapp:', '')
        
        response = MessagingResponse()
        db = db_manager.get_db()
        
        if sender not in chat_sessions:
            chat_sessions[sender] = ChatSession()
            welcome_msg = (
                "Hello! I'm your medical consultation bot. I'll ask you a few "
                "questions to understand your condition better. Please answer them accurately.\n\n"
                + MEDICAL_QUESTIONS[0]
            )
            response.message(welcome_msg)
            return Response(content=str(response), media_type="application/xml")
        
        session = chat_sessions[sender]
        
        if session.conversation_end:
            response.message("Your consultation has ended. Say 'Hi' to start a new consultation.")
            return Response(content=str(response), media_type="application/xml")
        
        is_valid, validation_msg = await session.validate_answer(
            MEDICAL_QUESTIONS[session.current_question],
            incoming_msg
        )
        
        if not is_valid:
            response.message(validation_msg)
            return Response(content=str(response), media_type="application/xml")
        
        session.answers[MEDICAL_QUESTIONS[session.current_question]] = incoming_msg
        session.current_question += 1
        
        if session.current_question < len(MEDICAL_QUESTIONS):
            response.message(MEDICAL_QUESTIONS[session.current_question])
        else:
            # Generate summaries
            patient_summary = await session.generate_summary()
            doctor_summary = await session.generate_doctor_summary(patient_summary)
            
            try:
                # Save patient info to database
                patient = await db_manager.create_or_update_patient(
                    db=db,
                    mobile_number=sender,
                    name=session.answers.get("What is your name?", "Unknown"),
                    age=int(session.answers.get("What is your age?", "0").replace('years', '').strip()),
                    blood_group=session.answers.get("What is your blood group?", None),
                    allergies=session.answers.get("Do you have any known allergies? If yes, please list them.", None),
                    email=session.answers.get("Do you have an email address? If yes, please enter you email address, else enter no/No", None)  
                )
                
                # Save consultation to database
                await db_manager.create_consultation(
                    db=db,
                    patient_id=patient.id,
                    symptoms=session.answers.get("What symptoms are you currently experiencing?", ""),
                    symptoms_duration=session.answers.get("How long have you been experiencing these symptoms?", ""),
                    patient_summary=patient_summary,
                    doctor_summary=doctor_summary
                )
            
            except Exception as db_error:
                print(f"Database error: {str(db_error)}")
            
            # Send email notification
            email_sent = await email_service.send_email(
                to_emails=["ssamuel.sushant@gmail.com"],
                subject=f"Medical Consultation Summary - {session.answers.get('What is your name?', 'Patient')}",
                content=f"""
                <h2>Medical Consultation Summary</h2>
                <p><strong>Patient Name:</strong> {session.answers.get('What is your name?', 'Unknown')}</p>
                <hr>
                <h3>Doctor's Summary:</h3>
                <p>{doctor_summary}</p>
                <hr>
                <h3>Raw Consultation Data:</h3>
                <pre>{json.dumps(session.answers, indent=2)}</pre>
                """
            )
            
            if not email_sent:
                print("Failed to send email notification")
            
            final_msg = (
                f"Consultation Summary:\n\n{patient_summary}\n\n"
                "Your consultation details have been sent to our medical team. "
                "They will contact you if immediate attention is needed. "
                "Say 'Hi' to start a new consultation."
            )
            response.message(final_msg)
            # session.conversation_end = True
            del chat_sessions[sender]
        
        return Response(content=str(response), media_type="application/xml")
            
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        response = MessagingResponse()
        response.message(
            "I apologize, but I encountered an error. Please try again by saying 'Hi'."
        )
        return Response(content=str(response), media_type="application/xml")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}