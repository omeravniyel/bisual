from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/quizzes/", response_model=schemas.Quiz)
def create_quiz(quiz: schemas.QuizCreate, request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not user: raise HTTPException(status_code=401, detail="User not found")

    db_quiz = models.Quiz(
        title=quiz.title, 
        description=quiz.description, 
        theme=quiz.theme,
        user_id=user.id
    )
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)
    
    for q in quiz.questions:
        db_question = models.Question(
            quiz_id=db_quiz.id,
            text=q.text,
            time_limit=q.time_limit,
            points=q.points,
            question_type=q.question_type,
            image_url=q.image_url
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        for opt in q.options:
            db_option = models.Option(
                question_id=db_question.id,
                text=opt.text,
                is_correct=opt.is_correct
            )
            db.add(db_option)
        db.commit() # Commit options
        
    db.refresh(db_quiz)
    return db_quiz

@router.get("/quizzes/", response_model=List[schemas.Quiz])
def read_quizzes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    quizzes = db.query(models.Quiz).offset(skip).limit(limit).all()
    return quizzes

@router.get("/quizzes/{quiz_id}", response_model=schemas.Quiz)
def read_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

def check_auth(request: Request):
    user = request.cookies.get("user_session")
    if not user:
        raise HTTPException(status_code=303, detail="Not authenticated") # Will be caught by exception handler or just redirect manually
    return user

@router.get("/create", response_class=HTMLResponse)
async def create_quiz_page(request: Request):
    user = request.cookies.get("user_session")
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("create_quiz.html", {"request": request, "title": "BiSual - Yarışma Oluştur"})

@router.get("/host", response_class=HTMLResponse)
async def host_list_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = request.cookies.get("user_session")
        if not user: return RedirectResponse("/login")
        
        user_obj = db.query(models.User).filter(models.User.username == user).first()
        if not user_obj:
            response = RedirectResponse("/login")
            response.delete_cookie("user_session")
            return response
            
        quizzes = db.query(models.Quiz).filter(models.Quiz.user_id == user_obj.id).all()
        # Calculate total Stats
        total_questions = sum(len(q.questions) for q in quizzes)
        
        return templates.TemplateResponse("host_list.html", {
            "request": request, 
            "quizzes": quizzes,
            "total_questions": total_questions
        })
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"<h1>Error Loading Host Page</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

@router.get("/host/{quiz_id}", response_class=HTMLResponse)
async def host_lobby_page(request: Request, quiz_id: int):
    user = request.cookies.get("user_session")
    if not user: return RedirectResponse("/login")
    
    host_ip = get_local_ip()
    port = "8000" # Default port
    
    return templates.TemplateResponse("host_lobby.html", {
        "request": request, 
        "quiz_id": quiz_id,
        "host_ip": host_ip,
        "port": port
    })
@router.get("/quizzes/{quiz_id}/edit", response_class=HTMLResponse)
async def edit_quiz_page(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    user = request.cookies.get("user_session")
    if not user: return RedirectResponse("/login")
    
    user_obj = db.query(models.User).filter(models.User.username == user).first()
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id, models.Quiz.user_id == user_obj.id).first()
    
    if not quiz:
        return RedirectResponse("/host")

    # Serialize Quiz Data for Frontend
    quiz_data = {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "theme": quiz.theme,
        "settings": quiz.settings or {},
        "questions": []
    }
    
    for q in quiz.questions:
        q_data = {
            "text": q.text,
            "time_limit": q.time_limit,
            "points": q.points,
            "question_type": q.question_type,
            "image_url": q.image_url,
            "options": [{"text": opt.text, "is_correct": opt.is_correct} for opt in q.options]
        }
        quiz_data["questions"].append(q_data)
        
    return templates.TemplateResponse("create_quiz.html", {
        "request": request, 
        "title": f"Düzenle: {quiz.title}",
        "quiz_json": quiz_data
    })

@router.put("/quizzes/{quiz_id}", response_model=schemas.Quiz)
async def update_quiz(quiz_id: int, quiz_update: schemas.QuizCreate, request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(models.User).filter(models.User.username == user_cookie).first()
    db_quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id, models.Quiz.user_id == user.id).first()
    
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    # Update Basic Info
    db_quiz.title = quiz_update.title
    db_quiz.description = quiz_update.description
    db_quiz.theme = quiz_update.theme
    db_quiz.settings = quiz_update.settings  # assuming schema supports this now or loose check

    # Replace Questions (Simplest strategy for complex nested edits)
    # Delete existing questions (adjust cascade deletion in models covers options)
    db.query(models.Question).filter(models.Question.quiz_id == db_quiz.id).delete()
    
    # Add new questions
    for q in quiz_update.questions:
        db_question = models.Question(
            quiz_id=db_quiz.id,
            text=q.text,
            time_limit=q.time_limit,
            points=q.points,
            question_type=q.question_type,
            image_url=q.image_url
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        for opt in q.options:
            db_option = models.Option(
                question_id=db_question.id,
                text=opt.text,
                is_correct=opt.is_correct
            )
            db.add(db_option)
        db.commit()
        
    return db_quiz

@router.post("/quizzes/duplicate/{quiz_id}")
async def duplicate_quiz(quiz_id: int, request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: return RedirectResponse("/login")
    
    user = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not user: return RedirectResponse("/login")
    
    original_quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id, models.Quiz.user_id == user.id).first()
    if not original_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    # 1. Copy Quiz
    new_quiz = models.Quiz(
        title=f"{original_quiz.title} (Kopya)",
        description=original_quiz.description,
        theme=original_quiz.theme,
        settings=original_quiz.settings,
        user_id=user.id
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    
    # 2. Copy Questions & Options
    for q in original_quiz.questions:
        new_q = models.Question(
            quiz_id=new_quiz.id,
            text=q.text,
            time_limit=q.time_limit,
            points=q.points,
            question_type=q.question_type,
            image_url=q.image_url
        )
        db.add(new_q)
        db.commit()
        db.refresh(new_q)
        
        for opt in q.options:
            new_opt = models.Option(
                question_id=new_q.id,
                text=opt.text,
                is_correct=opt.is_correct
            )
            db.add(new_opt)
        db.commit()
        
    return RedirectResponse(url="/host", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/quizzes/delete/{quiz_id}")
async def delete_quiz(quiz_id: int, request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: return RedirectResponse("/login")
    
    user = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not user: return RedirectResponse("/login")
    
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id, models.Quiz.user_id == user.id).first()
    if quiz:
        db.delete(quiz)
        db.commit()
        
    return RedirectResponse(url="/host", status_code=status.HTTP_303_SEE_OTHER)
