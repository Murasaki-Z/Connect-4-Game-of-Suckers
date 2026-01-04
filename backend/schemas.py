#schemas.py

from pydantic import BaseModel
from typing import List, Optional, Union

# --- PERSONA MODELS ---
class Persona(BaseModel):
    id: str
    name: str
    description: str
    difficulty: str # "Easy", "Hard", "Grandmaster"
    system_prompt: str # The core instruction set
    vulnerabilities: List[str] # Hidden traits for the notepad logic

# --- REQUEST MODELS ---
class GameStartRequest(BaseModel):
    persona_id: str
    hard_mode: bool = False

class UserMoveRequest(BaseModel):
    session_id: str
    column: int

class ChatRequest(BaseModel):
    session_id: str
    message: str

class HintRequest(BaseModel):
    session_id: str
    chat_history: List[dict]

# --- RESPONSE MODELS ---
class GameStateResponse(BaseModel):
    session_id: str
    board_state: List[List[int]] # The 6x7 grid
    game_over: bool
    winner: Optional[int] # 1=User, 2=AI
    current_persona: str

class ChatResponse(BaseModel):
    visible_response: str # What the user sees in chat
    internal_thought: str # Hidden debug thought (optional)
    notepad_clue: Optional[str] # "Clue Found: He misses his daughter"
    action_taken: Optional[str] # "played_bad_move", "undo", etc.
    board_update: Optional[List[List[int]]] = None