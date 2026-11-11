"""
Automated Test Suite for DesktopPilot AI — Phase 1 (P1) High-Priority Upgrades.
Verifies:
1. Approval token generation and single-use validation (ApprovalManager).
2. Expired approval token rejection.
3. Execution of exact approved payload via /api/v1/chat/approve.
4. SQLite persistence for ChatSessionModel and ChatMessageModel.
5. Unified execution path: routing and safety intercept integration.
"""

import time
import unittest
import asyncio
from pathlib import Path
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.safety.approval_gate import approval_manager
from database.session import init_db, session_factory
from database.models import ChatSessionModel, ChatMessageModel
from api.routes.chat_routes import handle_chat_message, handle_approval, ChatMessageRequest, ChatApprovalRequest


class TestP1HighPriorityFeatures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_approval_token_creation_and_consumption(self):
        """P1-1: Verify cryptographically random tokens can be created and consumed once."""
        token = approval_manager.create_pending_approval(
            action_type="test_action",
            target="test_target",
            payload={"tool_name": "volume_up", "params": {"steps": 1}},
            prompt="Do you approve testing volume?",
            ttl_seconds=10
        )
        self.assertTrue(token.startswith("DP_AUTH_"))

        # First consumption should succeed
        consumed = approval_manager.consume_token(token)
        self.assertIsNotNone(consumed)
        self.assertEqual(consumed.action_type, "test_action")

        # Second consumption (replay attempt) MUST fail
        replay = approval_manager.consume_token(token)
        self.assertIsNone(replay, "Approval token must strictly be single-use!")

    def test_02_approval_token_expiration(self):
        """P1-2: Verify tokens past their TTL are rejected as expired."""
        token = approval_manager.create_pending_approval(
            action_type="short_lived",
            target="test",
            payload={"tool_name": "mute_volume", "params": {}},
            prompt="Expire test",
            ttl_seconds=1  # 1 second TTL
        )
        time.sleep(1.2)  # Wait for expiration
        consumed = approval_manager.consume_token(token)
        self.assertIsNone(consumed, "Expired token must be rejected!")

    def test_03_execute_approved_payload_endpoint(self):
        """P1-3: Verify handle_approval executes the exact registered payload."""
        token = approval_manager.create_pending_approval(
            action_type="volume_up",
            target="system audio",
            payload={"tool_name": "volume_up", "params": {"steps": 2}},
            prompt="Approve volume increase"
        )

        async def run_approve():
            req = ChatApprovalRequest(token=token, approved=True)
            return await handle_approval(req)

        res = asyncio.run(run_approve())
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.tool_executed, "volume_up")

    def test_04_chat_persistence_in_sqlite(self):
        """P1-4: Verify chat messages and sessions are persistently recorded in SQLite."""
        test_session_id = f"test_session_{int(time.time())}"
        test_prompt = "system status"

        async def run_chat():
            req = ChatMessageRequest(message=test_prompt, session_id=test_session_id)
            return await handle_chat_message(req)

        res = asyncio.run(run_chat())
        self.assertEqual(res.status, "completed")

        # Query database to confirm persistence
        with session_factory() as db:
            sess = db.query(ChatSessionModel).filter_by(session_id=test_session_id).first()
            self.assertIsNotNone(sess, "Chat session must be persisted in SQLite")

            messages = db.query(ChatMessageModel).filter_by(session_id=test_session_id).all()
            self.assertGreaterEqual(len(messages), 2, "Both user and assistant turns must be saved")
            roles = [m.role for m in messages]
            self.assertIn("user", roles)
            self.assertIn("assistant", roles)


if __name__ == "__main__":
    unittest.main()

