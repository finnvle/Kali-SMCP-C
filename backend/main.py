import os
import json
import sqlite3
import httpx
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from mcp_client import KaliMCPClient
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings, reload_env

app = FastAPI()

#Modify this if you concern about security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = settings.DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  session_id TEXT DEFAULT 'default',
                  role TEXT,
                  content TEXT)''')
    try:
        c.execute("ALTER TABLE messages ADD COLUMN session_id TEXT DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass
        
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id TEXT PRIMARY KEY,
                  title TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute("INSERT OR IGNORE INTO sessions (id, title) VALUES ('default', 'New Chat')")
    conn.commit()
    conn.close()

init_db()

class ChatRequest(BaseModel):
    model: str # "ollama" or "claude"
    message: str
    session_id: str = "default"
    
class Broadcaster:
    """Manages multiple listeners for a single session's agent task."""
    def __init__(self):
        self.queues = []
        self.is_running = False

    def add_listener(self):
        q = asyncio.Queue()
        self.queues.append(q)
        return q

    def remove_listener(self, q):
        if q in self.queues:
            self.queues.remove(q)

    async def emit(self, event):
        for q in self.queues:
            await q.put(event)

active_sessions: Dict[str, Broadcaster] = {}

def save_message(session_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def update_message(msg_id: int, content: str):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("UPDATE messages SET content = ? WHERE id = ?", (content, msg_id))
    conn.commit()
    conn.close()

def get_all_messages(session_id: str):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def build_cli_command(tool_name: str, args: dict) -> str:
    """Reconstruct a human-readable CLI command from a tool name and its arguments."""
    CLI_TEMPLATES = {
        "nmap_scan": lambda a: (
            f"nmap {a.get('scan_type', '-sV')} "
            f"{'-p ' + a.get('ports') + ' ' if a.get('ports') else ''}"
            f"{a.get('additional_args') + ' ' if a.get('additional_args') else ''}"
            f"{a.get('target', '')}"
        ).strip(),
        "gobuster_scan": lambda a: (
            f"gobuster dir -u {a.get('url', '')} "
            f"-w {a.get('wordlist', '/usr/share/wordlists/dirb/common.txt')}"
            f"{' -x ' + a.get('extensions') if a.get('extensions') else ''}"
        ),
        "nikto_scan": lambda a: f"nikto -h {a.get('target', '')}",
        "dirb_scan": lambda a: f"dirb {a.get('url', '')} {a.get('wordlist', '')}".strip(),
        "run_exploit": lambda a: (
            f"msfconsole -q -x 'use {a.get('module','')}; "
            f"set RHOSTS {a.get('target','')}; run'"
        ),
        "ssh_bruteforce": lambda a: (
            f"hydra -l {a.get('username','')} -P {a.get('wordlist','')} "
            f"{a.get('target','')} ssh"
        ),
        "server_health": lambda a: f"curl {a.get('server_url', 'http://kali-mcp:5000')}/health",
    }
    template = CLI_TEMPLATES.get(tool_name)
    if template:
        try:
            return template(args)
        except Exception:
            pass
    # Fallback: tool_name key=value ...
    arg_str = " ".join(f"{k}={v}" for k, v in args.items() if v)
    return f"{tool_name} {arg_str}".strip()

async def stream_chat(request: ChatRequest, broadcaster: Broadcaster = None):
    # Helper to emit events
    async def emit(event):
        if broadcaster:
            await broadcaster.emit(event)
        yield event

    yield {"event": "status", "data": "Connecting to MCP Server..."}
    if broadcaster: await broadcaster.emit({"event": "status", "data": "Connecting to MCP Server..."})
    
    import sys
    mcp_client = KaliMCPClient(sys.executable, ["client.py", "--server", settings.MCP_SERVER_URL])
    
    try:
        try:
            tools_response = await mcp_client.get_tools()
            yield {"event": "status", "data": f"Connected! Found {len(tools_response.tools)} tools."}
        except Exception as e:
            yield {"event": "error", "data": f"Failed to connect to MCP: {e}"}
            return

        lc_tools = []
        for t in tools_response.tools:
            lc_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            })
    
        # Determine which LLM to use
        reload_env()
        ollama_model = request.model if request.model not in ["claude", "openai", "gemini"] else settings.OLLAMA_MODEL
        if request.model == "claude":
            llm = ChatAnthropic(model=settings.CLAUDE_MODEL, temperature=0, api_key=settings.ANTHROPIC_API_KEY.strip("\"' "))
        elif request.model == "openai":
            llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY.strip("\"' "))
        elif request.model == "gemini":
            llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, temperature=0, google_api_key=settings.GOOGLE_API_KEY.strip("\"' "))
        else:
            llm = ChatOllama(model=ollama_model, base_url=settings.OLLAMA_BASE_URL, temperature=0) 

        if lc_tools:
            llm_with_tools = llm.bind_tools(lc_tools)
        else:
            llm_with_tools = llm

        history = get_all_messages(request.session_id)
        system_prompt = settings.SYSTEM_PROMPT
        messages = [SystemMessage(content=system_prompt)]
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            else:
                messages.append(AIMessage(content=h["content"]))
                
        messages.append(HumanMessage(content=request.message))
        save_message(request.session_id, "user", request.message)
        
        # Pre-save the assistant message so it appears immediately on refresh
        msg_id = save_message(request.session_id, "assistant", "Consulting the grid...")

        yield {"event": "status", "data": "Generating response..."}
        if broadcaster: await broadcaster.emit({"event": "status", "data": "Generating response..."})
        
        full_response = ""
        iteration = 0
        max_iterations = 10
        
        while iteration < max_iterations:
            iteration += 1
            chunks = []
            is_tool_call = False
            iteration_content = ""
            
            async for chunk in llm_with_tools.astream(messages):
                # Track if this chunk is part of a tool call
                if chunk.tool_call_chunks:
                    is_tool_call = True
                
                # Stream content if it's not a tool call
                if chunk.content:
                    delta = chunk.content
                    if isinstance(delta, list):
                        delta = "".join(item.get("text", "") for item in delta if isinstance(item, dict) and item.get("type") == "text")
                    
                    if delta:
                        iteration_content += delta
                        # Update DB incrementally
                        update_message(msg_id, full_response + iteration_content)
                        
                        # Only stream to UI if we aren't currently in a tool call sequence
                        # or if the model provides reasoning before tools
                        evt = {"event": "message", "data": json.dumps({"delta": delta})}
                        if broadcaster: await broadcaster.emit(evt)
                        yield evt
                
                chunks.append(chunk)
                
            if not chunks:
                break
                
            # Reassemble the full response for this iteration
            response = chunks[0]
            for chunk in chunks[1:]:
                response = response + chunk
            
            full_response += iteration_content
            messages.append(response)
                    
            if not response.tool_calls:
                break
                
            # Handle tool calls
            for tc in response.tool_calls:
                evt = {"event": "status", "data": f"Tool Execution: {tc['name']}..."}
                if broadcaster: await broadcaster.emit(evt)
                yield evt
                try:
                    # Set a strict 30-second timeout for tool execution
                    tool_task = asyncio.create_task(mcp_client.call_tool(tc["name"], tc["args"]))
                    
                    elapsed = 0
                    while not tool_task.done():
                        if elapsed >= 30:
                            tool_task.cancel()
                            raise asyncio.TimeoutError(f"Tool {tc['name']} timed out after 30 seconds.")
                        await asyncio.sleep(2.0)
                        elapsed += 2
                        evt = {"event": "status", "data": f"Working on {tc['name']} ({elapsed}s elapsed)..."}
                        if broadcaster: await broadcaster.emit(evt)
                        yield evt
                    
                    tool_res = tool_task.result()
                    
                    tool_content = "Executed successfully (no output)."
                    if hasattr(tool_res, 'content') and tool_res.content:
                        # Collect all text content from tool result
                        parts = []
                        for part in tool_res.content:
                            text_val = ""
                            if hasattr(part, 'text'):
                                text_val = part.text
                            elif isinstance(part, dict) and 'text' in part:
                                text_val = part['text']
                            
                            if text_val:
                                # Try to parse as JSON to extract stdout directly
                                try:
                                    parsed = json.loads(text_val)
                                    if isinstance(parsed, dict):
                                        outer_out = parsed.get("stdout", "")
                                        outer_err = parsed.get("stderr", "")
                                        # Use stdout if present, otherwise fallback to stderr or original
                                        text_val = outer_out if outer_out else (outer_err if outer_err else text_val)
                                except:
                                    pass # Not JSON, keep original
                                parts.append(text_val)
                                
                        if parts:
                            tool_content = "\n".join(parts)
                    elif str(tool_res):
                        # Try parsing root as well
                        text_val = str(tool_res)
                        try:
                            parsed = json.loads(text_val)
                            if isinstance(parsed, dict) and "stdout" in parsed:
                                tool_content = parsed["stdout"]
                            else:
                                tool_content = text_val
                        except:
                            tool_content = text_val
                    
                    # Append result to history and notify UI
                    messages.append(ToolMessage(content=tool_content, tool_call_id=tc["id"]))
                    cli_cmd = build_cli_command(tc["name"], tc.get("args", {}))
                    evt_res = {"event": "tool_result", "data": json.dumps({"tool": tc["name"], "cli": cli_cmd, "result": tool_content})}
                    if broadcaster: await broadcaster.emit(evt_res)
                    yield evt_res
                    
                    # PERSISTENCE: Append the formatted block to full_response so it saves to DB
                    formatted_tool_block = f"\n\n### Command Used:\n```bash\n{cli_cmd}\n```\n\n### Raw Output:\n```text\n{tool_content}\n```\n\n"
                    full_response += formatted_tool_block
                    
                    evt_stat = {"event": "status", "data": "Processing results..."}
                    if broadcaster: await broadcaster.emit(evt_stat)
                    yield evt_stat
                    
                    # Also update DB with current state
                    update_message(msg_id, full_response)
                except Exception as e:
                    import traceback
                    error_msg = f"Tool failure: {str(e)}\n{traceback.format_exc()}"
                    messages.append(ToolMessage(content=error_msg, tool_call_id=tc["id"]))
                    evt_err = {"event": "error", "data": f"Tool error: {str(e)}"}
                    if broadcaster: await broadcaster.emit(evt_err)
                    yield evt_err

        # Skip final save as we've been updating incrementally
        evt_done = {"event": "done", "data": ""}
        if broadcaster: await broadcaster.emit(evt_done)
        yield evt_done

    except Exception as e:
        import traceback
        error_msg = f"Agent Loop Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        yield {"event": "error", "data": error_msg}
        if broadcaster: await broadcaster.emit({"event": "error", "data": error_msg})
    finally:
        try:
            await mcp_client.close()
        except:
            pass

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    chat_req = ChatRequest(**data)
    session_id = chat_req.session_id
    
    if session_id in active_sessions:
        # Re-attach to existing stream
        broadcaster = active_sessions[session_id]
        queue = broadcaster.add_listener()
    else:
        # Start new agent
        broadcaster = Broadcaster()
        active_sessions[session_id] = broadcaster
        broadcaster.is_running = True
        queue = broadcaster.add_listener()

        async def worker():
            try:
                # No need to iterate here as stream_chat handles broadcaster.emit internally
                async for _ in stream_chat(chat_req, broadcaster):
                    pass
            except Exception as e:
                import traceback
                await broadcaster.emit({"event": "error", "data": f"{str(e)}\n{traceback.format_exc()}"})
            finally:
                await broadcaster.emit(None) # Sentinel
                broadcaster.is_running = False
                if active_sessions.get(session_id) == broadcaster:
                    del active_sessions[session_id]

        asyncio.create_task(worker())
    
    async def event_generator():
        try:
            while True:
                event = await queue.get()
                if event is None: break
                yield event
        except asyncio.CancelledError:
            pass
        finally:
            if session_id in active_sessions:
                active_sessions[session_id].remove_listener(queue)

    return EventSourceResponse(event_generator())

@app.get("/chat/stream/{session_id}")
async def get_chat_stream(session_id: str):
    """Allows a client to re-subscribe to an ongoing agent task via SSE."""
    if session_id not in active_sessions:
        # Return a stream that immediately closes if inactive to satisfy EventSource
        async def empty_gen():
            yield {"event": "done", "data": "inactive"}
        return EventSourceResponse(empty_gen())
    
    broadcaster = active_sessions[session_id]
    queue = broadcaster.add_listener()
    
    async def event_generator():
        try:
            # Send an initial status to confirm connection
            yield {"event": "status", "data": "Re-attached to active operation..."}
            while True:
                event = await queue.get()
                if event is None: break
                yield event
        except asyncio.CancelledError:
            pass
        finally:
            if session_id in active_sessions:
                active_sessions[session_id].remove_listener(queue)

    return EventSourceResponse(event_generator())

@app.get("/chat/active/{session_id}")
async def is_chat_active(session_id: str):
    """Check if a session has an active running agent."""
    is_active = session_id in active_sessions and active_sessions[session_id].is_running
    return {"active": is_active}

class SessionCreate(BaseModel):
    id: str
    title: str

@app.get("/sessions")
async def get_sessions():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    # Add active status based on background worker presence
    return [{
        "id": r[0], 
        "title": r[1], 
        "created_at": r[2],
        "is_active": r[0] in active_sessions and active_sessions[r[0]].is_running
    } for r in rows]

@app.post("/sessions")
async def create_session(session: SessionCreate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (session.id, session.title))
    conn.commit()
    conn.close()
    return {"status": "created"}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

class SessionUpdate(BaseModel):
    title: str

@app.patch("/sessions/{session_id}")
async def update_session(session_id: str, session: SessionUpdate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sessions SET title = ? WHERE id = ?", (session.title, session_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    return get_all_messages(session_id)

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"status": "cleared"}

# Global cache for provider connectivity
_claude_status = {"online": False, "last_check": 0}
_openai_status = {"online": False}
_gemini_status = {"online": False}

@app.get("/models")
async def get_models():
    """Discover available LLM models (Ollama local + External APIs)."""
    import time
    global _claude_status
    
    # Reload .env to catch live changes
    reload_env()
    
    # Process Keys
    claude_key = settings.ANTHROPIC_API_KEY.strip("\"' ")
    openai_key = settings.OPENAI_API_KEY.strip("\"' ")
    gemini_key = settings.GOOGLE_API_KEY.strip("\"' ")
    
    # Claude logic
    current_time = time.time()
    # Signature detect: Anthropic keys usually start with sk-ant-
    claude_valid = claude_key.startswith("sk-ant-") and len(claude_key) > 30
    
    if claude_valid:
        if not _claude_status["online"] or (current_time - _claude_status["last_check"]) > 600:
            _claude_status["online"] = True # Assume valid if signature matches
            _claude_status["last_check"] = current_time
    else:
        _claude_status["online"] = False

    # OpenAI Signature: starts with sk-
    openai_online = openai_key.startswith("sk-") and len(openai_key) > 30
    
    # Gemini Signature: usually no prefix, but we check length and basic character set
    gemini_online = len(gemini_key) > 30 and not gemini_key.startswith("sk-")

    result = {
        "ollama": {"online": False, "models": [], "base_url": settings.OLLAMA_BASE_URL},
        "claude": {"online": _claude_status["online"], "model": settings.CLAUDE_MODEL},
        "openai": {"online": openai_online, "model": settings.OPENAI_MODEL},
        "gemini": {"online": gemini_online, "model": settings.GEMINI_MODEL}
    }
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                result["ollama"]["online"] = True
                result["ollama"]["models"] = [
                    m["name"] for m in data.get("models", [])
                ]
    except Exception:
        pass
    return result

@app.get("/app-config")
async def get_app_config():
    """Return non-sensitive config values for the frontend."""
    reload_env()
    return {
        "mcp_server_url": settings.MCP_SERVER_URL,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "default_ollama_model": settings.OLLAMA_MODEL,
        "claude_model": settings.CLAUDE_MODEL,
        "claude_configured": bool(settings.ANTHROPIC_API_KEY.strip("\"' ")),
        "openai_configured": bool(settings.OPENAI_API_KEY.strip("\"' ")),
        "gemini_configured": bool(settings.GOOGLE_API_KEY.strip("\"' ")),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
