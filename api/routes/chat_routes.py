"""
FastAPI Chat Router for DesktopPilot AI.
Provides clean REST and streaming endpoints connecting the React frontend to the agent.
"""

import uuid
import asyncio
import inspect
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from agent.graphs.pilot_graph import pilot_agent_graph
except ImportError:
    pilot_agent_graph = None

from tools.registry import tool_registry
from agent.safety.risk_analyzer import safety_analyzer, RiskLevel
from agent.safety.approval_gate import approval_manager
from agent.autonomous_pilot import autonomous_pilot
from agent.decision_engine import decision_engine
from database.session import session_factory
from database.models import ChatSessionModel, ChatMessageModel, ActionAuditLog
from utils.logger import logger

chat_router = APIRouter(prefix="/api/v1", tags=["Chat & Desktop Control"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User prompt or desktop command")
    session_id: Optional[str] = Field(default=None)


class ChatApprovalRequest(BaseModel):
    token: str = Field(..., description="Confirmation token for medium-risk action")
    approved: bool = Field(..., description="True to execute, False to cancel")


class ToolExecutionRecord(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    output: Any
    is_success: bool


class ChatResponse(BaseModel):
    response: str
    tool_executed: Optional[str] = None
    tool_result: Optional[Any] = None
    requires_approval: bool = False
    approval_token: Optional[str] = None
    approval_prompt: Optional[str] = None
    status: str  # completed | awaiting_approval | failed


# In-memory session store for fast chat turns
CHAT_SESSIONS: Dict[str, List[Dict[str, str]]] = {}


def _resolve_instant_tool_call(message: str) -> Optional[tuple[str, Dict[str, Any]]]:
    """
    Fast, resilient intent router for direct desktop commands.
    Handles typos ('lunch', 'lauch'), natural phrasing ('open vs code please', 'chrome kholo'),
    and keyword detection.
    """
    msg = message.lower().strip()

    # Multi-action detection: If the user asked to open AND perform an action (type/calculate),
    # let AutonomousScreenPilot drive the full multi-step desktop workflow!
    if any(w in msg for w in ["type", "write", "likh", "likho", "calculate", "hisab", "*", "+", " and "]):
        return None

    # --- PHASE 1: SYSTEM CONTROLS ---
    # Volume Controls
    if any(k in msg for k in ["volume up", "increase volume", "louder", "awaz barhao", "awaz tez"]):
        return ("volume_up", {"steps": 5})
    if any(k in msg for k in ["volume down", "decrease volume", "quieter", "awaz kam", "awaz kam kro"]):
        return ("volume_down", {"steps": 5})
    if any(k in msg for k in ["mute volume", "toggle mute", "unmute"]) or msg == "mute":
        return ("mute_volume", {})

    # Brightness Controls
    if "brightness" in msg:
        nums = re.findall(r"\d+", msg)
        pct = int(nums[0]) if nums else 50
        return ("set_brightness", {"percent": pct})

    # Recycle Bin
    if any(k in msg for k in ["empty recycle bin", "clear recycle bin", "recycle bin empty", "clean recycle bin"]):
        return ("empty_recycle_bin", {})

    # Lock PC
    if any(k in msg for k in ["lock pc", "lock computer", "lock screen", "pc lock"]):
        return ("lock_pc", {})

    # Shutdown Timers
    if "cancel shutdown" in msg or "abort shutdown" in msg:
        return ("cancel_shutdown", {})
    if "shutdown after" in msg or "shutdown in" in msg:
        nums = re.findall(r"\d+", msg)
        mins = int(nums[0]) if nums else 30
        return ("schedule_shutdown", {"minutes": mins})

    # System Status / RAM Metrics
    if any(k in msg for k in ["system status", "ram usage", "memory usage", "pc specs", "pc health"]):
        return ("get_system_metrics", {})

    # --- PHASE 1: CLIPBOARD AI ---
    if any(k in msg for k in ["summarize clipboard", "summarize copied text", "copied text summarize", "clipboard summarize"]):
        return ("clipboard_summarize", {})
    if any(k in msg for k in ["translate clipboard", "translate copied text"]):
        target_lang = "English" if "english" in msg else "Urdu"
        return ("clipboard_translate", {"target_language": target_lang})
    if any(k in msg for k in ["rewrite professionally", "rewrite clipboard", "rewrite copied text", "improve grammar"]):
        style = "email_reply" if "email" in msg else ("grammar_fix" if "grammar" in msg else "professional")
        return ("clipboard_rewrite", {"style": style})
    if any(k in msg for k in ["copy as markdown", "clipboard to markdown", "markdown clipboard"]):
        return ("clipboard_format_markdown", {})

    # --- PHASE 1: SEARCH FILES & FOLDERS ---
    if msg.startswith("find ") or msg.startswith("search file ") or msg.startswith("search files "):
        raw_query = msg.replace("find all ", "").replace("find ", "").replace("search files ", "").replace("search file ", "").strip()
        # Check for extension pattern like "csv files" or "all pdfs"
        ext = None
        for known_ext in ["pdf", "csv", "png", "jpg", "txt", "py", "xlsx", "docx"]:
            if known_ext in raw_query:
                ext = known_ext
                break
        return ("search_files", {"query": raw_query.replace("files", "").replace("file", "").strip(), "extension": ext})

    # --- PHASE 1: UNIVERSAL OPEN ANYTHING ---
    # Specific popular applications & folders
    if any(k in msg for k in ["downloads folder", "open downloads", "downloads"]):
        return ("open_anything", {"target": "downloads"})
    if any(k in msg for k in ["documents folder", "open documents"]):
        return ("open_anything", {"target": "documents"})
    if any(k in msg for k in ["c drive", "open c:"]):
        return ("open_anything", {"target": "c drive"})

    # 1. VS Code / Code
    if any(k in msg for k in ["vs code", "vscode", "code"]) and any(k in msg for k in ["open", "launch", "lunch", "start", "run", "khol", "kholo", "chalao"]):
        return ("launch_vscode", {"project_path": "."})

    # 2. Chrome / Web Browser / Internet
    if any(k in msg for k in ["chrome", "browser", "internet", "edge", "google", "web"]):
        return ("open_browser", {"url": "https://www.google.com"})

    # 3. Notepad / Calculator / Terminal
    if "notepad" in msg:
        return ("open_app", {"app_name": "notepad"})
    if "calc" in msg or "calculator" in msg:
        return ("open_app", {"app_name": "calc"})
    if "terminal" in msg or "cmd" in msg or "powershell" in msg:
        return ("open_app", {"app_name": "terminal"})

    # 4. Storage & File Cleanup
    if any(k in msg for k in ["clean", "cleanup", "safai", "junk", "temp", "storage", "disk"]) and "recycle bin" not in msg:
        return ("analyze_disk_storage", {"target_dir": "C:\\", "large_file_threshold_mb": 100})

    # 5. Generic Application Launch ("open <app>", "lunch <app>", "start <app>")
    launch_prefixes = ["open ", "launch ", "lunch ", "start ", "run ", "kholo "]
    for prefix in launch_prefixes:
        if msg.startswith(prefix):
            target = msg.replace(prefix, "").strip()
            # Clean common filler words
            target = target.replace("please", "").replace("app", "").replace("software", "").strip()
            return ("open_anything", {"target": target})

    # 6. Package Installations ("install <pkg>")
    if msg.startswith("install "):
        pkg = msg.replace("install ", "").strip()
        cmd = f"winget install {pkg} --silent" if "winget" not in pkg else pkg
        return ("run_terminal_command", {"command": cmd})

    return None


@chat_router.post("/chat", response_model=ChatResponse)
async def handle_chat_message(request: ChatMessageRequest):
    """
    Primary endpoint for the React frontend.
    Driven by the AI Decision-Making Engine (Semantic Reasoning + LLM Tool Calling).
    """
    session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
    user_msg = request.message.strip()
    logger.info(f"Received chat from React [{session_id}]: '{user_msg}'")

    # 1. Ask the AI Decision Engine to reason about the prompt
    decision = await decision_engine.decide_action(user_msg)
    logger.info(f"AI Decision: Intent={decision.intent} | Tool={decision.tool_name} | Thought={decision.thought}")

    tool_name = decision.tool_name
    params = decision.parameters

    # 2. Multi-Step Physical PC Workflow
    if decision.is_multi_step or tool_name == "autonomous_screen_pilot":
        logger.info(f"Invoking Autonomous Screen Pilot for goal: '{user_msg}'")
        try:
            pilot_result = await autonomous_pilot.execute_autonomous_goal(user_msg)
            return ChatResponse(
                response=pilot_result.get("final_summary", "Completed autonomous operations on screen."),
                tool_executed="autonomous_screen_pilot",
                tool_result=pilot_result,
                status="completed"
            )
        except Exception as e:
            logger.error(f"Autonomous screen pilot error: {e}")
            return ChatResponse(
                response=f"Autonomous action error: {str(e)}",
                status="failed"
            )

    # 3. Check safety if terminal command or destructive operation
    if tool_name == "run_terminal_command":
        cmd = params.get("command", "")
        assessment = safety_analyzer.evaluate_command(cmd)
        if assessment.level == RiskLevel.HIGH:
            return ChatResponse(
                response=f"Command blocked by AI Safety Layer: {assessment.reason}",
                status="failed"
            )
        if assessment.requires_approval:
            token = approval_manager.create_pending_approval(
                action_type="terminal_command",
                target=cmd,
                payload={"tool_name": "run_terminal_command", "params": params},
                prompt=assessment.confirmation_prompt or f"Approve running: {cmd}"
            )
            return ChatResponse(
                response=f"Approval needed: {assessment.confirmation_prompt}",
                requires_approval=True,
                approval_prompt=assessment.confirmation_prompt,
                approval_token=token,
                status="awaiting_approval"
            )

    # 4. Check if planning is required via LangGraph
    # When user asks for a complex multi-tool system plan (e.g., 'plan and install', 'setup workflow')
    if decision.intent == "COMPLEX_PLAN" and pilot_agent_graph is not None:
        try:
            logger.info(f"Delegating complex plan to LangGraph StateGraph: '{user_msg}'")
            initial_state = {
                "user_goal": user_msg,
                "current_step_index": 0,
                "plan": [],
                "retry_count": 0,
                "max_retries": 2,
                "step_verified": True,
                "is_finished": False,
                "is_approved": True,
                "requires_approval": False
            }
            graph_result = await pilot_agent_graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": session_id}}
            )
            summary = graph_result.get("final_summary", "LangGraph plan execution completed.")
            return ChatResponse(
                response=summary,
                tool_executed="langgraph_planner",
                tool_result=graph_result,
                status="completed"
            )
        except Exception as ge:
            logger.warning(f"LangGraph execution exception: {ge}. Falling back to direct tool execution.")

    # 5. Execute tool
    result = tool_registry.execute(tool_name, **params)
    if asyncio.iscoroutine(result):
        result = await result

    # Intercept confirmation required results from tools (e.g. restart_pc, sleep_pc)
    if isinstance(result, dict) and result.get("status") == "confirmation_required":
        req_token = approval_manager.create_pending_approval(
            action_type=tool_name,
            target=str(params),
            payload={"tool_name": tool_name, "params": {**params, "confirmed": True}},
            prompt=result.get("message", f"Confirmation required to execute {tool_name}")
        )
        return ChatResponse(
            response=result.get("message", "Confirmation required."),
            requires_approval=True,
            approval_token=req_token,
            approval_prompt=result.get("message"),
            status="awaiting_approval"
        )

    # Format human-friendly response for React UI
    if tool_name == "open_app":
        resp_text = f"Launched {params['app_name']} on your desktop."
    elif tool_name == "open_anything":
        resp_text = result.get("message", f"Opened {params.get('target')}.")
    elif tool_name == "search_files":
        total = result.get("total_found", 0)
        if total == 0:
            resp_text = f"No files found matching '{params.get('query')}'."
        else:
            top_files = [f"• {f['name']} ({f['size']}) -> {f['path']}" for f in result.get("files", [])[:5]]
            resp_text = f"Found {total} files matching '{params.get('query')}':\n" + "\n".join(top_files)
    elif tool_name in ["volume_up", "volume_down", "mute_volume", "set_brightness", "empty_recycle_bin", "lock_pc", "schedule_shutdown", "cancel_shutdown", "restart_pc", "sleep_pc"]:
        resp_text = result.get("message", f"Executed {tool_name}.")
    elif tool_name == "get_system_metrics":
        m = result.get("system_metrics", {})
        resp_text = f"RAM Status: {m.get('UsedRAM_GB', 0)} GB used / {m.get('TotalRAM_GB', 0)} GB total ({m.get('FreeRAM_GB', 0)} GB free)."
    elif tool_name == "clipboard_summarize":
        resp_text = f"📋 Summary of copied text:\n\n{result.get('summary', result.get('message', ''))}"
    elif tool_name == "clipboard_translate":
        resp_text = f"🌐 Translation ({result.get('target_language', 'Urdu')}):\n\n{result.get('translation', result.get('message', ''))}"
    elif tool_name == "clipboard_rewrite":
        resp_text = f"✍️ Rewritten text ({result.get('style', 'professional')}):\n\n{result.get('rewritten_text', result.get('message', ''))}"
    elif tool_name == "clipboard_format_markdown":
        resp_text = f"📝 Formatted Markdown:\n\n{result.get('markdown', result.get('message', ''))}"
    elif tool_name in ["file_copy", "file_move", "file_move_by_extension", "file_rename", "file_compress_zip", "file_extract_zip", "folder_auto_organize", "download_file", "download_media", "organize_downloads", "take_screenshot", "extract_screen_text", "explain_screen", "find_and_click_button", "web_search", "open_multiple_tabs", "ai_writing_assistant"]:
        resp_text = result.get("message", f"Executed {tool_name} successfully.")
    elif tool_name == "launch_vscode":
        resp_text = "Visual Studio Code has been launched."
    elif tool_name == "analyze_disk_storage":
        scanned = result.get("total_scanned_files", 0)
        reclaimable = result.get("estimated_reclaimable_space", "0 B")
        token = result.get("safety_confirmation_token")
        resp_text = f"Scanned {scanned} files. Found {reclaimable} of safe cleanup candidates. Approval required to delete."
        return ChatResponse(
            response=resp_text,
            tool_executed=tool_name,
            tool_result=result,
            requires_approval=True if token else False,
            approval_token=token,
            approval_prompt="Do you approve purging identified temporary files?",
            status="awaiting_approval" if token else "completed"
        )
    else:
        resp_text = f"Executed {tool_name} successfully."

    # Persist chat turn and session in SQLite database
    try:
        with session_factory() as db:
            # Upsert chat session
            sess = db.query(ChatSessionModel).filter_by(session_id=session_id).first()
            if not sess:
                sess = ChatSessionModel(session_id=session_id, title=user_msg[:60])
                db.add(sess)
            # Add user message
            db.add(ChatMessageModel(
                session_id=session_id,
                role="user",
                content=user_msg,
                intent=decision.intent
            ))
            # Add assistant message
            db.add(ChatMessageModel(
                session_id=session_id,
                role="assistant",
                content=resp_text,
                intent=decision.intent,
                tool_executed=tool_name
            ))
            db.commit()
    except Exception as dbe:
        logger.debug(f"Non-critical DB logging bypass: {dbe}")

    return ChatResponse(
        response=resp_text,
        tool_executed=tool_name,
        tool_result=result,
        status="completed"
    )


@chat_router.post("/chat/approve", response_model=ChatResponse)
async def handle_approval(request: ChatApprovalRequest):
    """
    Submits user approval/rejection for actions flagged by the AI safety layer.
    Validates cryptographic approval tokens, enforces single-use & TTL, and executes exact payload.
    """
    if not request.approved:
        approval_manager.reject_token(request.token)
        return ChatResponse(
            response="Action rejected by user. Safe state preserved.",
            status="completed"
        )

    # 1. Check legacy disk cleanup token
    if request.token.startswith("CONFIRM-CLEANUP"):
        result = tool_registry.execute(
            "confirm_disk_cleanup",
            confirmation_token=request.token,
            user_approval=True
        )
        return ChatResponse(
            response=f"Cleanup completed: Purged {result.get('deleted_items', 0)} files ({result.get('reclaimed_space', '0 B')} reclaimed).",
            tool_executed="confirm_disk_cleanup",
            tool_result=result,
            status="completed"
        )

    # 2. Check and consume cryptographically bound approval token
    pending = approval_manager.consume_token(request.token)
    if not pending:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or previously consumed approval token."
        )

    payload = pending.payload
    tool_name = payload.get("tool_name")
    params = payload.get("params", {})

    logger.info(f"Executing approved payload for token {request.token}: Tool '{tool_name}' with params {params}")
    try:
        result = tool_registry.execute(tool_name, **params)
        if asyncio.iscoroutine(result):
            result = await result

        return ChatResponse(
            response=f"Successfully executed approved operation '{pending.action_type}': {result.get('message', 'Done') if isinstance(result, dict) else 'Completed'}",
            tool_executed=tool_name,
            tool_result=result,
            status="completed"
        )
    except Exception as e:
        logger.error(f"Failed to execute approved operation for token {request.token}: {e}")
        return ChatResponse(
            response=f"Approved operation failed during execution: {e}",
            status="failed"
        )


@chat_router.get("/capabilities")
async def get_agent_capabilities():
    """Returns all 10 core agent capability categories and example prompts for the UI Dashboard."""
    return {
        "total_categories": 10,
        "total_registered_tools": len(tool_registry._tools),
        "categories": [
            {
                "id": 1,
                "title": "1. Open Anything",
                "icon": "🚀",
                "description": "Apps, Websites, Drives (C:/D:/E:), This PC, Downloads & Folders",
                "examples": ["open downloads", "open E drive", "open my pc", "open notepad", "open calculator"]
            },
            {
                "id": 2,
                "title": "2. Search Files & Folders",
                "icon": "🔍",
                "description": "Instant recursive file search, text preview & Explorer reveal",
                "examples": ["find settings.py", "search all py files", "dhundo requirements.txt"]
            },
            {
                "id": 3,
                "title": "3. Smart File Management",
                "icon": "📁",
                "description": "Copy, Move, Rename, Zip/Unzip & Auto-Organize messy folders",
                "examples": ["organize downloads", "zip logs folder"]
            },
            {
                "id": 4,
                "title": "4. Clipboard AI",
                "icon": "📋",
                "description": "Summarize, Translate (Urdu/English), Rewrite & Markdown format",
                "examples": ["summarize clipboard", "translate clipboard to urdu", "rewrite clipboard professionally", "clipboard to markdown"]
            },
            {
                "id": 5,
                "title": "5. Browser Automation",
                "icon": "🌐",
                "description": "Smart Google, YouTube & GitHub searches + multi-tab workflows",
                "examples": ["open browser and search pak vs sri lanka test match", "open youtube and search AI agents"]
            },
            {
                "id": 6,
                "title": "6. Screenshot & Screen Vision",
                "icon": "🖥️",
                "description": "Capture screenshots, OCR text extraction & AI screen explanation",
                "examples": ["take a screenshot", "explain screen", "extract text from screen"]
            },
            {
                "id": 7,
                "title": "7. System Control",
                "icon": "⚙️",
                "description": "Volume, Brightness, Mute, RAM Status, Recycle Bin & Power Timer",
                "examples": ["ram usage", "volume up", "vlume low", "mute volume", "brightness 75", "empty recycle bin"]
            },
            {
                "id": 8,
                "title": "8. AI Writing Assistant",
                "icon": "✍️",
                "description": "In-app grammar fix, professional polish & email reply generator",
                "examples": ["rewrite professionally", "improve grammar"]
            },
            {
                "id": 9,
                "title": "9. Download Manager",
                "icon": "⬇️",
                "description": "Direct URL file downloads, yt-dlp media & Downloads organizer",
                "examples": ["organize downloads folder"]
            },
            {
                "id": 10,
                "title": "10. Multi-Step Workflows",
                "icon": "🤖",
                "description": "Chained physical desktop actions (Open app -> Focus -> Type/Calculate)",
                "examples": ["Open Notepad and type DesktopPilot is running autonomously", "Open Calculator and calculate 25*4"]
            }
        ]
    }

