"""Diálogos simples (info/confirmação/prompt de texto) baseados em ttk.Toplevel puro.

Não usamos ttkbootstrap.dialogs (Messagebox/Querybox) porque, neste ambiente
de janela (KDE/KWin), aqueles diálogos abrem sem conteúdo — usam a dica de
janela X11 "windowtype=dialog" e um ciclo iconify/withdraw/deiconify que o
KWin aqui não respeita, deixando só a barra de título visível. ttk.Toplevel
puro (o mesmo padrão usado em SessionDialog) renderiza normalmente.
"""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk


class _BaseDialog(ttk.Toplevel):
    def __init__(self, master, title: str):
        super().__init__(title=title, resizable=(False, False), transient=master)
        self.grab_set()
        self.result = None
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_cancel(self) -> None:
        self.destroy()


class _InfoDialog(_BaseDialog):
    def __init__(self, master, message: str, title: str, bootstyle: str):
        super().__init__(master, title)
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=message, wraplength=320, justify="left").pack(pady=(0, 16))
        btn = ttk.Button(frm, text="OK", command=self.destroy, bootstyle=bootstyle)
        btn.pack()
        btn.focus_set()
        self.bind("<Return>", lambda _e: self.destroy())


class _ConfirmDialog(_BaseDialog):
    def __init__(self, master, message: str, title: str):
        super().__init__(master, title)
        self.result = False
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=message, wraplength=320, justify="left").pack(pady=(0, 16))
        btns = ttk.Frame(frm)
        btns.pack()
        ttk.Button(btns, text="Não", command=self._on_no, bootstyle="secondary").pack(side="left", padx=4)
        yes_btn = ttk.Button(btns, text="Sim", command=self._on_yes, bootstyle="danger")
        yes_btn.pack(side="left", padx=4)
        yes_btn.focus_set()
        self.bind("<Return>", lambda _e: self._on_yes())
        self.bind("<Escape>", lambda _e: self._on_no())

    def _on_yes(self) -> None:
        self.result = True
        self.destroy()

    def _on_no(self) -> None:
        self.result = False
        self.destroy()


class _PromptDialog(_BaseDialog):
    def __init__(self, master, message: str, title: str, initialvalue: str):
        super().__init__(master, title)
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=message).pack(anchor="w", pady=(0, 8))

        self.var_value = tk.StringVar(value=initialvalue)
        entry = ttk.Entry(frm, textvariable=self.var_value, width=32)
        entry.pack(fill="x", pady=(0, 16))
        entry.focus_set()
        entry.select_range(0, "end")

        btns = ttk.Frame(frm)
        btns.pack(anchor="e")
        ttk.Button(btns, text="Cancelar", command=self._on_cancel, bootstyle="secondary").pack(side="left", padx=4)
        ttk.Button(btns, text="Salvar", command=self._on_save, bootstyle="success").pack(side="left", padx=4)

        entry.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self._on_cancel())

    def _on_save(self) -> None:
        self.result = self.var_value.get()
        self.destroy()


def show_info(master, message: str, title: str = " ") -> None:
    dlg = _InfoDialog(master, message, title, bootstyle="secondary")
    master.wait_window(dlg)


def show_warning(master, message: str, title: str = " ") -> None:
    dlg = _InfoDialog(master, message, title, bootstyle="warning")
    master.wait_window(dlg)


def show_error(master, message: str, title: str = " ") -> None:
    dlg = _InfoDialog(master, message, title, bootstyle="danger")
    master.wait_window(dlg)


def ask_yesno(master, message: str, title: str = "Confirmar") -> bool:
    dlg = _ConfirmDialog(master, message, title)
    master.wait_window(dlg)
    return bool(dlg.result)


def ask_string(master, message: str, title: str = " ", initialvalue: str = "") -> str | None:
    dlg = _PromptDialog(master, message, title, initialvalue)
    master.wait_window(dlg)
    return dlg.result
