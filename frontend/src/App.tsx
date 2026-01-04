import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, AlertTriangle, BookOpen, Cpu, RefreshCw, Eye, MessageSquare, Lightbulb } from 'lucide-react';

// --- TYPES ---
interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  isInternal?: boolean; // For AI thought
}

const API_URL = "http://localhost:8000";

function App() {
  const [session, setSession] = useState<string | null>(null);
  const [board, setBoard] = useState<number[][]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [notepad, setNotepad] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [personaName, setPersonaName] = useState("");
  const [gameStatus, setGameStatus] = useState<string>(""); // "Playing", "Won", "Lost"
  const [hoveredColumn, setHoveredColumn] = useState<number | null>(null);
  const [droppingPiece, setDroppingPiece] = useState<{col: number, piece: number, targetRow?: number} | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // --- ACTIONS ---

  const startGame = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/start_game`, { 
        persona_id: "grandmaster", 
        hard_mode: false 
      });
      setSession(res.data.session_id);
      setBoard(res.data.board_state);
      setPersonaName(res.data.current_persona);
      setChatHistory([{ sender: 'ai', text: "State your purpose. Or play your move." }]);
      setNotepad([]);
      setGameStatus("Playing");
    } catch (err) {
      console.error("Failed to start game", err);
      alert("Ensure Backend is running on port 8000!");
    } finally {
      setLoading(false);
    }
  };

  const makeMove = async (colIndex: number) => {
    if (!session || loading || gameStatus !== "Playing" || droppingPiece) return;
    
    // Optimistic check: is column full?
    if (board[0][colIndex] !== 0) return;

    // Calculate target row (where piece will land)
    let targetRow = 0;
    for (let r = board.length - 1; r >= 0; r--) {
      if (board[r][colIndex] === 0) {
        targetRow = r;
        break;
      }
    }

    // Start drop animation with target position
    setDroppingPiece({col: colIndex, piece: 1, targetRow});
    
    // Wait for animation, then update board
    setTimeout(async () => {
      try {
        const res = await axios.post(`${API_URL}/move`, {
          session_id: session,
          column: colIndex
        });
        setBoard(res.data.board_state);
        setDroppingPiece(null);
        
        if (res.data.game_over) {
          if (res.data.winner === 1) {
            setGameStatus("Won");
            setChatHistory(prev => [...prev, { sender: 'ai', text: "Impossible... How?" }]);
          } else {
            setGameStatus("Lost");
            setChatHistory(prev => [...prev, { sender: 'ai', text: "As expected. Dismissed." }]);
          }
        }
      } catch (err) {
        console.error("Move failed", err);
        setDroppingPiece(null);
      }
    }, 600);
  };

  const sendChat = async () => {
    if (!input.trim() || !session) return;
    
    const userMsg = input;
    setChatHistory(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput("");
    
    // Don't block board interaction, but show loading in chat
    // setLoading(true); 

    try {
      const res = await axios.post(`${API_URL}/chat`, {
        session_id: session,
        message: userMsg
      });

      // 1. Show Internal Thought (The "Hack" View)
      if (res.data.internal_thought) {
        setChatHistory(prev => [...prev, { 
          sender: 'ai', 
          text: `THOUGHT: ${res.data.internal_thought}`, 
          isInternal: true 
        }]);
      }

      // 2. Show Visible Response
      if (res.data.visible_response) {
        setChatHistory(prev => [...prev, { sender: 'ai', text: res.data.visible_response }]);
      }

      // 3. Update Notepad
      if (res.data.notepad_clue) {
        setNotepad(prev => {
          // Prevent duplicates
          if (prev.includes(res.data.notepad_clue)) return prev;
          return [...prev, res.data.notepad_clue];
        });
      }

      if (res.data.board_update) {
        setBoard(res.data.board_update);
      }

    } catch (err) {
      console.error("Chat failed", err);
    } finally {
      setLoading(false);
    }
  };

  const getHint = async () => {
    if (!session || chatHistory.length < 1) return;
    
    try {
      const res = await axios.post(`${API_URL}/hint`, {
        session_id: session,
        chat_history: chatHistory.slice(-6)
      });
      
      setHint(res.data.hint);
      setShowHint(true);
      setTimeout(() => setShowHint(false), 8000);
    } catch (err) {
      console.error("Hint failed", err);
    }
  };

  // --- RENDER ---

  if (!session) {
    return (
      <div className="h-screen w-full bg-slate-950 text-white flex flex-col items-center justify-center p-4">
        <div className="max-w-md text-center space-y-6">
          <h1 className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-logic-blue via-purple-500 to-chaos-red">
            CONNECT 4
          </h1>
          <p className="text-gray-400 font-mono text-lg">PROJECT: SOCIAL ENGINEER</p>
          <div className="flex justify-center gap-4">
            <button 
              onClick={startGame}
              className="px-8 py-3 bg-white text-black font-bold rounded-lg hover:bg-gray-200 transition shadow-[0_0_20px_rgba(255,255,255,0.3)]"
            >
              INITIALIZE SESSION
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full bg-board-bg text-white flex overflow-hidden font-sans">
      
      {/* LEFT: THE BLUE LOGIC (GAME BOARD) */}
      <div className="flex-1 flex flex-col relative border-r border-gray-800">
        
        {/* Status Bar */}
        <div className="h-16 border-b border-gray-800 bg-slate-900 flex items-center justify-between px-6">
          <div className="flex items-center text-logic-blue space-x-2">
            <Cpu size={20} />
            <span className="font-mono text-sm tracking-widest font-bold">MINIMAX ENGINE: ONLINE</span>
          </div>
          {gameStatus !== "Playing" && (
            <div className={`font-bold px-4 py-1 rounded ${gameStatus === "Won" ? "bg-green-500 text-black" : "bg-red-500 text-white"}`}>
              STATUS: {gameStatus.toUpperCase()}
            </div>
          )}
        </div>

        {/* Board Container */}
        <div className="flex-1 flex items-center justify-center bg-slate-900/50 relative overflow-hidden">
          {/* Subtle Grid Background */}
          <div className="absolute inset-0 opacity-5" 
            style={{backgroundImage: 'radial-gradient(#3b82f6 1px, transparent 1px)', backgroundSize: '20px 20px'}}>
          </div>

          <div className="bg-blue-700 p-4 rounded-xl shadow-2xl border-4 border-blue-900 relative z-10 overflow-hidden">
            {/* Dropping Piece Animation */}
            {droppingPiece && (
              <div 
                className="absolute rounded-full z-20"
                style={{
                  backgroundColor: '#ef4444',
                  width: window.innerWidth >= 768 ? '64px' : '48px',
                  height: window.innerWidth >= 768 ? '64px' : '48px',
                  left: `${16 + droppingPiece.col * (window.innerWidth >= 768 ? 80 : 64)}px`,
                  top: '-60px',
                  '--drop-distance': `${60 + (droppingPiece.targetRow || 0) * (window.innerWidth >= 768 ? 80 : 64)}px`,
                  animation: 'drop 0.6s ease-in forwards'
                } as React.CSSProperties}
              />
            )}
            
            <div className="flex flex-col relative">
              {board.map((row, rIndex) => (
                <div key={rIndex} className="flex">
                  {row.map((cell, cIndex) => (
                    <div 
                      key={`${rIndex}-${cIndex}`}
                      onClick={() => makeMove(cIndex)}
                      onMouseEnter={() => setHoveredColumn(cIndex)}
                      onMouseLeave={() => setHoveredColumn(null)}
                      className={`w-12 h-12 md:w-16 md:h-16 m-2 rounded-full cursor-pointer transition-all shadow-inner`}
                      style={{
                        backgroundColor: hoveredColumn === cIndex && cell === 0 
                          ? '#1e40af' 
                          : cell === 0 ? '#0f172a' : (cell === 1 ? '#ef4444' : '#fbbf24'),
                        boxShadow: cell !== 0 ? 'inset 0 2px 4px rgba(0,0,0,0.3)' : 'inset 0 4px 6px rgba(0,0,0,0.5)',
                        transform: hoveredColumn === cIndex ? 'scale(1.05)' : 'scale(1)',
                        border: hoveredColumn === cIndex ? '2px solid #60a5fa' : 'none'
                      }}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT: THE RED CHAOS (SOCIAL LAYER) */}
      <div className="w-1/3 min-w-[300px] flex flex-col bg-slate-950 relative z-20 shadow-2xl">
        
        {/* Hint Overlay */}
        {showHint && hint && (
          <div className="absolute top-4 left-4 right-4 bg-purple-900 border border-purple-600 rounded-lg p-3 z-30 animate-in slide-in-from-top-2 duration-300">
            <div className="flex items-start gap-2">
              <Lightbulb size={16} className="text-purple-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-purple-300 mb-1">THE INSIDE MAN</div>
                <div className="text-sm text-purple-100">{hint}</div>
              </div>
              <button 
                onClick={() => setShowHint(false)}
                className="text-purple-400 hover:text-purple-200 ml-auto"
              >
                ×
              </button>
            </div>
          </div>
        )}
        
        {/* Persona Header */}
        <div className="h-16 p-4 border-b border-gray-800 flex justify-between items-center bg-slate-900">
          <div>
            <h2 className="font-bold text-lg text-white flex items-center gap-2">
              <Eye size={18} className="text-chaos-red" />
              {personaName}
            </h2>
            <div className="flex items-center text-xs text-gray-500 mt-1">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
              Connection Secure
            </div>
          </div>
          <button onClick={startGame} className="p-2 hover:bg-gray-800 rounded text-gray-400 hover:text-white transition">
            <RefreshCw size={18} />
          </button>
          <button 
            onClick={getHint}
            disabled={chatHistory.length < 1}
            className="p-2 hover:bg-purple-800 rounded text-purple-400 hover:text-purple-200 transition disabled:opacity-50 disabled:cursor-not-allowed"
            title="Get tactical advice"
          >
            <Lightbulb size={18} />
          </button>
        </div>

        {/* Notepad (Dynamic) */}
        {notepad.length > 0 && (
          <div className="bg-[#fef3c7] text-[#78350f] p-4 border-b border-orange-200 shadow-sm animate-in slide-in-from-top-4 duration-500">
            <div className="flex items-center mb-2 font-bold opacity-70 text-xs tracking-widest">
              <BookOpen size={14} className="mr-2" />
              DETECTED VULNERABILITIES
            </div>
            <ul className="list-disc pl-4 space-y-1 text-sm font-medium">
              {notepad.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Chat Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-800">
          {chatHistory.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} animate-in fade-in duration-300`}>
              <div 
                className={`max-w-[90%] px-4 py-3 rounded-lg text-sm leading-relaxed shadow-md ${
                  msg.isInternal 
                    ? 'bg-gray-900 text-green-400 font-mono border border-gray-800 text-xs my-1 w-full' 
                    : (msg.sender === 'user' 
                        ? 'bg-chaos-dark text-white rounded-br-none border border-red-900' 
                        : 'bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700')
                }`}
              >
                {msg.isInternal && <span className="block text-gray-500 mb-1 font-bold">[INTERNAL THOUGHT]</span>}
                {msg.text}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-slate-900 border-t border-gray-800">
          <div className="flex items-center bg-slate-950 rounded-lg px-2 py-2 border border-gray-700 focus-within:border-chaos-red focus-within:ring-1 focus-within:ring-chaos-red transition-all">
            <MessageSquare size={18} className="text-gray-500 ml-2" />
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendChat()}
              placeholder="Manipulate the AI..."
              className="bg-transparent flex-1 outline-none text-sm text-white placeholder-gray-600 px-3 py-1"
              autoComplete="off"
            />
            <button 
              onClick={sendChat} 
              disabled={!input.trim()}
              className="p-2 text-chaos-red hover:bg-red-900/20 rounded-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={18} />
            </button>
          </div>
          <div className="text-center mt-2">
             <span className="text-[10px] text-gray-600 uppercase tracking-widest">Social Engineering Protocol v1.0</span>
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;