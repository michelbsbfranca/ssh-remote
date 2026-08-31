"""Gerenciamento (CRUD) das categorias de sessões, salvas em ~/.ssh_remote/categories.json."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import crypto

CATEGORIES_FILE = crypto.CONFIG_DIR / "categories.json"


@dataclass
class Category:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""


class CategoryManager:
    def __init__(self, path: Path = CATEGORIES_FILE):
        self.path = path
        self.categories: list[Category] = []
        self.load()

    def load(self) -> None:
        crypto._ensure_config_dir()
        if not self.path.exists():
            self.categories = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = []
        self.categories = [Category(**item) for item in raw]

    def save(self) -> None:
        crypto._ensure_config_dir()
        data = [asdict(c) for c in self.categories]
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, category: Category) -> None:
        self.categories.append(category)
        self.save()

    def rename(self, category_id: str, new_name: str) -> None:
        for c in self.categories:
            if c.id == category_id:
                c.name = new_name
                break
        self.save()

    def delete(self, category_id: str) -> None:
        self.categories = [c for c in self.categories if c.id != category_id]
        self.save()

    def get(self, category_id: str) -> Category | None:
        return next((c for c in self.categories if c.id == category_id), None)

    def list_sorted(self) -> list[Category]:
        return sorted(self.categories, key=lambda c: c.name.lower())
