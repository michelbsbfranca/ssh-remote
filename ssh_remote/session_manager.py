"""Gerenciamento (CRUD) das sessões SSH salvas em ~/.ssh_remote/sessions.json."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import crypto

SESSIONS_FILE = crypto.CONFIG_DIR / "sessions.json"


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    host: str = ""
    port: int = 22
    username: str = ""
    auth_method: str = "password"  # "password" ou "key"
    password_enc: str = ""
    key_path: str = ""
    key_passphrase_enc: str = ""
    category_id: str = ""  # "" = sem categoria

    @property
    def password(self) -> str:
        return crypto.decrypt(self.password_enc)

    @password.setter
    def password(self, value: str) -> None:
        self.password_enc = crypto.encrypt(value)

    @property
    def key_passphrase(self) -> str:
        return crypto.decrypt(self.key_passphrase_enc)

    @key_passphrase.setter
    def key_passphrase(self, value: str) -> None:
        self.key_passphrase_enc = crypto.encrypt(value)


class SessionManager:
    def __init__(self, path: Path = SESSIONS_FILE):
        self.path = path
        self.sessions: list[Session] = []
        self.load()

    def load(self) -> None:
        crypto._ensure_config_dir()
        if not self.path.exists():
            self.sessions = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = []
        self.sessions = [Session(**item) for item in raw]

    def save(self) -> None:
        crypto._ensure_config_dir()
        data = [asdict(s) for s in self.sessions]
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            import os
            import stat

            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def add(self, session: Session) -> None:
        self.sessions.append(session)
        self.save()

    def update(self, session: Session) -> None:
        for i, s in enumerate(self.sessions):
            if s.id == session.id:
                self.sessions[i] = session
                break
        self.save()

    def delete(self, session_id: str) -> None:
        self.sessions = [s for s in self.sessions if s.id != session_id]
        self.save()

    def get(self, session_id: str) -> Session | None:
        return next((s for s in self.sessions if s.id == session_id), None)

    def list_sorted(self) -> list[Session]:
        return sorted(self.sessions, key=lambda s: s.name.lower())
