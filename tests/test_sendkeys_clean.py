"""
Test script verifying send_keys_to_app.
"""

import subprocess


def send_keys_to_app(app_title: str, text: str):
    escaped_chars = []
    for ch in text:
        if ch in "+^%~(){}[]":
            escaped_chars.append(f"{{{ch}}}")
        else:
            escaped_chars.append(ch)
    safe_keys = "".join(escaped_chars).replace("'", "''")

    ps_script = f"""
    $ws = New-Object -ComObject WScript.Shell
    $activated = $ws.AppActivate('{app_title}')
    if (-not $activated) {{
        Start-Sleep -Milliseconds 400
        $ws.AppActivate('{app_title}')
    }}
    Start-Sleep -Milliseconds 600
    $ws.SendKeys('{safe_keys}')
    Write-Output "Successfully typed into {app_title}"
    """
    res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    print("Output:", res.stdout.strip())
    print("Errors:", res.stderr.strip())


if __name__ == "__main__":
    send_keys_to_app("Notepad", "DesktopPilot AI typing test successful!\n")

