from pydantic import BaseModel
from typing import List, Optional

class OptionBase(BaseModel):
    text: str
    is_correct: bool

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserDisplay(UserBase):
    id: int
    role: str
    is_approved: bool
    class Config:
        orm_mode = True

class OptionCreate(OptionBase):
    pass

class Option(OptionBase):
    id: int
    question_id: int
    class Config:
        orm_mode = True

class QuestionBase(BaseModel):
    text: str
    time_limit: int = 20
    points: int = 1000
    question_type: str = "multiple_choice"
    image_url: Optional[str] = None

class QuestionCreate(QuestionBase):
    options: List[OptionCreate]

class Question(QuestionBase):
    id: int
    quiz_id: int
    options: List[Option]
    class Config:
        orm_mode = True

class QuizBase(BaseModel):
    title: str
    description: Optional[str] = None
    theme: str = "standard"

class QuizCreate(QuizBase):
    questions: List[QuestionCreate]

class Quiz(QuizBase):
    id: int
    questions: List[Question]
    class Config:
        orm_mode = True
