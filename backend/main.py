import os, re
from dotenv import load_dotenv

# 1. LOAD ENV VARS (Must happen first)
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from typing import Dict
from mangum import Mangum # For AWS Lambda

# Import our Brains
from agent import agent_executor 
from langchain_core.messages import HumanMessage

from game_engine import GodModeEngine, PLAYER_PIECE, AI_PIECE
from schemas import (
    GameStartRequest, UserMoveRequest, ChatRequest, 
    GameStateResponse, ChatResponse, Persona
)

app = FastAPI(title="Connect 4: Game of Suckers API")

# Allow React Frontend (Localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATE STORAGE ---
sessions: Dict[str, Dict] = {}

# --- HARDCODED PERSONAS ---
PERSONAS = {
    "grandmaster": Persona(
        id="grandmaster",
        name="The Retired Grandmaster",
        description="Arrogant. Undefeated. Looking for a successor.",
        difficulty="Grandmaster",
        system_prompt="You are a retired legend. You are ruthless. You only respect brilliance. You are playing Connect 4.",
        vulnerabilities=["Fear of being forgotten", "Regret over harsh teaching"]
    ),
    "grieving_father": Persona(
        id="grieving_father",
        name="The Distant Father",
        description="Plays distractedly. Stares at the red tokens.",
        difficulty="Easy",
        system_prompt="You are playing to pass time. You lost your daughter years ago. You are playing Connect 4.",
        vulnerabilities=["Childhood memories", "Protection metaphors"]
    )
}

# --- ENDPOINTS ---

@app.get("/personas")
async def get_personas():
    return list(PERSONAS.values())

@app.post("/start_game", response_model=GameStateResponse)
async def start_game(request: GameStartRequest):
    session_id = str(uuid4())
    engine = GodModeEngine()
    
    if request.persona_id not in PERSONAS:
        raise HTTPException(status_code=404, detail="Persona not found")
        
    sessions[session_id] = {
        "engine": engine,
        "persona": PERSONAS[request.persona_id],
        "history": [], 
        "sympathy_score": 0,
        "hard_mode": request.hard_mode
    }
    
    return GameStateResponse(
        session_id=session_id,
        board_state=engine.board.tolist(),
        game_over=False,
        winner=None,
        current_persona=PERSONAS[request.persona_id].name
    )

