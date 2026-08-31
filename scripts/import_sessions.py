#!/usr/bin/env python3
"""Importação em lote de sessões (nome + host), com usuário/senha fixos.

Lê os dados de scripts/import_sessions_data.json (não versionado, contém
credenciais e IPs reais). Veja scripts/import_sessions_data.example.json
para o formato esperado.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssh_remote.session_manager import Session, SessionManager

DATA_FILE = Path(__file__).resolve().parent / "import_sessions_data.json"


def load_data() -> dict:
    if not DATA_FILE.exists():
        sys.exit(
            f"Arquivo não encontrado: {DATA_FILE}\n"
            "Copie scripts/import_sessions_data.example.json para "
            f"{DATA_FILE.name} e preencha com usuário/senha/entradas reais."
        )
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def main() -> None:
    data = load_data()
    username = data["username"]
    password = data["password"]
    port = data.get("port", 22)
    entries = [tuple(entry) for entry in data["entries"]]

    mgr = SessionManager()
    existing_by_key = {(s.host, s.username): s for s in mgr.sessions}
    existing_names = {s.name for s in mgr.sessions}

    added, skipped = 0, 0
    for name, host in entries:
        if (host, username) in existing_by_key:
            skipped += 1
            continue
        session_name = name
        suffix = 2
        while session_name in existing_names:
            session_name = f"{name} ({suffix})"
            suffix += 1
        existing_names.add(session_name)

        session = Session(
            name=session_name,
            host=host,
            port=port,
            username=username,
            auth_method="password",
        )
        session.password = password
        mgr.sessions.append(session)
        existing_by_key[(host, username)] = session
        added += 1

    mgr.save()
    print(f"Adicionadas: {added}  |  já existiam (host+usuário iguais): {skipped}  |  total no arquivo: {len(mgr.sessions)}")


if __name__ == "__main__":
    main()
