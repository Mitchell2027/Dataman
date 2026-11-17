"""Stubbed data layer.

"""
import json
from pathlib import Path


class MemoryStore:
    """Lives in RAM. Gone when the program ends."""

    def __init__(self):
        self._attempts: list[dict] = []
        self._sets: dict[str, list[str]] = {}

    def save_attempt(self, session_id, problem_id, try_number, answer, correct):
        self._attempts.append({
            "session_id": session_id, "problem_id": problem_id,
            "try": try_number, "answer": answer, "correct": correct,
        })

    def attempts_for(self, session_id, problem_id):
        return [a for a in self._attempts
                if a["session_id"] == session_id and a["problem_id"] == problem_id]

    def attempts_for_player(self, player_id):
        """Convention: session ids look like '<player>:<round>'."""
        prefix = f"{player_id}:"
        return [a for a in self._attempts if a["session_id"].startswith(prefix)]

    def members(self, set_id):
        return list(self._sets.get(set_id, []))

    def add_member(self, set_id, problem_id):
        self._sets.setdefault(set_id, []).append(problem_id)

class JsonFileStore(MemoryStore):
    """Same methods. Writes to a file, so evidence survives a restart.
    Prototype-grade: no locking, no schema versioning, a corrupt file is not handled."""

    def __init__(self, path="dataman_store.json"):
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self._attempts = raw.get("attempts", [])
            self._sets = raw.get("sets", {})

    def _flush(self):
        self.path.write_text(json.dumps(
            {"attempts": self._attempts, "sets": self._sets,},
            indent=2))

    def save_attempt(self, *args):
        super().save_attempt(*args)
        self._flush()

    def add_member(self, *args):
        super().add_member(*args)
        self._flush()
