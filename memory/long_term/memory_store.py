"""
Long-Term Vector Memory System for DesktopPilot AI.
Persists past errors, verified solutions, user preferences, and successful command recipes.
Uses ChromaDB with a graceful fallback vector engine.
"""

import json
import uuid
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from utils.logger import logger

CHROMA_STORAGE_DIR = Path("memory/chroma_db")
CHROMA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

FALLBACK_STORE_FILE = Path("memory/long_term/memory_store.json")


class MemoryRecord(BaseModel):
    id: str
    category: str  # problem_solution, user_preference, successful_command
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class LongTermMemoryStore:
    """
    Semantic long-term memory powered by ChromaDB.
    Enables DesktopPilot AI to remember past problems and instantly recognize solutions.
    """

    def __init__(self):
        self._use_chroma = False
        self._client = None
        self._collections: Dict[str, Any] = {}
        self._fallback_records: List[MemoryRecord] = []

        self._initialize_storage()

    def _initialize_storage(self):
        """Attempts to load ChromaDB persistent client; falls back cleanly if not installed."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=str(CHROMA_STORAGE_DIR.resolve()),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            # Initialize specialized collections
            self._collections["problem_solutions"] = self._client.get_or_create_collection(
                name="problem_solutions",
                metadata={"description": "Known errors, exceptions, and working fixes"}
            )
            self._collections["user_preferences"] = self._client.get_or_create_collection(
                name="user_preferences",
                metadata={"description": "User habits, directories, and preferences"}
            )
            self._collections["successful_commands"] = self._client.get_or_create_collection(
                name="successful_commands",
                metadata={"description": "Proven command recipes that succeeded"}
            )
            self._use_chroma = True
            logger.info("ChromaDB vector memory initialized successfully.")
        except ImportError:
            logger.warning("ChromaDB not installed. Using local JSON vector-fallback engine.")
            self._load_fallback_store()

    def _load_fallback_store(self):
        """Loads fallback memory store from disk."""
        if FALLBACK_STORE_FILE.exists():
            try:
                with open(FALLBACK_STORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._fallback_records = [MemoryRecord(**item) for item in data]
            except Exception as e:
                logger.error(f"Error loading fallback memory store: {e}")
                self._fallback_records = []
        else:
            self._fallback_records = []

    def _save_fallback_store(self):
        """Saves fallback memory records to disk."""
        try:
            with open(FALLBACK_STORE_FILE, "w", encoding="utf-8") as f:
                json.dump([r.model_dump() for r in self._fallback_records], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fallback memory: {e}")

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Lightweight token-based cosine similarity for fallback vector ranking."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a.intersection(words_b)
        return len(intersection) / (math.sqrt(len(words_a)) * math.sqrt(len(words_b)))

    # ==========================================
    # 1. Problem & Solution Memory
    # ==========================================
    def store_problem_solution(self, problem: str, solution: str, tags: Optional[List[str]] = None) -> str:
        """
        Learns and persists an error pattern and its verified fix.
        Example: problem="npm EACCES error", solution="Run: npm config set prefix ~/.npm-global"
        """
        record_id = f"sol_{uuid.uuid4().hex[:8]}"
        meta = {
            "solution": solution,
            "tags": ",".join(tags or []),
            "stored_at": datetime.utcnow().isoformat()
        }

        if self._use_chroma:
            collection = self._collections["problem_solutions"]
            collection.add(
                ids=[record_id],
                documents=[problem],
                metadatas=[meta]
            )
        else:
            rec = MemoryRecord(
                id=record_id,
                category="problem_solution",
                content=problem,
                metadata=meta
            )
            self._fallback_records.append(rec)
            self._save_fallback_store()

        logger.info(f"Learned solution for problem: '{problem[:40]}...'")
        return record_id

    def recall_solution(self, query_error: str, top_k: int = 1) -> List[Dict[str, Any]]:
        """
        Searches memory for recognized problems and returns the verified solution.
        """
        if self._use_chroma:
            collection = self._collections["problem_solutions"]
            results = collection.query(
                query_texts=[query_error],
                n_results=top_k
            )
            recalled = []
            if results and results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    recalled.append({
                        "id": results["ids"][0][i],
                        "matched_problem": results["documents"][0][i],
                        "solution": results["metadatas"][0][i].get("solution"),
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })
            return recalled
        else:
            # Fallback search
            scored = []
            for r in self._fallback_records:
                if r.category == "problem_solution":
                    sim = self._text_similarity(query_error, r.content)
                    if sim > 0.15:  # Similarity threshold
                        scored.append((sim, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [
                {
                    "id": r.id,
                    "matched_problem": r.content,
                    "solution": r.metadata.get("solution"),
                    "similarity": round(sim, 2)
                }
                for sim, r in scored[:top_k]
            ]

    # ==========================================
    # 2. User Preferences Memory
    # ==========================================
    def set_user_preference(self, key: str, value: str, context: Optional[str] = None):
        """Remembers a user preference (e.g. key="default_browser", value="chrome")."""
        record_id = f"pref_{key.lower().replace(' ', '_')}"
        meta = {"key": key, "value": value, "context": context or ""}

        if self._use_chroma:
            collection = self._collections["user_preferences"]
            # Upsert
            collection.upsert(
                ids=[record_id],
                documents=[f"{key}: {value}. Context: {context or ''}"],
                metadatas=[meta]
            )
        else:
            # Replace if exists
            self._fallback_records = [r for r in self._fallback_records if r.id != record_id]
            self._fallback_records.append(
                MemoryRecord(id=record_id, category="user_preference", content=f"{key}: {value}", metadata=meta)
            )
            self._save_fallback_store()

        logger.info(f"User preference updated: {key} -> {value}")

    def get_user_preference(self, key: str) -> Optional[str]:
        """Direct lookup for a specific user preference."""
        record_id = f"pref_{key.lower().replace(' ', '_')}"
        if self._use_chroma:
            collection = self._collections["user_preferences"]
            try:
                res = collection.get(ids=[record_id])
                if res and res.get("metadatas") and len(res["metadatas"]) > 0:
                    return res["metadatas"][0].get("value")
            except Exception:
                return None
        else:
            for r in self._fallback_records:
                if r.id == record_id:
                    return r.metadata.get("value")
        return None

    # ==========================================
    # 3. Successful Command Recipes
    # ==========================================
    def store_successful_command(self, goal: str, command: str):
        """Records a verified command that achieved a goal."""
        record_id = f"cmd_{uuid.uuid4().hex[:8]}"
        meta = {"command": command, "stored_at": datetime.utcnow().isoformat()}

        if self._use_chroma:
            collection = self._collections["successful_commands"]
            collection.add(ids=[record_id], documents=[goal], metadatas=[meta])
        else:
            self._fallback_records.append(
                MemoryRecord(id=record_id, category="successful_command", content=goal, metadata=meta)
            )
            self._save_fallback_store()

    def find_command_for_goal(self, goal: str) -> Optional[str]:
        """Finds if a similar goal was previously accomplished and returns the successful command."""
        if self._use_chroma:
            collection = self._collections["successful_commands"]
            res = collection.query(query_texts=[goal], n_results=1)
            if res and res.get("metadatas") and res["metadatas"][0]:
                return res["metadatas"][0][0].get("command")
        else:
            best_cmd = None
            best_sim = 0.0
            for r in self._fallback_records:
                if r.category == "successful_command":
                    sim = self._text_similarity(goal, r.content)
                    if sim > 0.4 and sim > best_sim:
                        best_sim = sim
                        best_cmd = r.metadata.get("command")
            return best_cmd
        return None


# Global long-term memory singleton
memory_store = LongTermMemoryStore()

