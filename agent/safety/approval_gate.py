"""
Cryptographically-backed Human-in-the-Loop Approval Manager for DesktopPilot AI.
Safely stores, validates, expires, and binds approval tokens to exact operational payloads.
"""

import time
import uuid
import secrets
from typing import Dict, Any, Optional
from utils.logger import logger


class PendingApproval:
    """Represents an intercepted high/medium-impact action awaiting human sign-off."""

    def __init__(
        self,
        token: str,
        action_type: str,
        target: str,
        payload: Dict[str, Any],
        prompt: str,
        ttl_seconds: int = 300  # 5 minutes
    ):
        self.token = token
        self.action_type = action_type
        self.target = target
        self.payload = payload
        self.prompt = prompt
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.is_executed = False

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class ApprovalManager:
    """
    Manages security tokens for actions requiring human confirmation.
    Guarantees:
    - Tokens are cryptographically random (secrets.token_urlsafe).
    - Every token is strictly single-use (cannot be replayed).
    - Tokens expire after TTL (default 300s).
    - Exact payload is executed only when approved.
    """

    def __init__(self):
        self._pending: Dict[str, PendingApproval] = {}

    def create_pending_approval(
        self,
        action_type: str,
        target: str,
        payload: Dict[str, Any],
        prompt: str,
        ttl_seconds: int = 300
    ) -> str:
        """Issues and registers a new cryptographically bound approval token."""
        token = f"DP_AUTH_{secrets.token_urlsafe(16)}"
        record = PendingApproval(
            token=token,
            action_type=action_type,
            target=target,
            payload=payload,
            prompt=prompt,
            ttl_seconds=ttl_seconds
        )
        self._pending[token] = record
        logger.info(f"Generated approval token {token} for action '{action_type}' on '{target}' (TTL: {ttl_seconds}s)")
        return token

    def get_pending(self, token: str) -> Optional[PendingApproval]:
        """Retrieves active pending approval record without consuming it."""
        record = self._pending.get(token)
        if not record:
            return None
        if record.is_expired or record.is_executed:
            return None
        return record

    def consume_token(self, token: str) -> Optional[PendingApproval]:
        """
        Validates, marks as executed, and removes token from pending pool.
        Returns the PendingApproval record if valid, otherwise None.
        """
        record = self._pending.get(token)
        if not record:
            logger.warning(f"Rejected unknown or missing approval token: {token}")
            return None

        if record.is_expired:
            logger.warning(f"Rejected expired approval token: {token}")
            self._pending.pop(token, None)
            return None

        if record.is_executed:
            logger.warning(f"Rejected re-used approval token: {token}")
            return None

        record.is_executed = True
        self._pending.pop(token, None)
        return record

    def reject_token(self, token: str) -> bool:
        """Discards a pending approval on user rejection."""
        if token in self._pending:
            self._pending.pop(token)
            logger.info(f"Pending approval token {token} was cancelled by user.")
            return True
        return False

    def purge_expired(self):
        """Purges any stale approval tokens."""
        now = time.time()
        expired = [t for t, rec in self._pending.items() if now > rec.expires_at]
        for t in expired:
            self._pending.pop(t, None)


approval_manager = ApprovalManager()

