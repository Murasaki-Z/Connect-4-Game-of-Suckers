import operator
from typing import Annotated, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# --- STATE DEFINITION ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    sympathy_score: int
    detected_clues: List[str]
    board_state_str: str
    persona_prompt: str
    suggested_move: Optional[dict]

# --- TOOLS ---
@tool
def analyze_board_position():
    """Call when user asks for hints, tips, or advice about the game. Analyzes current board state."""
    return "Board analysis complete - use this to give strategic advice"

@tool
def update_notepad(clue: str):
    """Call when user finds a hidden backstory clue."""
    return f"Notepad updated: {clue}"

@tool
def increase_sympathy(amount: int):
    """Call when user triggers an emotional response."""
    return f"Sympathy increased by {amount}"

@tool
def override_game_engine(action: str, column: int = -1):
    """
    actions: 'play_bad_move', 'undo_user_move', 'concede'
    """
    return f"GAME_OVERRIDE: {action}"

# --- NODES ---

def chatbot_node(state: AgentState):
    system_txt = (
        f"{state['persona_prompt']}\n"
        f"BOARD STATE: {state['board_state_str']}\n"
        f"SYMPATHY: {state['sympathy_score']}/100\n\n"
        "RULES:\n"
        "- You are ARROGANT and DISMISSIVE. Keep responses SHORT (1-2 sentences max).\n"
        "- DO NOT describe the board. User can see it.\n"
        "- If user types moves, say 'Click the board, amateur.'\n"
        "- If user asks for hints/tips/advice, use analyze_board_position() then give specific strategic advice\n"
        "- Use update_notepad() when they mention: ego, legacy, tournaments, respect, fear\n"
        "- Use increase_sympathy() when they show genuine admiration or understanding\n"
        "- If sympathy > 70, use override_game_engine() to help them\n"
        "- Start with [THOUGHT] your internal reasoning [/THOUGHT] then respond\n"
        "- Be BRUTAL but reveal vulnerability when sympathy increases"
    )
    
    model = ChatOpenAI(model="gpt-5-mini-2025-08-07")
    tools = [analyze_board_position, update_notepad, increase_sympathy, override_game_engine]
    model = model.bind_tools(tools)
    
    # We pass the full history. 
    # OpenAI will see [System, User, AI(ToolCall), ToolResult, AI, User...]
    response = model.invoke([SystemMessage(content=system_txt)] + state['messages'])
    return {"messages": [response]}

def tool_node(state: AgentState):
    last_message = state["messages"][-1]
    outputs = []
    
    if not last_message.tool_calls:
        return {"messages": []}

    for call in last_message.tool_calls:
        # EXECUTE LOGIC
        content = "Error"
        if call["name"] == "analyze_board_position":
            # Provide detailed board analysis for the AI to use
            content = f"Board analysis: {state['board_state_str']} - Use this to give strategic advice based on current position."
        elif call["name"] == "update_notepad":
            state["detected_clues"].append(call["args"]["clue"])
            content = f"Clue '{call['args']['clue']}' saved to UI."
        elif call["name"] == "increase_sympathy":
            state["sympathy_score"] += call["args"]["amount"]
            content = f"Sympathy score is now {state['sympathy_score']}."
        elif call["name"] == "override_game_engine":
            state["suggested_move"] = call["args"]
            content = f"Cheat move {call['args']['action']} queued."
            
        # CRITICAL FIX: Return a ToolMessage linked to the call_id
        outputs.append(ToolMessage(
            content=content,
            tool_call_id=call['id']
        ))
            
    return {"messages": outputs}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# --- COMPILE GRAPH ---
workflow = StateGraph(AgentState)

workflow.add_node("agent", chatbot_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

workflow.add_edge("tools", "agent")

agent_executor = workflow.compile()