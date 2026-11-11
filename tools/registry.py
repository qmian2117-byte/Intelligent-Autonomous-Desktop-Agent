"""
Central Tool Registry for DesktopPilot AI.
Exposes tool definitions, JSON schemas for Llama 3.1, and execution dispatchers.
"""

import asyncio
from typing import Dict, Any, Callable
from utils.logger import logger

from tools.desktop.mouse import MouseController
from tools.desktop.keyboard import KeyboardController
from tools.vision.screen import ScreenTools
from tools.system.os_ops import SystemTools
from tools.system.terminal import terminal_tool
from tools.system.file_manager import file_manager_tool
from tools.system.app_controller import app_controller
from tools.vision.ui_grounding import visual_grounding_tool
from tools.voice.voice_tool import voice_tool
from tools.system.system_control import system_control
from tools.system.clipboard_ai import clipboard_ai
from tools.system.universal_launcher import universal_launcher
from tools.system.file_search import file_search_tool
from tools.system.smart_file_ops import smart_file_manager
from tools.system.download_manager import download_manager
from tools.vision.screen_understanding import screen_understanding
from tools.web.browser_automation import browser_automation
from tools.system.writing_assistant import writing_assistant


class ToolRegistry:
    """Manages available agent tools and dynamic execution."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register(self, name: str, func: Callable, schema: Dict[str, Any]):
        """Register a new tool with its callable and schema definition."""
        self._tools[name] = func
        self._schemas[name] = schema
        logger.debug(f"Registered tool: {name}")

    def _register_default_tools(self):
        # 1. Mouse Tools
        self.register(
            name="click",
            func=lambda x, y, button="left": MouseController.click(int(x), int(y), button),
            schema={
                "name": "click",
                "description": "Click at specific screen coordinates (x, y).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate on screen"},
                        "y": {"type": "integer", "description": "Y coordinate on screen"},
                        "button": {"type": "string", "enum": ["left", "right"], "default": "left"}
                    },
                    "required": ["x", "y"]
                }
            }
        )

        self.register(
            name="move_mouse",
            func=lambda x, y: MouseController.move_to(int(x), int(y)),
            schema={
                "name": "move_mouse",
                "description": "Smoothly move mouse pointer to screen coordinates (x, y).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"}
                    },
                    "required": ["x", "y"]
                }
            }
        )

        # 2. Keyboard Tools
        self.register(
            name="type_text",
            func=lambda text: KeyboardController.type_text(str(text)),
            schema={
                "name": "type_text",
                "description": "Type a given text string into the currently active window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to type"}
                    },
                    "required": ["text"]
                }
            }
        )

        self.register(
            name="hotkey",
            func=lambda keys: KeyboardController.hotkey(*keys if isinstance(keys, list) else keys.split("+")),
            schema={
                "name": "hotkey",
                "description": "Trigger a keyboard shortcut combination (e.g. ['ctrl', 'c'] or 'win+r').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keys": {"type": "string", "description": "Keys separated by plus, e.g. 'win+r' or 'ctrl+s'"}
                    },
                    "required": ["keys"]
                }
            }
        )

        # 3. Screen & Vision Tools
        self.register(
            name="capture_screen",
            func=lambda: ScreenTools.capture_screen(),
            schema={
                "name": "capture_screen",
                "description": "Capture full screen screenshot and return the local image path.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        # 4. OS & System Tools
        self.register(
            name="launch_app",
            func=lambda app_name: SystemTools.launch_app(str(app_name)),
            schema={
                "name": "launch_app",
                "description": "Launch a desktop application by name (e.g. 'notepad', 'calc', 'chrome').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Name of app executable to launch"}
                    },
                    "required": ["app_name"]
                }
            }
        )

        # 5. Secure Terminal Execution
        self.register(
            name="run_terminal_command",
            func=lambda command, timeout=30, confirmed=False: terminal_tool.execute(
                command=str(command),
                timeout=int(timeout),
                confirmed_by_user=bool(confirmed)
            ).model_dump(),
            schema={
                "name": "run_terminal_command",
                "description": "Execute a terminal / PowerShell command safely and return stdout/stderr.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to run (e.g. 'node --version')"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                        "confirmed": {"type": "boolean", "description": "True if user confirmed high-risk command", "default": False}
                    },
                    "required": ["command"]
                }
            }
        )

        # 6. Disk & File Management
        self.register(
            name="analyze_disk_storage",
            func=lambda target_dir="C:\\", large_file_threshold_mb=100: file_manager_tool.analyze_storage(
                target_dir=str(target_dir),
                large_file_threshold_mb=int(large_file_threshold_mb)
            ).model_dump(),
            schema={
                "name": "analyze_disk_storage",
                "description": "Scan a directory/drive for large files, temp caches, and disk hogs. Does NOT delete files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_dir": {"type": "string", "description": "Folder or drive letter (e.g. 'C:\\' or 'C:\\Users')", "default": "C:\\"},
                        "large_file_threshold_mb": {"type": "integer", "description": "File size threshold in MB", "default": 100}
                    }
                }
            }
        )

        self.register(
            name="confirm_disk_cleanup",
            func=lambda confirmation_token, user_approval=False: file_manager_tool.execute_confirmed_cleanup(
                confirmation_token=str(confirmation_token),
                user_explicit_approval=bool(user_approval)
            ),
            schema={
                "name": "confirm_disk_cleanup",
                "description": "Deletes safe temp files identified during disk analysis. Requires confirmation_token and explicit approval.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "confirmation_token": {"type": "string", "description": "The unique token generated by analyze_disk_storage"},
                        "user_approval": {"type": "boolean", "description": "Must be True after user provides confirmation"}
                    },
                    "required": ["confirmation_token", "user_approval"]
                }
            }
        )

        # 7. Application Control & Developer Environment
        self.register(
            name="open_app",
            func=lambda app_name, arguments=None: app_controller.launch_app(str(app_name), arguments).model_dump(),
            schema={
                "name": "open_app",
                "description": "Launch an approved whitelisted application (e.g. 'code', 'chrome', 'notepad', 'terminal', 'calc').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Application name or alias"},
                        "arguments": {"type": "string", "description": "Optional CLI arguments or path"}
                    },
                    "required": ["app_name"]
                }
            }
        )

        self.register(
            name="close_app",
            func=lambda app_name, force=False, confirmed=False: app_controller.close_app(
                str(app_name), bool(force), bool(confirmed)
            ).model_dump(),
            schema={
                "name": "close_app",
                "description": "Safely close an application. Intercepted if trying to terminate core Windows processes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Application name to close"},
                        "force": {"type": "boolean", "default": False},
                        "confirmed": {"type": "boolean", "description": "User confirmation flag", "default": False}
                    },
                    "required": ["app_name"]
                }
            }
        )

        self.register(
            name="launch_vscode",
            func=lambda project_path=None: app_controller.launch_vscode(project_path).model_dump(),
            schema={
                "name": "launch_vscode",
                "description": "Launch Visual Studio Code in a target project directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Directory path to open in VS Code"}
                    }
                }
            }
        )

        self.register(
            name="open_browser",
            func=lambda url=None: app_controller.open_browser(url).model_dump(),
            schema={
                "name": "open_browser",
                "description": "Open default web browser to a specified URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Web URL to open (e.g. 'https://github.com')"}
                    }
                }
            }
        )

        self.register(
            name="run_project_command",
            func=lambda command, project_dir=None, confirmed=False: app_controller.run_project_command(
                str(command), project_dir, bool(confirmed)
            ).model_dump(),
            schema={
                "name": "run_project_command",
                "description": "Execute a safe development command inside a project directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to run (e.g. 'npm test', 'git status')"},
                        "project_dir": {"type": "string", "description": "Project directory path"},
                        "confirmed": {"type": "boolean", "default": False}
                    },
                    "required": ["command"]
                }
            }
        )

        # 8. Universal "Open Anything" Launcher
        self.register(
            name="open_anything",
            func=lambda target: universal_launcher.open(str(target)),
            schema={
                "name": "open_anything",
                "description": "Open any app, website, file, drive, or special folder (e.g. 'downloads', 'spotify', 'chatgpt.com', 'excel').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Target app, website, or folder name"}
                    },
                    "required": ["target"]
                }
            }
        )

        # 9. Search Files & Folders
        self.register(
            name="search_files",
            func=lambda query, search_dir=None, extension=None, max_results=15: file_search_tool.search_files(
                str(query), search_dir, extension, int(max_results)
            ),
            schema={
                "name": "search_files",
                "description": "Search for files or folders by name, pattern, or extension across the computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Filename or pattern to search"},
                        "search_dir": {"type": "string", "description": "Optional directory to limit search"},
                        "extension": {"type": "string", "description": "Optional extension filter like 'pdf', 'csv', 'py'"}
                    },
                    "required": ["query"]
                }
            }
        )

        self.register(
            name="preview_file",
            func=lambda file_path: file_search_tool.preview_file(str(file_path)),
            schema={
                "name": "preview_file",
                "description": "Preview first lines of a text/code/csv file or inspect binary file metadata.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Full path to file"}
                    },
                    "required": ["file_path"]
                }
            }
        )

        self.register(
            name="copy_file_path",
            func=lambda file_path: file_search_tool.copy_path_to_clipboard(str(file_path)),
            schema={
                "name": "copy_file_path",
                "description": "Copy absolute file path to the Windows clipboard.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Full path of file"}
                    },
                    "required": ["file_path"]
                }
            }
        )

        self.register(
            name="reveal_file_in_explorer",
            func=lambda file_path: file_search_tool.reveal_in_explorer(str(file_path)),
            schema={
                "name": "reveal_file_in_explorer",
                "description": "Open Windows Explorer and highlight the selected file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Full path of file"}
                    },
                    "required": ["file_path"]
                }
            }
        )

        # 10. Clipboard AI Tools
        self.register(
            name="clipboard_summarize",
            func=lambda: asyncio.run(clipboard_ai.summarize_clipboard()) if not asyncio.get_event_loop().is_running() else clipboard_ai.summarize_clipboard(),
            schema={
                "name": "clipboard_summarize",
                "description": "Read copied text from Windows clipboard, summarize it, and copy summary back to clipboard.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="clipboard_translate",
            func=lambda target_language="Urdu": asyncio.run(clipboard_ai.translate_clipboard(target_language)) if not asyncio.get_event_loop().is_running() else clipboard_ai.translate_clipboard(target_language),
            schema={
                "name": "clipboard_translate",
                "description": "Translate clipboard content into target language (e.g. 'Urdu', 'English', 'Spanish').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_language": {"type": "string", "default": "Urdu"}
                    }
                }
            }
        )

        self.register(
            name="clipboard_rewrite",
            func=lambda style="professional": asyncio.run(clipboard_ai.rewrite_clipboard(style)) if not asyncio.get_event_loop().is_running() else clipboard_ai.rewrite_clipboard(style),
            schema={
                "name": "clipboard_rewrite",
                "description": "Rewrite clipboard text in specified tone ('professional', 'email_reply', 'casual', 'concise').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "style": {"type": "string", "default": "professional"}
                    }
                }
            }
        )

        self.register(
            name="clipboard_format_markdown",
            func=lambda: clipboard_ai.format_as_markdown(),
            schema={
                "name": "clipboard_format_markdown",
                "description": "Convert copied text or tabular data in clipboard into clean GitHub markdown.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        # 11. System Control Tools (Volume, Brightness, Lock, Recycle Bin, Shutdown)
        self.register(
            name="volume_up",
            func=lambda steps=5: system_control.volume_up(int(steps)),
            schema={
                "name": "volume_up",
                "description": "Increase system master volume.",
                "parameters": {
                    "type": "object",
                    "properties": {"steps": {"type": "integer", "default": 5}}
                }
            }
        )

        self.register(
            name="volume_down",
            func=lambda steps=5: system_control.volume_down(int(steps)),
            schema={
                "name": "volume_down",
                "description": "Decrease system master volume.",
                "parameters": {
                    "type": "object",
                    "properties": {"steps": {"type": "integer", "default": 5}}
                }
            }
        )

        self.register(
            name="mute_volume",
            func=lambda: system_control.toggle_mute(),
            schema={
                "name": "mute_volume",
                "description": "Toggle master audio mute/unmute.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="set_brightness",
            func=lambda percent=50: system_control.set_brightness(int(percent)),
            schema={
                "name": "set_brightness",
                "description": "Set monitor screen brightness percentage (0-100).",
                "parameters": {
                    "type": "object",
                    "properties": {"percent": {"type": "integer", "description": "0 to 100", "default": 50}},
                    "required": ["percent"]
                }
            }
        )

        self.register(
            name="empty_recycle_bin",
            func=lambda: system_control.empty_recycle_bin(),
            schema={
                "name": "empty_recycle_bin",
                "description": "Empty the Windows Recycle Bin.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="lock_pc",
            func=lambda: system_control.lock_pc(),
            schema={
                "name": "lock_pc",
                "description": "Lock the Windows PC immediately.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="schedule_shutdown",
            func=lambda minutes=30: system_control.schedule_shutdown(int(minutes)),
            schema={
                "name": "schedule_shutdown",
                "description": "Schedule PC shutdown after a certain number of minutes.",
                "parameters": {
                    "type": "object",
                    "properties": {"minutes": {"type": "integer", "default": 30}},
                    "required": ["minutes"]
                }
            }
        )

        self.register(
            name="cancel_shutdown",
            func=lambda: system_control.cancel_shutdown(),
            schema={
                "name": "cancel_shutdown",
                "description": "Cancel any pending scheduled shutdown or restart.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="restart_pc",
            func=lambda delay_seconds=10: system_control.restart_pc(int(delay_seconds)),
            schema={
                "name": "restart_pc",
                "description": "Restart the Windows computer after a short delay (default 10 seconds).",
                "parameters": {
                    "type": "object",
                    "properties": {"delay_seconds": {"type": "integer", "default": 10}}
                }
            }
        )

        self.register(
            name="sleep_pc",
            func=lambda: system_control.sleep_pc(),
            schema={
                "name": "sleep_pc",
                "description": "Put the Windows computer into Sleep mode immediately.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="get_system_metrics",
            func=lambda: system_control.get_system_battery_and_memory(),
            schema={
                "name": "get_system_metrics",
                "description": "Get RAM and system memory stats.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        # 12. Smart File Operations (Copy, Move, Rename, Zip, Organize)
        self.register(
            name="file_copy",
            func=lambda source, destination: smart_file_manager.copy_item(str(source), str(destination)),
            schema={
                "name": "file_copy",
                "description": "Copy a file or directory to a target path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"}
                    },
                    "required": ["source", "destination"]
                }
            }
        )

        self.register(
            name="file_move",
            func=lambda source, destination: smart_file_manager.move_item(str(source), str(destination)),
            schema={
                "name": "file_move",
                "description": "Move a file or directory to a destination folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"}
                    },
                    "required": ["source", "destination"]
                }
            }
        )

        self.register(
            name="file_move_by_extension",
            func=lambda source_dir, extension, destination_dir: smart_file_manager.move_files_by_extension(
                str(source_dir), str(extension), str(destination_dir)
            ),
            schema={
                "name": "file_move_by_extension",
                "description": "Move all files with a given extension (e.g. 'pdf') to a target folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_dir": {"type": "string"},
                        "extension": {"type": "string"},
                        "destination_dir": {"type": "string"}
                    },
                    "required": ["source_dir", "extension", "destination_dir"]
                }
            }
        )

        self.register(
            name="file_rename",
            func=lambda file_path, new_name: smart_file_manager.rename_item(str(file_path), str(new_name)),
            schema={
                "name": "file_rename",
                "description": "Rename a file or folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "new_name": {"type": "string"}
                    },
                    "required": ["file_path", "new_name"]
                }
            }
        )

        self.register(
            name="file_compress_zip",
            func=lambda target_path, output_zip=None: smart_file_manager.compress_to_zip(str(target_path), output_zip),
            schema={
                "name": "file_compress_zip",
                "description": "Compress a folder or file into a .zip archive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_path": {"type": "string"},
                        "output_zip": {"type": "string"}
                    },
                    "required": ["target_path"]
                }
            }
        )

        self.register(
            name="file_extract_zip",
            func=lambda zip_path, destination_dir=None: smart_file_manager.extract_zip(str(zip_path), destination_dir),
            schema={
                "name": "file_extract_zip",
                "description": "Extract a .zip archive into a target directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zip_path": {"type": "string"},
                        "destination_dir": {"type": "string"}
                    },
                    "required": ["zip_path"]
                }
            }
        )

        self.register(
            name="folder_auto_organize",
            func=lambda target_dir: smart_file_manager.organize_folder(str(target_dir)),
            schema={
                "name": "folder_auto_organize",
                "description": "Auto-organize files in a folder into subfolders (Documents, Images, Videos, Code, Archives).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_dir": {"type": "string"}
                    },
                    "required": ["target_dir"]
                }
            }
        )

        # 13. Download Manager Tools
        self.register(
            name="download_file",
            func=lambda url, filename=None, destination_dir=None: download_manager.download_url(
                str(url), filename, destination_dir
            ),
            schema={
                "name": "download_file",
                "description": "Download any file from a URL to the Downloads folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "filename": {"type": "string"},
                        "destination_dir": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        )

        self.register(
            name="download_media",
            func=lambda url, extract_audio=False: download_manager.download_media_with_ytdlp(
                str(url), bool(extract_audio)
            ),
            schema={
                "name": "download_media",
                "description": "Download video or audio from YouTube / web platforms via yt-dlp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "extract_audio": {"type": "boolean", "default": False}
                    },
                    "required": ["url"]
                }
            }
        )

        self.register(
            name="organize_downloads",
            func=lambda: download_manager.organize_downloads(),
            schema={
                "name": "organize_downloads",
                "description": "Auto-organize the user's Downloads folder into Documents, Videos, Music, Pictures, and Code.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        # 14. Phase 3: Screen Understanding & OCR Tools
        self.register(
            name="take_screenshot",
            func=lambda save_to_pictures=True: screen_understanding.take_screenshot(bool(save_to_pictures)),
            schema={
                "name": "take_screenshot",
                "description": "Capture a screenshot of the screen and save to Pictures/Screenshots.",
                "parameters": {
                    "type": "object",
                    "properties": {"save_to_pictures": {"type": "boolean", "default": True}}
                }
            }
        )

        self.register(
            name="extract_screen_text",
            func=lambda: screen_understanding.extract_text_from_screen(),
            schema={
                "name": "extract_screen_text",
                "description": "Extract visible text from the current screen using OCR.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="explain_screen",
            func=lambda: screen_understanding.explain_screen(),
            schema={
                "name": "explain_screen",
                "description": "Analyze and explain what is currently displayed on the user's screen.",
                "parameters": {"type": "object", "properties": {}}
            }
        )

        self.register(
            name="find_and_click_button",
            func=lambda element_description: screen_understanding.find_and_click_button(str(element_description)),
            schema={
                "name": "find_and_click_button",
                "description": "Visually locate a button or UI element on screen and click it.",
                "parameters": {
                    "type": "object",
                    "properties": {"element_description": {"type": "string"}},
                    "required": ["element_description"]
                }
            }
        )

        # 15. Phase 3: Browser Automation & AI Writing Assistant
        self.register(
            name="web_search",
            func=lambda query, engine="google": browser_automation.web_search(str(query), str(engine)),
            schema={
                "name": "web_search",
                "description": "Open browser and search Google, YouTube, GitHub, or Bing for a query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "engine": {"type": "string", "default": "google"}
                    },
                    "required": ["query"]
                }
            }
        )

        self.register(
            name="open_multiple_tabs",
            func=lambda urls: browser_automation.open_multiple_tabs(urls if isinstance(urls, list) else str(urls).split(",")),
            schema={
                "name": "open_multiple_tabs",
                "description": "Open multiple websites in browser tabs.",
                "parameters": {
                    "type": "object",
                    "properties": {"urls": {"type": "array", "items": {"type": "string"}}},
                    "required": ["urls"]
                }
            }
        )

        self.register(
            name="ai_writing_assistant",
            func=lambda action="professional", target_language="Urdu", auto_paste=False: writing_assistant.improve_text_in_app(
                str(action), str(target_language), bool(auto_paste)
            ),
            schema={
                "name": "ai_writing_assistant",
                "description": "Improve, rewrite, summarize, or translate text in the active application.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "default": "professional"},
                        "target_language": {"type": "string", "default": "Urdu"},
                        "auto_paste": {"type": "boolean", "default": False}
                    }
                }
            }
        )

    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name with parameters."""
        if name not in self._tools:
            return f"Error: Tool '{name}' is not registered."
        try:
            return self._tools[name](**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return f"Error executing tool '{name}': {str(e)}"

    def get_tool_descriptions(self) -> str:
        """Returns concise textual documentation of all registered tools for the LLM prompt."""
        descriptions = []
        for name, spec in self._schemas.items():
            params = ", ".join(spec.get("parameters", {}).get("properties", {}).keys())
            descriptions.append(f"- {name}({params}): {spec.get('description')}")
        return "\n".join(descriptions)


# Global tool registry singleton
tool_registry = ToolRegistry()
