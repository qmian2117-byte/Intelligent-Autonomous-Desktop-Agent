"""
Comprehensive test verifying:
1. AI Safety Layer & Risk Analyzer
2. Application Control Tool with Whitelist
3. Long-Term Vector Memory (ChromaDB architecture)
"""

from agent.safety.risk_analyzer import safety_analyzer, RiskLevel
from tools.system.app_controller import app_controller
from memory.long_term.memory_store import memory_store


def test_safety_analyzer():
    print("=== 1. Testing AI Safety Layer & Risk Analyzer ===")

    # Test High Risk: Format Drive
    r_high = safety_analyzer.evaluate_command("format D: /fs:NTFS")
    print(f"[HIGH RISK TEST] level={r_high.level}, blocked={r_high.level == RiskLevel.HIGH}")
    assert r_high.level == RiskLevel.HIGH

    # Test High Risk: Kill Windows Core Process
    r_proc = safety_analyzer.evaluate_process_termination("csrss.exe")
    print(f"[CORE PROCESS KILL TEST] level={r_proc.level}, blocked={r_proc.level == RiskLevel.HIGH}")
    assert r_proc.level == RiskLevel.HIGH

    # Test Medium Risk: Global Install
    r_med = safety_analyzer.evaluate_command("npm install -g n8n")
    print(f"[MEDIUM RISK TEST] level={r_med.level}, requires_approval={r_med.requires_approval}")
    assert r_med.level == RiskLevel.MEDIUM
    assert r_med.requires_approval is True

    # Test Low Risk: Check Node Version
    r_low = safety_analyzer.evaluate_command("node --version")
    print(f"[LOW RISK TEST] level={r_low.level}, requires_approval={r_low.requires_approval}")
    assert r_low.level == RiskLevel.LOW
    assert r_low.requires_approval is False


def test_app_controller():
    print("\n=== 2. Testing Application Control Tool ===")

    # Test Whitelist validation: Unknown app rejected
    res_bad = app_controller.launch_app("malicious_worm_payload")
    print(f"[WHITELIST TEST] success={res_bad.is_success}, msg='{res_bad.message}'")
    assert res_bad.is_success is False

    # Test Safe Close: Block attempt to kill Windows Explorer
    res_close_exp = app_controller.close_app("explorer.exe")
    print(f"[CLOSE BLOCKED TEST] success={res_close_exp.is_success}, msg='{res_close_exp.message}'")
    assert res_close_exp.is_success is False
    assert "Blocked by Safety Layer" in res_close_exp.message


def test_long_term_memory():
    print("\n=== 3. Testing Long-Term Memory (ChromaDB Architecture) ===")

    # Store known problem and solution
    problem = "npm ERR! code EACCES permission denied, access '/usr/local/lib/node_modules'"
    solution = "Configure npm to use a user-owned directory: npm config set prefix ~/.npm-global"

    rec_id = memory_store.store_problem_solution(problem=problem, solution=solution, tags=["npm", "permissions"])
    print(f"[MEMORY STORED] ID={rec_id}")

    # Set user preference
    memory_store.set_user_preference(key="default_editor", value="VS Code", context="Prefers code editor")
    pref_val = memory_store.get_user_preference("default_editor")
    print(f"[PREFERENCE RETRIEVED] default_editor = '{pref_val}'")
    assert pref_val == "VS Code"

    # Simulate next time encountering a similar problem:
    user_query_error = "I am getting npm EACCES permission error during installation"
    recalled = memory_store.recall_solution(user_query_error, top_k=1)
    print(f"[RECALLED SOLUTION]")
    for item in recalled:
        print(f" - Matched: '{item['matched_problem'][:50]}...'")
        print(f" - Solution: '{item['solution']}'")
    assert len(recalled) > 0
    assert "npm config set prefix" in recalled[0]["solution"]


if __name__ == "__main__":
    test_safety_analyzer()
    test_app_controller()
    test_long_term_memory()
    print("\n[ALL SAFETY, APP CONTROL & MEMORY TESTS PASSED!]")

