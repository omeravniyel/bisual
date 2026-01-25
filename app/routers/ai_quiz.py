from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter(
    prefix="/ai",
    tags=["ai"]
)

API_KEY = os.getenv("GEMINI_API_KEY")

@router.post("/preview")
async def generate_quiz_preview(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Generates questions using AI and returns them as JSON (does not save to DB).
    """
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found.")
        
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: raise HTTPException(status_code=401, detail="Not authenticated")
    
    # We don't strictly need user object for preview, just auth check, but good practice
    user = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not user: raise HTTPException(status_code=401, detail="User not found")

    topic = payload.get("topic")
    count = payload.get("count", 5)
    difficulty = payload.get("difficulty", "medium")

    # Limits
    if count > 20: count = 20
    if count < 1: count = 5

    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Create {count} quiz questions about "{topic}". 
    Difficulty: {difficulty}.
    Language: Turkish (Türkçe).
    
    Return ONLY a raw JSON object (list of questions).
    Structure:
    {{
        "questions": [
            {{
                "text": "Question text?",
                "limit": 20,
                "points": 1000,
                "options": [
                    {{ "text": "A", "is_correct": true }},
                    {{ "text": "B", "is_correct": false }},
                    {{ "text": "C", "is_correct": false }},
                    {{ "text": "D", "is_correct": false }}
                ]
            }}
        ]
    }}
    Randomize correct option position.
    """

    try:
        # Try models in order of preference: Flash (Fast/Cheap), then Pro (Stable)
        models_to_try = ['gemini-1.5-flash', 'gemini-pro']
        
        response = None
        last_error = None

        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                break
            except Exception as e:
                print(f"Model {model_name} failed: {e}")
                last_error = e
                continue
                
        if not response and last_error:
        # Debugging: List available models
            try:
                available = [m.name for m in genai.list_models()]
                debug_msg = f"Erişilebilir modeller: {', '.join(available)}"
            except Exception as list_exc:
                debug_msg = f"Model listesi alınamadı: {list_exc}"

            raise HTTPException(status_code=500, detail=f"Yapay zeka hatası: {str(last_error)}. {debug_msg}")

        text_resp = response.text.strip()
        if text_resp.startswith("```"):
            text_resp = text_resp.replace("```json", "").replace("```", "")
        
        data = json.loads(text_resp)
        return data.get("questions", [])

    except Exception as e:
        print(f"AI Preview Error: {e}")
        raise HTTPException(status_code=500, detail=f"Yapay zeka hatası: {str(e)}")

@router.post("/generate")
async def generate_quiz_ai(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Generates a quiz using Google Gemini AI.
    Payload: { "topic": str, "count": int, "difficulty": str }
    """
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found in environment.")

    user_cookie = request.cookies.get("user_session")
    if not user_cookie: raise HTTPException(status_code=401, detail="Not authenticated")
    
    current_user = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not current_user: raise HTTPException(status_code=401, detail="User not found")

    topic = payload.get("topic")
    count = payload.get("count", 5)
    difficulty = payload.get("difficulty", "medium")

    # Validate limits
    if count > 20: count = 20
    if count < 1: count = 5

    # Configure Gemini
    genai.configure(api_key=API_KEY)
    
    # Use Flash model for speed/cost
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Create a quiz about "{topic}" with {count} questions. 
    Difficulty level: {difficulty}.
    Language: Turkish (Türkçe).
    
    Return ONLY a raw JSON object (no markdown formatting, no backticks).
    Structure:
    {{
        "title": "Creative Quiz Title",
        "description": "Short description",
        "questions": [
            {{
                "text": "Question text here?",
                "limit": 20,
                "points": 1000,
                "options": [
                    {{ "text": "Option A", "is_correct": true }},
                    {{ "text": "Option B", "is_correct": false }},
                    {{ "text": "Option C", "is_correct": false }},
                    {{ "text": "Option D", "is_correct": false }}
                ]
            }}
        ]
    }}
    Make sure to randomize the correct option position.
    """

    try:
        # Try models in order of preference: Flash (Fast/Cheap), then Pro (Stable)
        models_to_try = ['gemini-1.5-flash', 'gemini-pro']
        
        response = None
        last_error = None
    
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                break # Success
            except Exception as e:
                print(f"Model {model_name} failed: {e}")
                last_error = e
                continue
                
        if not response and last_error:
        # Debugging: List available models to see what IS supported
            try:
                available = [m.name for m in genai.list_models()]
                debug_msg = f"Erişilebilir modeller: {', '.join(available)}"
            except Exception as list_exc:
                debug_msg = f"Model listesi alınamadı: {list_exc}"
                
            print(f"All models failed. {debug_msg}")
            raise HTTPException(status_code=500, detail=f"Yapay zeka hatası: {str(last_error)}. {debug_msg}")

        text_resp = response.text.strip()
        
        # Cleanup potential markdown code blocks if the model ignores instruction
        if text_resp.startswith("```"):
            text_resp = text_resp.replace("```json", "").replace("```", "")
        
        quiz_data = json.loads(text_resp)
        
        # Create Quiz in DB
        new_quiz = models.Quiz(
            title=quiz_data.get("title", f"{topic} Yarışması"),
            description=quiz_data.get("description", "Yapay zeka ile oluşturuldu."),
            user_id=current_user.id,
            theme="standard",
            settings={"music_theme": "energetic"}
        )
        db.add(new_quiz)
        db.flush()

        # Create Questions
        for q in quiz_data.get("questions", []):
            question = models.Question(
                quiz_id=new_quiz.id,
                text=q.get("text"),
                question_type="multiple_choice",
                time_limit=q.get("limit", 20),
                points=q.get("points", 1000),
                image_url=None
            )
            
            # Create Options objects
            for opt in q.get("options", []):
                question.options.append(models.Option(
                    text=opt.get("text"),
                    is_correct=opt.get("is_correct")
                ))
            
            db.add(question)
        
        db.commit()
        db.refresh(new_quiz)
        
        return {"id": new_quiz.id, "message": "Yarışma oluşturuldu!"}

    except Exception as e:
        print(f"AI Generation Error: {e}")
        raise HTTPException(status_code=500, detail=f"Yapay zeka hatası: {str(e)}")
