from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from urllib.parse import urlparse

# Parse the MySQL URL from environment
mysql_url = os.getenv('MYSQL_PUBLIC_URL')
parsed = urlparse(mysql_url)

# Construct Database URL for SQLAlchemy
DATABASE_URL = f"mysql+mysqlconnector://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 3306}/{parsed.path.lstrip('/')}"

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    mobile_number = Column(String(20), unique=True, index=True, nullable=False)
    age = Column(Integer)
    blood_group = Column(String(10))
    allergies = Column(Text)
    email = Column(String(255))  # Added email field
    created_at = Column(DateTime, default=datetime.utcnow)
    
    consultations = relationship("Consultation", back_populates="patient")

class Consultation(Base):
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    consultation_date = Column(DateTime, default=datetime.utcnow)
    symptoms = Column(Text, nullable=False)
    symptoms_duration = Column(String(100))
    patient_summary = Column(Text)
    doctor_summary = Column(Text)
    
    patient = relationship("Patient", back_populates="consultations")

class DatabaseManager:
    def __init__(self):
        self.SessionLocal = SessionLocal

    def get_db(self):
        db = self.SessionLocal()
        try:
            return db
        finally:
            db.close()

    async def create_or_update_patient(self, db, mobile_number: str, name: str, age: int, 
                                     blood_group: str = None, allergies: str = None,
                                     email: str = None) -> Patient:  # Added email parameter
        try:
            mobile_number = mobile_number.replace('whatsapp:', '')
            patient = db.query(Patient).filter(Patient.mobile_number == mobile_number).first()
            
            if patient:
                patient.name = name
                patient.age = age
                patient.blood_group = blood_group
                patient.allergies = allergies
                patient.email = email  # Update email
            else:
                patient = Patient(
                    mobile_number=mobile_number,
                    name=name,
                    age=age,
                    blood_group=blood_group,
                    allergies=allergies,
                    email=email  # Add email to new patient
                )
                db.add(patient)
            
            db.commit()
            db.refresh(patient)
            return patient
            
        except Exception as e:
            db.rollback()
            raise

    async def create_consultation(self, db, patient_id: int, symptoms: str, 
                                symptoms_duration: str, patient_summary: str, 
                                doctor_summary: str) -> Consultation:
        try:
            consultation = Consultation(
                patient_id=patient_id,
                symptoms=symptoms,
                symptoms_duration=symptoms_duration,
                patient_summary=patient_summary,
                doctor_summary=doctor_summary
            )
            
            db.add(consultation)
            db.commit()
            db.refresh(consultation)
            return consultation
            
        except Exception as e:
            db.rollback()
            raise

def init_db():
    Base.metadata.create_all(bind=engine)

# Initialize database manager
db_manager = DatabaseManager()