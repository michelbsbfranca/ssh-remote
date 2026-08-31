"""Widget de terminal SSH: conecta via paramiko e mostra a sessão interativa."""
from __future__ import annotations

import re
import threading
import tkinter as tk
from tkinter import ttk

import paramiko

from . import dialogs
from .session_manager import Session

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=>]")

# Alguns dispositivos (ex.: switches HP/H3C Comware) não ecoam BS/DEL puro
# para apagar — em vez disso mandam "mover cursor p/ esquerda N, N espaços,
# mover cursor p/ esquerda N de novo" (ex.: "\x1b[1D \x1b[1D") para desenhar
# o apagamento. Isso precisa virar N backspaces *antes* do ANSI_ESCAPE_RE
# rodar, senão os códigos de cursor são descartados e sobra só o espaço solto
# na tela.
CURSOR_BACK_ERASE_RE = re.compile(r"\x1b\[\d+D( +)\x1b\[\d+D")

# Cores fixas do terminal — não seguem o tema claro/escuro da interface,
# igual a um emulador de terminal de verdade (ttkbootstrap reaplica as cores
# do tema em widgets tk.Text ao trocar de tema, por isso precisam ser
# reforçadas via reapply_colors() sempre que o tema mudar).
TERMINAL_BG = "black"
TERMINAL_FG = "#d0d0d0"
TERMINAL_CURSOR = "white"

# Teclas especiais -> sequência enviada ao servidor
SPECIAL_KEYS = {
    "Return": "\r",
    # Alguns servidores só reconhecem BS (\x08, o mesmo byte que Ctrl+H
    # produz) para apagar, em vez do DEL (\x7f) padrão — mapear a tecla
    # Backspace para \x08 evita que o usuário precise usar Ctrl+H manualmente.
    "BackSpace": "\x08",
    "Tab": "\t",
    "Escape": "\x1b",
    "Up": "\x1b[A",
    "Down": "\x1b[B",
    "Right": "\x1b[C",
    "Left": "\x1b[D",
    "Home": "\x1b[H",
    "End": "\x1b[F",
    "Delete": "\x1b[3~",
}


class SSHTerminalFrame(ttk.Frame):
    def __init__(self, master, session: Session, on_close=None):
        super().__init__(master)
        self.session = session
        self.on_close = on_close
        self.client: paramiko.SSHClient | None = None
        self.channel: paramiko.Channel | None = None
        self._stop = threading.Event()

        self.text = tk.Text(
            self,
            font=("Consolas", 11) if self._font_exists("Consolas") else ("Courier New", 11),
            wrap="char",
            undo=False,
        )
        self.text.pack(fill="both", expand=True)
        self.reapply_colors()
        self.text.bind("<Key>", self._on_key)
        self.text.bind("<Control-c>", self._on_ctrl_c)
        self.text.bind("<<Paste>>", self._on_paste)

        self._append(f"Conectando em {session.username}@{session.host}:{session.port} ...\n")
        threading.Thread(target=self._connect_and_read, daemon=True).start()

    def reapply_colors(self) -> None:
        """Força as cores fixas do terminal, sobrescrevendo o que o
        ttkbootstrap possa ter reaplicado numa troca de tema."""
        self.text.configure(bg=TERMINAL_BG, fg=TERMINAL_FG, insertbackground=TERMINAL_CURSOR)

    @staticmethod
    def _font_exists(name: str) -> bool:
        try:
            import tkinter.font as tkfont

            return name in tkfont.families()
        except Exception:
            return False

    # ---------- conexão ----------
    def _connect_and_read(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            connect_kwargs = dict(
                hostname=self.session.host,
                port=self.session.port,
                username=self.session.username,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            if self.session.auth_method == "key" and self.session.key_path:
                pkey = self._load_private_key()
                connect_kwargs["pkey"] = pkey
            else:
                connect_kwargs["password"] = self.session.password

            client.connect(**connect_kwargs)
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            self._append(f"\nFalha na conexão: {error_msg}\n")
            self.after(
                0,
                lambda msg=error_msg: dialogs.show_error(self.winfo_toplevel(), msg, "Erro de conexão"),
            )
            self._cleanup()
            return

        self.client = client
        self.channel = client.invoke_shell(term="xterm", width=100, height=32)
        self._append("Conectado.\n\n")

        try:
            while not self._stop.is_set():
                data = self.channel.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="ignore")
                text = CURSOR_BACK_ERASE_RE.sub(lambda m: "\x08" * len(m.group(1)), text)
                text = ANSI_ESCAPE_RE.sub("", text)
                self._append(text)
        except (OSError, EOFError):
            pass
        finally:
            self._append("\n[Conexão encerrada]\n")
            self._cleanup()

    def _load_private_key(self):
        path = self.session.key_path
        passphrase = self.session.key_passphrase or None
        last_err = None
        for loader in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                return loader.from_private_key_file(path, password=passphrase)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
        raise last_err or RuntimeError("Não foi possível carregar a chave privada")

    # ---------- entrada do usuário ----------
    def _send(self, data: str) -> None:
        if self.channel and not self.channel.closed:
            try:
                self.channel.send(data)
            except OSError:
                pass

    def _on_key(self, event: tk.Event) -> str:
        if event.keysym in SPECIAL_KEYS:
            self._send(SPECIAL_KEYS[event.keysym])
            return "break"
        if event.char and event.char.isprintable():
            self._send(event.char)
            return "break"
        if event.char in ("\r", "\n"):
            self._send("\r")
            return "break"
        return "break"

    def _on_ctrl_c(self, _event: tk.Event) -> str:
        self._send("\x03")
        return "break"

    def _on_paste(self, _event: tk.Event) -> str:
        try:
            clip = self.clipboard_get()
            self._send(clip)
        except tk.TclError:
            pass
        return "break"

    # ---------- saída ----------
    def _append(self, text: str) -> None:
        def do_append():
            # BS (\x08) e DEL (\x7f) chegam como texto puro depois do strip de
            # ANSI, ecoados pelo servidor para apagar o caractere anterior (ex.:
            # a sequência clássica "\b \b"). Inserir esse byte de controle
            # literalmente no Text mostra um glifo/caixa em vez de apagar, então
            # tratamos como "apagar o último caractere exibido".
            for ch in text:
                if ch in ("\x08", "\x7f"):
                    self.text.delete("end-2c", "end-1c")
                elif ch in ("\r", "\x07"):
                    # \r puro (parte de "\r\n") e BEL (\x07, beep de alguns
                    # dispositivos ao apagar além do início da linha) também
                    # apareciam como glifo literal — nenhum dos dois deve ser
                    # exibido.
                    continue
                else:
                    self.text.insert("end", ch)
            self.text.see("end")

        self.after(0, do_append)

    def close(self) -> None:
        self._stop.set()
        self._cleanup()

    def _cleanup(self) -> None:
        try:
            if self.channel:
                self.channel.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:  # noqa: BLE001
            pass
        if self.on_close:
            self.after(0, self.on_close)
