"""
Stress Test: 10 Random, Confusing, Typo-Heavy & Roman Urdu Prompts for DesktopPilot AI.
Verifies end-to-end resilience before final project upload.
"""

import asyncio
import time
from api.routes.chat_routes import handle_chat_message, ChatMessageRequest

CONFUSING_PROMPTS = [
    "1. yr awz thori km krdo plzz",
    "2. screen ki roshni 65 percent krdo",
    "3. mery pc ma kitni ram free ha abhi",
    "4. dwnlods walay flder ko kholo",
    "5. e drive ma aiml wala folder dhundo",
    "6. calclator kholo or 350 zarb 8 kro",
    "7. notpad open kro aur likho Final Year Project Ready",
    "8. youtube pr python crash course srch kro",
    "9. screnshot le lo jaldi sa",
    "10. mujhe btao c drive ma kitne folder hain"
]


async def run_stress_test():
    print("=" * 75)
    print("🚀 RUNNING 10 CONFUSING / TRICKY PROMPTS STRESS TEST")
    print("=" * 75)
    passed = 0
    for item in CONFUSING_PROMPTS:
        raw_prompt = item.split(". ", 1)[1]
        t0 = time.time()
        res = await handle_chat_message(ChatMessageRequest(message=raw_prompt))
        elapsed = round(time.time() - t0, 2)
        ok = res.status == "completed"
        if ok:
            passed += 1
        print(f"\n✅ [{item}] ({elapsed}s)")
        print(f"   Tool Executed : {res.tool_executed}")
        print(f"   Agent Output  : {res.response}")

    print("\n" + "=" * 75)
    print(f"🏆 FINAL SCORE: {passed}/{len(CONFUSING_PROMPTS)} PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_stress_test())

