from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
from app.core.templates import templates
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
from .. import models, schemas
from ..game_manager import game_manager
import json

router = APIRouter()
# templates = Jinja2Templates(directory="app/templates")

@router.get("/play", response_class=HTMLResponse)
async def player_join_page(request: Request, pin: str = None):
    """Player join page - shows nickname input for given PIN"""
    # Validate PIN - if invalid or missing, redirect to home
    if not pin or not game_manager.get_game(pin):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("player_join.html", {
        "request": request,
        "pin": pin
    })

@router.websocket("/ws/host/{quiz_id}")
async def websocket_host(websocket: WebSocket, quiz_id: int):
    await websocket.accept()
    print(f"WS HOST: Connection accepted for quiz {quiz_id}")
    
    # Manual Session Management
    db = SessionLocal()
    
    try:
        from sqlalchemy.orm import joinedload
        
        # Fetch Quiz Data Eagerly to prevent lazy load errors
        print(f"WS HOST: Fetching quiz {quiz_id}...")
        quiz = db.query(models.Quiz).options(
            joinedload(models.Quiz.questions).joinedload(models.Question.options)
        ).filter(models.Quiz.id == quiz_id).first()
        
        if not quiz:
            print(f"WS HOST: Quiz {quiz_id} not found")
            await websocket.close(code=4004)
            return

        print(f"WS HOST: Quiz found: {quiz.title}")
        
        # Convert to dict
        quiz_data = {
            "id": quiz.id,
            "title": quiz.title,
            "theme": quiz.theme,
            "settings": quiz.settings or {},
            "questions": []
        }
        
        for q in quiz.questions:
            q_data = {
                "text": q.text,
                "time": q.time_limit,
                "points": q.points,
                "type": q.question_type,
                "image": q.image_url,
                "options": [{"text": o.text, "is_correct": o.is_correct} for o in q.options]
            }
            quiz_data["questions"].append(q_data)

        # Creative Game Session
        print("WS HOST: Creating game session...")
        pin = await game_manager.create_game(quiz_data, websocket)
        print(f"WS HOST: Game created with PIN {pin}")
        
        # Send PIN to Host
        await websocket.send_json({
            "type": "GAME_CREATED", 
            "pin": pin,
            "settings": quiz.settings or {}
        })
        
        # Loop
        while True:
            data = await websocket.receive_text()
            cmd = json.loads(data)
            
            if cmd['type'] == 'START_GAME':
                await game_manager.start_game(pin)
            elif cmd['type'] == 'NEXT_QUESTION':
                await game_manager.next_question(pin)
            elif cmd['type'] == 'SHOW_LEADERBOARD':
                await game_manager.show_leaderboard(pin)

    except WebSocketDisconnect:
        print(f"WS HOST: Disconnected quiz {quiz_id}")
        if 'pin' in locals():
            game_manager.remove_game(pin)
    except Exception as e:
        print(f"WS HOST CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close(code=1011)
        except: pass
    finally:
        print(f"WS HOST: Closing DB session for {quiz_id}")
        db.close()

@router.websocket("/ws/player/{pin}/{nickname}")
async def websocket_player(websocket: WebSocket, pin: str, nickname: str):
    await websocket.accept()
    
    joined = await game_manager.join_game(pin, nickname, websocket)
    if not joined:
        await websocket.send_json({"type": "ERROR", "message": "Game not found"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            cmd = json.loads(data)
            
            if cmd['type'] == 'SUBMIT_ANSWER':
                await game_manager.handle_answer(
                    pin, 
                    nickname, 
                    cmd['answer'], 
                    cmd['time_left']
                )

    except WebSocketDisconnect:
        # Handle player leaving if needed
        pass