@app.post("/move", response_model=GameStateResponse)
async def make_move(request: UserMoveRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    engine: GodModeEngine = session["engine"]
    
    # 1. USER MOVE
    if not engine.is_valid_location(request.column):
        raise HTTPException(status_code=400, detail="Invalid Move")
        
    row = engine.get_next_open_row(request.column)
    engine.drop_piece(row, request.column, PLAYER_PIECE)
    
    if engine.winning_move(PLAYER_PIECE):
        return _build_response(request.session_id, game_over=True, winner=1)

    # 2. AI MOVE (Standard Minimax)
    col, _ = engine.minimax(engine.board, 5, -float('inf'), float('inf'), True)
    
    if col is not None:
        row = engine.get_next_open_row(col)
        engine.drop_piece(row, col, AI_PIECE)
        
        if engine.winning_move(AI_PIECE):
            return _build_response(request.session_id, game_over=True, winner=2)
            
    return _build_response(request.session_id)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    engine = session["engine"]
    persona = session["persona"]
    
    # 1. Prepare State for LangGraph
    board_str = engine.get_board_state_string() 
    
    initial_state = {
        "messages": session["history"] + [HumanMessage(content=request.message)],
        "sympathy_score": session["sympathy_score"],
        "detected_clues": [],
        "board_state_str": board_str,
        "persona_prompt": persona.system_prompt,
        "suggested_move": None
    }
    
    # 2. Run the Brain
    final_state = await agent_executor.ainvoke(initial_state)
    
    # 3. Save History
    session["history"] = final_state["messages"]
    session["sympathy_score"] = final_state["sympathy_score"]
    
    # 4. Extract Response
    last_msg = final_state["messages"][-1]
    
    # Clean up the [THOUGHT] tags if you are using them
    import re
    full_content = last_msg.content
    internal_thought = "Processed"
    visible_response = full_content
    
    match = re.search(r"\[THOUGHT\](.*?)\[/THOUGHT\]", full_content, re.DOTALL)
    if match:
        internal_thought = match.group(1).strip()
        visible_response = full_content.replace(match.group(0), "").strip()

    # --- THE BRIDGE LOGIC ---
    notepad_clue = None
    if final_state["detected_clues"]:
        notepad_clue = final_state["detected_clues"][-1]

    # CHECK FOR CHEATS / GOD MODE ACTIONS
    board_update = None
    action_taken = None
    
    if final_state["suggested_move"]:
        move_data = final_state["suggested_move"]
        action = move_data.get("action")
        col = move_data.get("column", -1)
        action_taken = action

        # EXECUTE THE CHEAT ON THE ENGINE
        if action == "play_bad_move":
            # Force AI to play a random valid column instead of Minimax
            import random
            valid_cols = engine.get_valid_locations()
            if valid_cols:
                bad_col = random.choice(valid_cols)
                row = engine.get_next_open_row(bad_col)
                engine.drop_piece(row, bad_col, AI_PIECE)
                board_update = engine.board.tolist()
        
        elif action == "undo_user_move":
            # Remove the last token (Simplified: we'd need a move stack properly, 
            # but for MVP we can just let the AI say it did it, or implement a basic 'remove top token' logic)
            # For now, let's just let it clear the board or fill a column
            pass
            
        elif action == "concede":
            # AI gives up
            board_update = engine.board.tolist() # Or specific 'win' state logic

    return ChatResponse(
        visible_response=visible_response,
        internal_thought=internal_thought, 
        notepad_clue=notepad_clue,
        action_taken=action_taken,
        board_update=board_update
    )

@app.post("/hint")
async def get_hint(request: dict):
    session_id = request.get("session_id")
    chat_history = request.get("chat_history", [])
    
    if session_id not in sessions:
        return {"hint": "Start a game first!"}
    
    session = sessions[session_id]
    persona = session["persona"]
    sympathy = session["sympathy_score"]
    
    # Analyze recent conversation patterns
    recent_messages = [msg.get('text', '') for msg in chat_history[-4:] if msg.get('sender') == 'user']
    user_approach = ' '.join(recent_messages).lower()
    
    # Track conversation length for evolving advice
    conversation_length = len([msg for msg in chat_history if msg.get('sender') == 'user'])
    
    # Dynamic hints based on multiple factors
    import random
    
    if sympathy < 15:
        hints = [
            "He craves validation - call him 'master' or 'legend'",
            "Ask about his greatest tournament victory",
            "Show awe: 'I've heard stories about your undefeated streak'"
        ]
    elif sympathy < 35:
        if 'tournament' in user_approach or 'victory' in user_approach:
            hints = [
                "Good! Now ask about the pressure of being undefeated",
                "Dig deeper - ask what it cost him to be the best",
                "He's opening up - mention the loneliness at the top"
            ]
        else:
            hints = [
                "He's warming up - ask about his teaching methods",
                "Try: 'What separates legends from amateurs?'",
                "Ask about his most challenging opponent ever"
            ]
    elif sympathy < 60:
        hints = [
            "He's vulnerable now - ask about his regrets",
            "Try: 'Do you ever miss the competition?'",
            "Ask if he's proud of how he treated students",
            "Mention fear of being forgotten by the next generation"
        ]
    else:
        hints = [
            "He trusts you - ask him to go easy on you",
            "Request: 'Could you teach me just one move?'",
            "He might cheat for you now - show you're struggling",
            "Ask him to prove he's still got it by helping you"
        ]
    
    # Add conversation-specific modifiers
    if conversation_length > 8:
        hints.append("The conversation is getting long - be more direct now")
    
    if 'amateur' in user_approach:
        hints.append("He called you amateur - counter with respect for his expertise")
    
    return {"hint": random.choice(hints)}

def _build_response(session_id: str, game_over=False, winner=None):
    session = sessions[session_id]
    engine = session["engine"]
    return GameStateResponse(
        session_id=session_id,
        board_state=engine.board.tolist(),
        game_over=game_over,
        winner=winner,
        current_persona=session["persona"].name
    )

# SERVERLESS HANDLER
handler = Mangum(app)