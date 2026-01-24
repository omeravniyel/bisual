from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    theme = Column(String, default="standard")
    settings = Column(JSON, default={})  # New: Store flexible settings
    user_id = Column(Integer, ForeignKey("users.id"))
    
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="quizzes")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String) # Storing plain for strict MVP, usually hash it
    role = Column(String, default="teacher") # 'teacher', 'super_admin'
    is_approved = Column(Boolean, default=False)
    reset_requested = Column(Boolean, default=False)
    
    # Enhanced Profile
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    quizzes = relationship("Quiz", back_populates="owner")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    text = Column(String)
    time_limit = Column(Integer, default=20) # seconds
    points = Column(Integer, default=1000)
    image_url = Column(String, nullable=True) # For future media support
    question_type = Column(String, default="multiple_choice") # multiple_choice, true_false
    
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    quiz = relationship("Quiz", back_populates="questions")

class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    text = Column(String)
    is_correct = Column(Boolean, default=False)
    
    question = relationship("Question", back_populates="options")
