"""
Native Windows Desktop Input & Window Controller for DesktopPilot AI.
Directly interfaces with Windows user32.dll via ctypes.
Requires zero external pip packages. Works out of the box.
"""

import time
import ctypes
from ctypes import wintypes
from typing import Tuple, Optional, List
from utils.logger import logger

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Configure 64-bit safe ctypes argtypes and restype to prevent handle truncation
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL

user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL

user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

# Mouse Event Flags (Win32 standard)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

# Virtual Key Codes
VK_CODES = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "esc": 0x1B,
    "escape": 0x1B,
    "win": 0x5B,
    "windows": 0x5B,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "delete": 0x2E,
    "f4": 0x73,
    "f5": 0x74,
}


class NativeDesktopController:
    """Controls mouse, keyboard, and screen windows via Windows Win32 API."""

    @staticmethod
    def get_screen_resolution() -> Tuple[int, int]:
        """Returns primary monitor resolution (width, height)."""
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        return (width, height)

    @staticmethod
    def get_active_window_title() -> str:
        """Returns the title text of the currently active/focused window."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Desktop"
        buffer = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buffer, 512)
        return buffer.value or "Unknown Window"

    @classmethod
    def move_mouse(cls, x: int, y: int, smooth: bool = True) -> str:
        """Moves cursor to (x, y) coordinates."""
        width, height = cls.get_screen_resolution()
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))

        if smooth:
            # Smooth interpolation
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            cur_x, cur_y = pt.x, pt.y
            steps = 15
            for i in range(1, steps + 1):
                nx = int(cur_x + (x - cur_x) * (i / steps))
                ny = int(cur_y + (y - cur_y) * (i / steps))
                user32.SetCursorPos(nx, ny)
                time.sleep(0.01)

        user32.SetCursorPos(x, y)
        return f"Mouse moved to ({x}, {y})"

    @classmethod
    def click(cls, x: int, y: int, button: str = "left") -> str:
        """Moves to (x, y) and performs a click."""
        cls.move_mouse(x, y, smooth=True)
        time.sleep(0.05)

        if button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        logger.info(f"Native click at ({x}, {y}) [{button}]")
        return f"Clicked ({x}, {y})"

    @classmethod
    def double_click(cls, x: int, y: int) -> str:
        """Performs a double click at (x, y)."""
        cls.click(x, y)
        time.sleep(0.08)
        cls.click(x, y)
        return f"Double-clicked ({x}, {y})"

    @classmethod
    def key_down(cls, vk_code: int):
        user32.keybd_event(vk_code, 0, 0, 0)

    @classmethod
    def key_up(cls, vk_code: int):
        user32.keybd_event(vk_code, 0, 2, 0)

    @classmethod
    def press_key(cls, key: str) -> str:
        """Presses and releases a single key."""
        k = key.lower().strip()
        vk = VK_CODES.get(k)
        if vk is None and len(k) == 1:
            vk = ord(k.upper())

        if vk is not None:
            cls.key_down(vk)
            time.sleep(0.05)
            cls.key_up(vk)
            return f"Pressed '{key}'"
        return f"Unknown key '{key}'"

    @classmethod
    def hotkey(cls, *keys: str) -> str:
        """Presses key combo (e.g. ['ctrl', 's'] or ['alt', 'f4'])."""
        resolved_vks = []
        for k in keys:
            normalized = k.lower().strip()
            vk = VK_CODES.get(normalized)
            if vk is None and len(normalized) == 1:
                vk = ord(normalized.upper())
            if vk:
                resolved_vks.append(vk)

        for vk in resolved_vks:
            cls.key_down(vk)
            time.sleep(0.02)

        time.sleep(0.05)

        for vk in reversed(resolved_vks):
            cls.key_up(vk)
            time.sleep(0.02)

        combo = "+".join(keys)
        logger.info(f"Native hotkey triggered: {combo}")
        return f"Triggered hotkey {combo}"

    @classmethod
    def find_window_by_title(cls, app_title_substr: str) -> Optional[int]:
        """Finds the first visible top-level window matching app_title_substr."""
        hwnds = []
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if app_title_substr.lower() in buff.value.lower():
                        hwnds.append(hwnd)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return hwnds[0] if hwnds else None

    @classmethod
    def find_and_click_ui_element(cls, app_title: str, control_text_or_class: str) -> Optional[Tuple[int, int]]:
        """
        Uses Win32 FindWindowExW to locate a child control/button inside an application window,
        computes its bounding rectangle, and clicks the center of the control.
        """
        parent_hwnd = cls.find_window_by_title(app_title)
        if not parent_hwnd:
            return None

        # Enumerate child windows to find matching control text or class name
        child = None
        target_child = None
        while True:
            child = user32.FindWindowExW(parent_hwnd, child, None, None)
            if not child:
                break
            length = user32.GetWindowTextLengthW(child)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(child, buf, length + 1)
            if control_text_or_class.lower() in buf.value.lower():
                target_child = child
                break

        if not target_child:
            return None

        rect = wintypes.RECT()
        if user32.GetWindowRect(target_child, ctypes.byref(rect)):
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            cls.click(cx, cy)
            logger.info(f"Clicked Win32 UI Element '{control_text_or_class}' inside '{app_title}' at ({cx}, {cy})")
            return (cx, cy)
        return None

    @classmethod
    def force_bring_to_foreground(cls, app_title_or_hwnd) -> bool:
        """
        Uses Win32 AttachThreadInput + SetForegroundWindow to bypass Windows focus-lock
        and forcibly bring the target window to the front of the user's desktop.
        Accepts either a title substring (str) or window handle (int).
        """
        if isinstance(app_title_or_hwnd, int):
            target_hwnd = app_title_or_hwnd
        else:
            target_hwnd = cls.find_window_by_title(str(app_title_or_hwnd))

        if not target_hwnd:
            return False
        try:
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_SHOWWINDOW = 0x0040
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002

            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            user32.SetWindowPos(target_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            user32.SetWindowPos(target_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

            cur_thread = kernel32.GetCurrentThreadId()
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
            target_thread = user32.GetWindowThreadProcessId(target_hwnd, None)

            if fg_thread and fg_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, fg_thread, True)
            if target_thread and target_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, target_thread, True)

            # Simulate Alt key press/release to unlock Windows SetForegroundWindow restriction
            user32.keybd_event(0x12, 0, 0, 0)
            user32.SetForegroundWindow(target_hwnd)
            user32.BringWindowToTop(target_hwnd)
            user32.SetFocus(target_hwnd)
            user32.keybd_event(0x12, 0, 2, 0)

            if target_thread and target_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, target_thread, False)
            if fg_thread and fg_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, fg_thread, False)
            time.sleep(0.25)
            return True
        except Exception as e:
            logger.warning(f"Error in force_bring_to_foreground: {e}")
            return False

    @classmethod
    def send_keys_to_app(cls, app_title: str, text: str) -> str:
        """
        Brings the target application window to the foreground and types directly into it.
        """
        # Try Win32 Thread-attached Foreground activation first
        activated = cls.force_bring_to_foreground(app_title)
        if activated:
            time.sleep(0.2)
            cls.type_text(text)
            logger.info(f"Direct typed into '{app_title}': '{text}'")
            return f"Typed '{text}' into {app_title}"

        # Fallback to WScript.Shell
        import subprocess
        escaped_chars = []
        for ch in text:
            if ch in "+^%~(){}[]":
                escaped_chars.append(f"{{{ch}}}")
            else:
                escaped_chars.append(ch)
        safe_keys = "".join(escaped_chars).replace("'", "''")

        ps_script = f"""
        $ws = New-Object -ComObject WScript.Shell
        $act = $ws.AppActivate('{app_title}')
        if (-not $act) {{
            Start-Sleep -Milliseconds 400
            $ws.AppActivate('{app_title}')
        }}
        Start-Sleep -Milliseconds 500
        $ws.SendKeys('{safe_keys}')
        """
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            return f"Typed '{text}' into {app_title}"
        except Exception as e:
            return f"Error: {e}"

    @classmethod
    def type_text(cls, text: str, interval: float = 0.03) -> str:
        """Types text character by character into the currently focused window."""
        # Use Windows SendInput unicode event to support all characters, symbols, and spaces
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        class INPUT(ctypes.Structure):
            class _I(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("_i",)
            _fields_ = [("type", ctypes.c_ulong), ("_i", _I)]

        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1
        VK_RETURN = 0x0D

        for char in text:
            # If newline or carriage return, send true hardware VK_RETURN instead of scan code
            if char in ("\r", "\n"):
                inp_down = INPUT(type=INPUT_KEYBOARD)
                inp_down.ki = KEYBDINPUT(wVk=VK_RETURN, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
                user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

                inp_up = INPUT(type=INPUT_KEYBOARD)
                inp_up.ki = KEYBDINPUT(wVk=VK_RETURN, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
                user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
                time.sleep(interval)
                continue

            # Standard Unicode Character Key down
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.ki = KEYBDINPUT(wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=None)
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

            # Key up
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.ki = KEYBDINPUT(wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

            time.sleep(interval)

        return f"Typed {len(text)} characters"


native_desktop = NativeDesktopController()

