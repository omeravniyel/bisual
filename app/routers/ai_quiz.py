from fastapi import APIRouter, Depends, HTTPException, Body
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

@router.post("/generate")
async def generate_quiz_ai(
    payload: dict = Body(...),
    current_user: models.User = Depends(models.User.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generates a quiz using Google Gemini AI.
    Payload: { "topic": str, "count": int, "difficulty": str }
    """
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found in environment.")

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
        response = model.generate_content(prompt)
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
                options=q.get("options"),
                image_url=None
            )
            db.add(question)
        
        db.commit()
        db.refresh(new_quiz)
        
        return {"id": new_quiz.id, "message": "Yarışma oluşturuldu!"}

    except Exception as e:
        print(f"AI Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Yapay zeka servisi yanıt vermedi veya hata oluştu.")
