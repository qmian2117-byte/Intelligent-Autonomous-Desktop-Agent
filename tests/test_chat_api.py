"""
Test suite verifying the FastAPI Chat endpoints directly:
- POST /api/v1/chat with "Open Chrome"
- POST /api/v1/chat with "Clean temporary files"
- POST /api/v1/chat with "Install Python"
- POST /api/v1/chat/approve
"""

import asyncio
from api.routes.chat_routes import handle_chat_message, handle_approval, ChatMessageRequest, ChatApprovalRequest


async def main():
    print("=== 1. Testing Chat: 'Open Chrome' ===")
    req1 = ChatMessageRequest(message="Open Chrome")
    res1 = await handle_chat_message(req1)
    print(f"Tool Executed: {res1.tool_executed}")
    print(f"Response: {res1.response}")
    print(f"Status: {res1.status}")
    assert res1.tool_executed == "open_app"
    assert "chrome" in res1.response.lower()
    assert res1.status == "completed"

    print("\n=== 2. Testing Chat: 'Clean temporary files' ===")
    req2 = ChatMessageRequest(message="Clean temporary files")
    res2 = await handle_chat_message(req2)
    print(f"Tool Executed: {res2.tool_executed}")
    print(f"Response: {res2.response}")
    print(f"Requires Approval: {res2.requires_approval}")
    print(f"Approval Token: {res2.approval_token}")
    assert res2.tool_executed == "analyze_disk_storage"

    if res2.requires_approval:
        print("\n--- Submitting Approval Rejection ---")
        appr_req = ChatApprovalRequest(token=res2.approval_token, approved=False)
        appr_res = await handle_approval(appr_req)
        print(f"Approval Response: {appr_res.response}")
        assert "rejected" in appr_res.response.lower()

    print("\n=== 3. Testing Chat: 'Install Python' ===")
    req3 = ChatMessageRequest(message="Install Python")
    res3 = await handle_chat_message(req3)
    print(f"Tool Executed: {res3.tool_executed}")
    print(f"Response: {res3.response}")
    print(f"Status: {res3.status}")
    assert res3.tool_executed == "run_terminal_command" or res3.status in ["completed", "awaiting_approval"]

    print("\n[ALL REACT-FASTAPI CHAT ENDPOINT LOGIC PASSED SUCCESSFULLY!]")


if __name__ == "__main__":
    asyncio.run(main())
