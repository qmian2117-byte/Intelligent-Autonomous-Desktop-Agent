"""
Database audit models for DesktopPilot AI.
Tracks all autonomous actions, tool invocations, and human approvals.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.session import Base


class TaskRun(Base):
    """Represents a high-level user request or automated goal."""
    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running, completed, failed, paused
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    final_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    actions: Mapped[list["ActionAuditLog"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class ActionAuditLog(Base):
    """Records an individual tool invocation executed by the agent."""
    __tablename__ = "action_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_id: Mapped[int] = mapped_column(Integer, default=0)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    result_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["TaskRun"] = relationship(back_populates="actions")


class ApprovalRecord(Base):
    """Audit log of Human-in-the-Loop approval requests."""
    __tablename__ = "approval_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, approved, rejected
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)



class ChatSessionModel(Base):
    """Stores user chat sessions."""
    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Desktop Session")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessageModel(Base):
    """Stores individual conversational turns."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_executed: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
