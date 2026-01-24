from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from ..game_manager import game_manager
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/play", response_class=HTMLResponse)
async def player_join_page(request: Request, pin: str = None):
    """Player join page - shows nickname input for given PIN"""
    return templates.TemplateResponse("player_join.html", {
        "request": request,
        "pin": pin or ""
    })

@router.websocket("/ws/host/{quiz_id}")
async def websocket_host(websocket: WebSocket, quiz_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    
    # Fetch Quiz Data
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        await websocket.close(code=4004)
        return

    # Convert complex SQLAlchemy object to simple dict for game logic
    # In a real app, use Pydantic helpers, here we do it manually for speed/simplicity
    quiz_data = {
        "id": quiz.id,
        "title": quiz.title,
        "theme": quiz.theme,
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
    pin = await game_manager.create_game(quiz_data, websocket)
    
    # Send PIN to Host
    await websocket.send_json({"type": "GAME_CREATED", "pin": pin})

    try:
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
        game_manager.remove_game(pin)

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
