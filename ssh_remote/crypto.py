"""Criptografia local para as credenciais salvas (senhas / passphrases)."""
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet

CONFIG_DIR = Path.home() / ".ssh_remote"
KEY_FILE = CONFIG_DIR / "secret.key"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, stat.S_IRWXU)  # 700, só o dono acessa
    except OSError:
        pass


def _load_or_create_key() -> bytes:
    _ensure_config_dir()
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()

    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    try:
        os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    if not token:
        return ""
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
