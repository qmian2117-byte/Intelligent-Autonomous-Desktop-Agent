"""
Test suite verifying Secure Terminal Tool and File Manager Tool.
"""

from tools.system.terminal import terminal_tool
from tools.system.file_manager import file_manager_tool


def test_terminal():
    print("=== Testing Secure Terminal Tool ===")

    # 1. Normal safe command
    res = terminal_tool.execute("python --version")
    print(f"[Safe Command] exit_code={res.exit_code}, stdout='{res.stdout}', success={res.is_success}")
    assert res.is_success is True

    # 2. Blocked dangerous command
    dangerous = r"rmdir /s /q C:\\"
    block_res = terminal_tool.execute(dangerous)
    print(f"[Dangerous Command] is_blocked={block_res.is_blocked}, reason='{block_res.block_reason}'")
    assert block_res.is_blocked is True


def test_file_manager():
    print("\n=== Testing File Manager & Safety Confirmation ===")

    # Scan current workspace directory
    report = file_manager_tool.analyze_storage(".", large_file_threshold_mb=10)
    print(f"Scanned files: {report.total_scanned_files}")
    print(f"Total size: {report.total_size_readable}")
    print(f"Safety confirmation token generated: {report.safety_confirmation_token}")
    print(f"Warning notice: {report.warning_notice}")

    # Test safety denial without explicit user approval
    if report.safety_confirmation_token:
        attempt = file_manager_tool.execute_confirmed_cleanup(
            confirmation_token=report.safety_confirmation_token,
            user_explicit_approval=False
        )
        print(f"Cleanup without approval: status={attempt['status']}, msg='{attempt['message']}'")
        assert attempt["status"] == "aborted"


if __name__ == "__main__":
    test_terminal()
    test_file_manager()
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

