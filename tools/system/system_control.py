"""
System Control Tool for DesktopPilot AI.
Provides direct control over Windows settings: Volume, Brightness, Recycle Bin,
PC Lock, Sleep/Shutdown timers, and Wi-Fi status.
Zero external heavy dependencies - uses native Windows APIs and PowerShell.
"""

import os
import subprocess
import ctypes
from typing import Dict, Any, Optional
from utils.logger import logger


class WindowsSystemControl:
    """Native Windows System Settings Controller."""

    # Virtual-Key codes for Volume
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    @classmethod
    def _send_vk(cls, vk_code: int, repetitions: int = 1):
        """Dispatches virtual key event via user32."""
        try:
            for _ in range(repetitions):
                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP
        except Exception as e:
            logger.error(f"Failed to send VK code {vk_code}: {e}")

    def volume_up(self, steps: int = 5) -> Dict[str, Any]:
        """Increases master system volume."""
        self._send_vk(self.VK_VOLUME_UP, repetitions=max(1, steps))
        logger.info(f"Increased system volume by {steps} steps.")
        return {"status": "success", "message": f"Volume increased by {steps} steps."}

    def volume_down(self, steps: int = 5) -> Dict[str, Any]:
        """Decreases master system volume."""
        self._send_vk(self.VK_VOLUME_DOWN, repetitions=max(1, steps))
        logger.info(f"Decreased system volume by {steps} steps.")
        return {"status": "success", "message": f"Volume decreased by {steps} steps."}

    def toggle_mute(self) -> Dict[str, Any]:
        """Toggles master volume mute/unmute."""
        self._send_vk(self.VK_VOLUME_MUTE, repetitions=1)
        logger.info("Toggled system audio mute.")
        return {"status": "success", "message": "Master audio mute toggled."}

    def set_brightness(self, percent: int) -> Dict[str, Any]:
        """
        Sets screen brightness level (0 - 100) via WMI.
        Note: Works on laptops and supported integrated displays.
        """
        percent = max(0, min(100, percent))
        cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {percent})"
        try:
            res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info(f"Brightness set to {percent}%.")
                return {"status": "success", "message": f"Screen brightness set to {percent}%."}
            else:
                return {"status": "warning", "message": f"Brightness adjustment not supported on this display hardware: {res.stderr.strip()}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to set brightness: {str(e)}"}

    def empty_recycle_bin(self) -> Dict[str, Any]:
        """Empties the Windows Recycle Bin silently."""
        cmd = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
        try:
            res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=10)
            logger.info("Windows Recycle Bin emptied.")
            return {"status": "success", "message": "Recycle Bin has been emptied."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to empty Recycle Bin: {str(e)}"}

    def lock_pc(self) -> Dict[str, Any]:
        """Locks the Windows workstation immediately."""
        try:
            ctypes.windll.user32.LockWorkStation()
            logger.info("Workstation locked.")
            return {"status": "success", "message": "PC has been locked."}
        except Exception as e:
            # Fallback to rundll32
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return {"status": "success", "message": "PC lock command sent."}

    def schedule_shutdown(self, minutes: int = 1) -> Dict[str, Any]:
        """Schedules a PC shutdown after specified minutes."""
        seconds = max(5, int(minutes * 60))
        cmd = f"shutdown /s /t {seconds}"
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"PC shutdown scheduled in {minutes} minutes.")
                return {"status": "success", "message": f"PC will shut down in {minutes} minute(s) ({seconds}s). Use 'cancel shutdown' to abort."}
            return {"status": "error", "message": res.stderr.strip()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def restart_pc(self, delay_seconds: int = 10, confirmed: bool = False) -> Dict[str, Any]:
        """
        Restarts the Windows PC after a short safety delay.
        Requires explicit confirmation flag to prevent accidental restarts.
        """
        if not confirmed:
            return {
                "status": "confirmation_required",
                "confirmation_token": "CONFIRM_RESTART_PC",
                "message": "Restarting the PC requires explicit confirmation. Please confirm by replying 'yes confirm restart'."
            }
        secs = max(5, int(delay_seconds))
        cmd = ["shutdown.exe", "/r", "/t", str(secs)]
        try:
            res = subprocess.run(cmd, shell=False, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"PC restart scheduled in {secs} seconds.")
                return {"status": "success", "message": f"PC is restarting in {secs} seconds (type 'cancel shutdown' to abort)."}
            return {"status": "error", "message": res.stderr.strip()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sleep_pc(self, confirmed: bool = False) -> Dict[str, Any]:
        """
        Puts the Windows PC into Sleep / Suspend state immediately.
        Requires explicit confirmation flag to prevent unintended sleep states.
        """
        if not confirmed:
            return {
                "status": "confirmation_required",
                "confirmation_token": "CONFIRM_SLEEP_PC",
                "message": "Putting the PC into Sleep mode requires confirmation. Reply with 'yes confirm sleep' to proceed."
            }
        try:
            # SetSuspendState(Hibernate=0, ForceCritical=1, DisableWakeEvent=0)
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            logger.info("PC placed into Sleep mode.")
            return {"status": "success", "message": "Putting PC into Sleep mode..."}
        except Exception as e:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=False)
            return {"status": "success", "message": "Sleep mode command dispatched."}

    def cancel_shutdown(self) -> Dict[str, Any]:
        """Cancels any pending scheduled shutdown."""
        try:
            res = subprocess.run("shutdown /a", shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info("Pending shutdown cancelled.")
                return {"status": "success", "message": "Pending shutdown has been cancelled."}
            return {"status": "info", "message": "No scheduled shutdown was found to cancel."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_system_battery_and_memory(self) -> Dict[str, Any]:
        """Retrieves exact hardware memory metrics via Win32 GlobalMemoryStatusEx."""
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))

            total_gb = round(mem.ullTotalPhys / (1024**3), 2)
            free_gb = round(mem.ullAvailPhys / (1024**3), 2)
            used_gb = round(total_gb - free_gb, 2)
            load_pct = mem.dwMemoryLoad

            return {
                "status": "success",
                "system_metrics": {
                    "TotalRAM_GB": total_gb,
                    "UsedRAM_GB": used_gb,
                    "FreeRAM_GB": free_gb,
                    "MemoryLoad_Percent": load_pct
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


system_control = WindowsSystemControl()
