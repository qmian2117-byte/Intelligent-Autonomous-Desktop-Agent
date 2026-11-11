"""
Test script verifying EnumWindows and window focus on Windows.
"""

import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)


def list_windows():
    windows = []

    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                windows.append((hwnd, buf.value))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    print(f"Total visible windows: {len(windows)}")
    for hwnd, title in windows[:8]:
        print(f" - [{hwnd}] '{title}'")
    return windows


if __name__ == "__main__":
    list_windows()

