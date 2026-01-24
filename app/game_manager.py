import random
import string
from typing import Dict, List, Optional
from fastapi import WebSocket

class Player:
    def __init__(self, nickname: str, websocket: WebSocket):
        self.nickname = nickname
        self.websocket = websocket
        self.score = 0
        self.streak = 0

class GameSession:
    def __init__(self, quiz_data: dict, host_websocket: WebSocket):
        self.quiz = quiz_data
        self.host_websocket = host_websocket
        self.players: Dict[str, Player] = {} # socket/id -> Player
        self.state = "LOBBY" # LOBBY, QUESTION, LEADERBOARD, END
        self.current_question_index = 0

    async def broadcast(self, message: dict):
        # Send to Host
        await self.host_websocket.send_json(message)
        # Send to Players
        for player in self.players.values():
            try:
                await player.websocket.send_json(message)
            except:
                pass # Handle disconnected players later

class GameManager:
    def __init__(self):
        self.active_games: Dict[str, GameSession] = {}

    def generate_pin(self) -> str:
        while True:
            pin = ''.join(random.choices(string.digits, k=6))
            if pin not in self.active_games:
                return pin

    async def create_game(self, quiz_data: dict, host_ws: WebSocket) -> str:
        pin = self.generate_pin()
        session = GameSession(quiz_data, host_ws)
        self.active_games[pin] = session
        return pin

    def get_game(self, pin: str) -> Optional[GameSession]:
        """Check if a game with given PIN exists"""
        return self.active_games.get(pin)

    async def join_game(self, pin: str, nickname: str, player_ws: WebSocket) -> bool:
        if pin in self.active_games:
            session = self.active_games[pin]
            # Simple unique ID for player connection (can use ws object or random ID)
            session.players[nickname] = Player(nickname, player_ws)
            
            # Notify Host about new player
            await session.host_websocket.send_json({
                "type": "PLAYER_JOINED",
                "nickname": nickname,
                "count": len(session.players)
            })

            # Send Success and Theme to Player
            await player_ws.send_json({
                "type": "GAME_JOINED",
                "theme": session.quiz.get('theme', 'standard'),
                "score": 0
            })
            return True
        return False

    async def start_game(self, pin: str):
        if pin in self.active_games:
            session = self.active_games[pin]
            session.state = "QUESTION"
            session.current_question_index = 0
            await self.broadcast_question(session)

    async def next_question(self, pin: str):
        if pin in self.active_games:
            session = self.active_games[pin]
            session.current_question_index += 1
            if session.current_question_index < len(session.quiz['questions']):
                session.state = "QUESTION"
                # Reset player answer flags if needed, though simpler to just ignore old ones
                await self.broadcast_question(session)
            else:
                session.state = "END"
                await session.broadcast({"type": "GAME_OVER", "leaderboard": self.get_leaderboard(session)})

    async def broadcast_question(self, session: GameSession):
        q = session.quiz['questions'][session.current_question_index]
        
        # Data for Host (Includes everything)
        await session.host_websocket.send_json({
            "type": "NEW_QUESTION",
            "question": q,
            "index": session.current_question_index,
            "total": len(session.quiz['questions'])
        })

        # Data for Players
        await self.broadcast_to_players(session, {
            "type": "NEW_QUESTION",
            "text": q['text'],
            "time": q['time'],
            "q_type": q['type'],
            "image": q.get('image'),
            "options": [o['text'] for o in q['options']], # Send labels for T/F or Poll
            "options_count": len(q['options'])
        })

    async def broadcast_to_players(self, session: GameSession, message: dict):
        for player in session.players.values():
            try:
                await player.websocket.send_json(message)
            except:
                pass

    async def handle_answer(self, pin: str, nickname: str, answer: any, time_left: int):
        if pin in self.active_games:
            session = self.active_games[pin]
            player = session.players.get(nickname)
            if not player: return

            q = session.quiz['questions'][session.current_question_index]
            is_correct = False
            points = 0
            
            # Check correctness based on Type
            q_type = q['type']

            if q_type == 'poll':
                # Polls have no correct answer, just acknowledge
                # Logic to track vote counts would go here (omitted for MVP)
                # Just give 0 points or maybe participation points? Let's say 0 but 'correct' feedback
                is_correct = True 
                points = 0
            
            elif q_type == 'typing':
                # Answer is a string
                correct_text = q['options'][0]['text']
                if str(answer).strip().lower() == correct_text.strip().lower():
                    is_correct = True
            
            elif q_type == 'marked_answer':
                # Answer is "x,y" string
                # Correct is "tx,ty" string
                try:
                    user_x, user_y = map(float, str(answer).split(','))
                    target_x, target_y = map(float, q['options'][0]['text'].split(','))
                    
                    # Distance check (Euclidean)
                    # Let's say 8% tolerance radius
                    dist = ((user_x - target_x)**2 + (user_y - target_y)**2) ** 0.5
                    if dist <= 8.0:
                        is_correct = True
                except:
                    is_correct = False

            else: 
                # Multiple Choice / True-False (Index based)
                try:
                    ans_idx = int(answer)
                    if 0 <= ans_idx < len(q['options']):
                        if q['options'][ans_idx]['is_correct']:
                            is_correct = True
                except:
                    is_correct = False

            if is_correct:
                # Calculate points
                if points == 0 and q_type != 'poll': # If not set above
                    max_points = q['points']
                    ratio = time_left / q['time'] 
                    points = int(max_points * (0.5 + (ratio * 0.5))) # Minimum 50% points for correct
            
            if is_correct:
                player.streak += 1
                player.score += points
                msg = {"type": "FEEDBACK", "result": "CORRECT", "score": player.score, "points_added": points}
            else:
                player.streak = 0
                msg = {"type": "FEEDBACK", "result": "WRONG", "score": player.score}
            
            try:
                await player.websocket.send_json(msg)
            except: pass
            
            # Notify Host of an answer (update count)
            # await session.host_websocket.send_json({"type": "ANSWER_RECEIVED"}) # Optional optimization

    def get_leaderboard(self, session: GameSession):
        # Return top 5
        sorted_players = sorted(session.players.values(), key=lambda p: p.score, reverse=True)
        return [{"nickname": p.nickname, "score": p.score} for p in sorted_players[:5]]

    async def show_leaderboard(self, pin: str):
        if pin in self.active_games:
            session = self.active_games[pin]
            session.state = "LEADERBOARD"
            data = self.get_leaderboard(session)
            await session.broadcast({"type": "LEADERBOARD", "data": data})

    def remove_game(self, pin: str):

        if pin in self.active_games:
            del self.active_games[pin]

game_manager = GameManager()
