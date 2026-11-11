"""
Test script verifying WScript.Shell SendKeys and AppActivate.
"""

import subprocess


def test_send_keys(app_name: str, keys: str):
    ps_cmd = f"""
    $ws = New-Object -ComObject WScript.Shell
    $activated = $ws.AppActivate('{app_name}')
    if (-not $activated) {{
        # Try launch if not open
        Start-Process '{app_name}'
        Start-Sleep -Seconds 1
        $ws.AppActivate('{app_name}')
    }}
    Start-Sleep -Milliseconds 600
    $ws.SendKeys('{keys}')
    Write-Output "Sent keys to {app_name} successfully!"
    """
    res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    print("STDOUT:", res.stdout.strip())
    print("STDERR:", res.stderr.strip())


if __name__ == "__main__":
    test_send_keys("Notepad", "Hello from DesktopPilot AI!{{ENTER}}This is 100% automated!{{ENTER}}")

