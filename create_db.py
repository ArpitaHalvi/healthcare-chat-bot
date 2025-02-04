from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Database Configuration
def get_database_url():
    # Get the MySQL URL from environment
    mysql_url = os.getenv('MYSQL_PUBLIC_URL')
    
    if not mysql_url:
        raise ValueError("MYSQL_PUBLIC_URL environment variable is not set")
    
    # Parse the URL to get components
    parsed = urlparse(mysql_url)
    
    # Extract host and port from netloc
    host = parsed.hostname
    port = parsed.port or 3306
    
    # Construct proper SQLAlchemy URL
    db_url = f"mysql+mysqlconnector://{parsed.username}:{parsed.password}@{host}:{port}/{parsed.path.lstrip('/')}"
    
    print("\nDatabase Connection Details:")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {parsed.path.lstrip('/')}")
    
    return db_url

# Create base class for declarative models
Base = declarative_base()

# Define Patient model
class Patient(Base):
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    mobile_number = Column(String(20), unique=True, nullable=False, index=True)
    age = Column(Integer)
    blood_group = Column(String(10))
    allergies = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    consultations = relationship("Consultation", back_populates="patient")

# Define Consultation model
class Consultation(Base):
    __tablename__ = 'consultations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    consultation_date = Column(DateTime, default=datetime.utcnow)
    symptoms = Column(Text, nullable=False)
    symptoms_duration = Column(String(100))
    patient_summary = Column(Text)
    doctor_summary = Column(Text)
    
    # Relationship
    patient = relationship("Patient", back_populates="consultations")

def create_tables():
    try:
        # Get database URL
        db_url = get_database_url()
        print("\nAttempting to connect to database...")
        
        # Create database engine
        engine = create_engine(db_url)
        
        print("Creating tables...")
        # Create all tables
        Base.metadata.create_all(engine)
        print("Tables created successfully!")
        
        # Print table information
        for table in Base.metadata.sorted_tables:
            print(f"\nTable: {table.name}")
            print("Columns:")
            for column in table.columns:
                nullable = "NULL" if column.nullable else "NOT NULL"
                default = f"DEFAULT {column.default.arg}" if column.default else ""
                print(f"  - {column.name}: {column.type} {nullable} {default}")
        
        return True
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    print("Starting database setup...")
    
    # Create tables
    success = create_tables()
    
    if success:
        print("\nDatabase setup completed successfully!")
    else:
        print("\nDatabase setup failed!")