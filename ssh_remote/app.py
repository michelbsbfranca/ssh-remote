"""Aplicação principal: SSH Remote - gerenciador de sessões com terminal em abas."""
from __future__ import annotations

import copy
import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk

from . import dialogs, preferences
from .category_manager import Category, CategoryManager
from .session_manager import Session, SessionManager
from .terminal import SSHTerminalFrame

THEME_DARK = "darkly"
THEME_LIGHT = "flatly"

NONE_CATEGORY_IID = "cat:none"


def _cat_iid(category_id: str) -> str:
    return f"cat:{category_id}" if category_id else NONE_CATEGORY_IID


def _sess_iid(session_id: str) -> str:
    return f"sess:{session_id}"


class SessionDialog(ttk.Toplevel):
    """Formulário de criação/edição de sessão."""

    def __init__(self, master, category_manager: CategoryManager, session: Session | None = None):
        super().__init__(
            title="Editar sessão" if session else "Nova sessão",
            resizable=(False, False),
            transient=master,
        )
        self.grab_set()

        self.result: Session | None = None
        self._session = session or Session(port=22, auth_method="password")
        self._category_manager = category_manager
        self._categories = category_manager.list_sorted()
        self._category_names = ["(sem categoria)"] + [c.name for c in self._categories]

        current_cat = next((c for c in self._categories if c.id == self._session.category_id), None)

        self.var_name = tk.StringVar(value=self._session.name)
        self.var_host = tk.StringVar(value=self._session.host)
        self.var_port = tk.StringVar(value=str(self._session.port or 22))
        self.var_user = tk.StringVar(value=self._session.username)
        self.var_category = tk.StringVar(value=current_cat.name if current_cat else "(sem categoria)")
        self.var_auth = tk.StringVar(value=self._session.auth_method or "password")
        self.var_password = tk.StringVar(value=self._session.password if session else "")
        self.var_keypath = tk.StringVar(value=self._session.key_path)
        self.var_keypass = tk.StringVar(value=self._session.key_passphrase if session else "")

        self._build_form()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_form(self) -> None:
        pad = dict(padx=10, pady=6, sticky="w")
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        row = 0
        ttk.Label(frm, text="Nome da sessão").grid(row=row, column=0, **pad)
        ttk.Entry(frm, textvariable=self.var_name, width=34).grid(row=row, column=1, **pad)

        row += 1
        ttk.Label(frm, text="Host").grid(row=row, column=0, **pad)
        ttk.Entry(frm, textvariable=self.var_host, width=34).grid(row=row, column=1, **pad)

        row += 1
        ttk.Label(frm, text="Porta").grid(row=row, column=0, **pad)
        ttk.Entry(frm, textvariable=self.var_port, width=10).grid(row=row, column=1, **pad)

        row += 1
        ttk.Label(frm, text="Usuário").grid(row=row, column=0, **pad)
        ttk.Entry(frm, textvariable=self.var_user, width=34).grid(row=row, column=1, **pad)

        row += 1
        ttk.Label(frm, text="Categoria").grid(row=row, column=0, **pad)
        ttk.Combobox(
            frm, textvariable=self.var_category, values=self._category_names, state="readonly", width=32,
        ).grid(row=row, column=1, **pad)

        row += 1
        ttk.Label(frm, text="Autenticação").grid(row=row, column=0, **pad)
        auth_frame = ttk.Frame(frm)
        auth_frame.grid(row=row, column=1, **pad)
        ttk.Radiobutton(
            auth_frame, text="Senha", variable=self.var_auth, value="password",
            command=self._toggle_auth, bootstyle="round-toggle",
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            auth_frame, text="Chave privada", variable=self.var_auth, value="key",
            command=self._toggle_auth, bootstyle="round-toggle",
        ).pack(side="left")

        row += 1
        self.lbl_password = ttk.Label(frm, text="Senha")
        self.lbl_password.grid(row=row, column=0, **pad)
        self.entry_password = ttk.Entry(frm, textvariable=self.var_password, show="•", width=34)
        self.entry_password.grid(row=row, column=1, **pad)

        row += 1
        self.lbl_keypath = ttk.Label(frm, text="Arquivo da chave")
        self.lbl_keypath.grid(row=row, column=0, **pad)
        key_frame = ttk.Frame(frm)
        key_frame.grid(row=row, column=1, **pad)
        self.entry_keypath = ttk.Entry(key_frame, textvariable=self.var_keypath, width=26)
        self.entry_keypath.pack(side="left")
        ttk.Button(
            key_frame, text="...", width=3, command=self._browse_key, bootstyle="secondary-outline",
        ).pack(side="left", padx=(4, 0))

        row += 1
        self.lbl_keypass = ttk.Label(frm, text="Passphrase da chave")
        self.lbl_keypass.grid(row=row, column=0, **pad)
        self.entry_keypass = ttk.Entry(frm, textvariable=self.var_keypass, show="•", width=34)
        self.entry_keypass.grid(row=row, column=1, **pad)

        row += 1
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttk.Button(btns, text="Cancelar", command=self.destroy, bootstyle="secondary").pack(side="left", padx=4)
        ttk.Button(btns, text="Salvar", command=self._on_save, bootstyle="success").pack(side="left", padx=4)

        self._toggle_auth()

    def _toggle_auth(self) -> None:
        is_key = self.var_auth.get() == "key"
        state_pw = "disabled" if is_key else "normal"
        state_key = "normal" if is_key else "disabled"
        self.entry_password.configure(state=state_pw)
        self.entry_keypath.configure(state=state_key)
        self.entry_keypass.configure(state=state_key)

    def _browse_key(self) -> None:
        path = filedialog.askopenfilename(title="Selecione a chave privada")
        if path:
            self.var_keypath.set(path)

    def _on_save(self) -> None:
        name = self.var_name.get().strip()
        host = self.var_host.get().strip()
        user = self.var_user.get().strip()

        if not name or not host or not user:
            dialogs.show_warning(self, "Preencha nome, host e usuário.", "Campos obrigatórios")
            return
        try:
            port = int(self.var_port.get().strip() or "22")
        except ValueError:
            dialogs.show_warning(self, "Informe uma porta numérica.", "Porta inválida")
            return

        auth_method = self.var_auth.get()
        if auth_method == "password" and not self.var_password.get():
            if not dialogs.ask_yesno(
                self, "Nenhuma senha foi informada. Continuar mesmo assim?", "Senha vazia",
            ):
                return
        if auth_method == "key" and not self.var_keypath.get():
            dialogs.show_warning(self, "Selecione o arquivo da chave privada.", "Chave obrigatória")
            return

        chosen_cat_name = self.var_category.get()
        chosen_cat = next((c for c in self._categories if c.name == chosen_cat_name), None)

        session = self._session
        session.name = name
        session.host = host
        session.port = port
        session.username = user
        session.category_id = chosen_cat.id if chosen_cat else ""
        session.auth_method = auth_method
        session.password = self.var_password.get()
        session.key_path = self.var_keypath.get()
        session.key_passphrase = self.var_keypass.get()

        self.result = session
        self.destroy()


class MainWindow(ttk.Window):
    def __init__(self):
        self._prefs = preferences.load()
        self._dark_mode = bool(self._prefs.get("dark_mode", True))

        super().__init__(
            title="SSH Remote",
            themename=THEME_DARK if self._dark_mode else THEME_LIGHT,
            size=(1150, 680),
            minsize=(760, 420),
        )
        self.manager = SessionManager()
        self.category_manager = CategoryManager()

        # tab_id (str) -> SSHTerminalFrame
        self._open_terminals: dict[str, SSHTerminalFrame] = {}

        self._build_ui()
        self._refresh_tree()
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

    # ---------- construção da UI ----------
    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(16, 12), bootstyle="dark")
        header.pack(fill="x", side="top")
        ttk.Label(
            header, text="SSH Remote", font=("Segoe UI", 14, "bold"), bootstyle="inverse-dark",
        ).pack(side="left")

        self.var_dark_mode = tk.BooleanVar(value=self._dark_mode)
        ttk.Checkbutton(
            header,
            text="Modo escuro",
            variable=self.var_dark_mode,
            command=self._on_toggle_theme,
            bootstyle="round-toggle",
        ).pack(side="right")

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        # ----- coluna esquerda: sessões e categorias -----
        left = ttk.Frame(paned, padding=(4, 0, 8, 0))
        paned.add(left, weight=0)

        ttk.Label(left, text="SESSÕES", font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(
            anchor="w", pady=(0, 6)
        )

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_frame, show="tree", selectmode="extended", bootstyle="dark",
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview, bootstyle="round")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._configure_tree_tags()
        self._reset_drag_state()

        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)
        # Assumimos o controle total do clique (sem add="+") para poder
        # preservar uma seleção múltipla ao arrastar: o binding padrão do
        # ttk.Treeview colapsa a seleção para um único item já no
        # ButtonPress, o que impediria arrastar vários itens selecionados
        # com Ctrl/Shift de uma vez.
        self.tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_release)
        self.tree.bind("<Button-3>", self._on_right_click)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Nova sessão", command=self._new_session, bootstyle="secondary-outline").grid(
            row=0, column=0, sticky="ew", padx=2, pady=2
        )
        ttk.Button(btns, text="Editar", command=self._edit_session, bootstyle="secondary-outline").grid(
            row=0, column=1, sticky="ew", padx=2, pady=2
        )
        ttk.Button(btns, text="Duplicar", command=self._duplicate_session, bootstyle="secondary-outline").grid(
            row=1, column=0, sticky="ew", padx=2, pady=2
        )
        ttk.Button(btns, text="Excluir", command=self._delete_session, bootstyle="danger-outline").grid(
            row=1, column=1, sticky="ew", padx=2, pady=2
        )
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        ttk.Button(
            left, text="📁 Nova categoria", command=self._new_category, bootstyle="info-outline",
        ).pack(fill="x", pady=(6, 0))

        ttk.Button(
            left, text="Conectar  ▶", command=self._connect_selected, bootstyle="success",
        ).pack(fill="x", pady=(10, 0), ipady=4)

        left.configure(width=280)
        left.pack_propagate(False)

        # ----- área central: abas de terminal -----
        center = ttk.Frame(paned, padding=(8, 0, 0, 0))
        paned.add(center, weight=1)

        top_bar = ttk.Frame(center)
        top_bar.pack(fill="x", pady=(0, 6))
        ttk.Button(
            top_bar, text="✕ Fechar aba", command=self._close_current_tab, bootstyle="danger-link",
        ).pack(side="right")

        self.notebook = ttk.Notebook(center, bootstyle="dark")
        self.notebook.pack(fill="both", expand=True)

        self._placeholder = ttk.Label(
            center,
            text=(
                "Nenhuma sessão aberta\n\n"
                "Selecione uma sessão na coluna à esquerda e clique em \"Conectar\"\n\n"
                "Dica: arraste sessões para dentro de uma categoria para organizá-las"
            ),
            anchor="center",
            justify="center",
            font=("Segoe UI", 11),
            bootstyle="secondary",
        )
        self._show_placeholder()

        self.bind("<Control-w>", lambda _e: self._close_current_tab())

    def _configure_tree_tags(self) -> None:
        colors = self.style.colors
        self.tree.tag_configure("category", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("drop_target", background=colors.primary, foreground=colors.selectfg)

    def _on_toggle_theme(self) -> None:
        self._dark_mode = self.var_dark_mode.get()
        self.style.theme_use(THEME_DARK if self._dark_mode else THEME_LIGHT)
        self._configure_tree_tags()
        for terminal in self._open_terminals.values():
            terminal.reapply_colors()
        self._prefs["dark_mode"] = self._dark_mode
        preferences.save(self._prefs)

    def _show_placeholder(self) -> None:
        if not self.notebook.tabs():
            self.notebook.pack_forget()
            self._placeholder.pack(fill="both", expand=True)

    def _hide_placeholder(self) -> None:
        self._placeholder.pack_forget()
        self.notebook.pack(fill="both", expand=True)

    # ---------- árvore de sessões/categorias ----------
    def _refresh_tree(self) -> None:
        selected = self.tree.selection()
        selected_iid = selected[0] if selected else None
        open_states = {iid: self.tree.item(iid, "open") for iid in self.tree.get_children("")}

        self.tree.delete(*self.tree.get_children(""))

        categories = self.category_manager.list_sorted()
        for cat in categories:
            iid = _cat_iid(cat.id)
            self.tree.insert(
                "", "end", iid=iid, text=f"📁  {cat.name}",
                open=open_states.get(iid, True), tags=("category",),
            )
        self.tree.insert(
            "", "end", iid=NONE_CATEGORY_IID, text="📁  Sem categoria",
            open=open_states.get(NONE_CATEGORY_IID, True), tags=("category",),
        )

        valid_cat_ids = {c.id for c in categories}
        for s in self.manager.list_sorted():
            parent = _cat_iid(s.category_id) if s.category_id in valid_cat_ids else NONE_CATEGORY_IID
            self.tree.insert(parent, "end", iid=_sess_iid(s.id), text=s.name, tags=("session",))

        if selected_iid and self.tree.exists(selected_iid):
            self.tree.selection_set(selected_iid)

    def _selected_session(self) -> Session | None:
        sel = self.tree.selection()
        if not sel or not sel[0].startswith("sess:"):
            return None
        return self.manager.get(sel[0].split(":", 1)[1])

    def _on_tree_double_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if item.startswith("sess:"):
            self._connect_selected()
        elif item.startswith("cat:"):
            self.tree.item(item, open=not self.tree.item(item, "open"))

    # ---------- CRUD de sessões ----------
    def _new_session(self) -> None:
        dialog = SessionDialog(self, self.category_manager)
        self.wait_window(dialog)
        if dialog.result:
            self.manager.add(dialog.result)
            self._refresh_tree()

    def _edit_session(self) -> None:
        session = self._selected_session()
        if not session:
            dialogs.show_info(self, "Selecione uma sessão para editar.", "Selecione")
            return
        dialog = SessionDialog(self, self.category_manager, session)
        self.wait_window(dialog)
        if dialog.result:
            self.manager.update(dialog.result)
            self._refresh_tree()

    def _duplicate_session(self) -> None:
        session = self._selected_session()
        if not session:
            dialogs.show_info(self, "Selecione uma sessão para duplicar.", "Selecione")
            return
        clone = copy.copy(session)
        clone.id = Session().id
        clone.name = f"{session.name} (cópia)"
        self.manager.add(clone)
        self._refresh_tree()

    def _delete_session(self) -> None:
        session = self._selected_session()
        if not session:
            dialogs.show_info(self, "Selecione uma sessão para excluir.", "Selecione")
            return
        if dialogs.ask_yesno(self, f"Excluir a sessão '{session.name}'?", "Confirmar"):
            self.manager.delete(session.id)
            self._refresh_tree()

    def _move_session_to_category(self, session_id: str, category_id: str) -> None:
        self._move_sessions_to_category([session_id], category_id)

    def _move_sessions_to_category(self, session_ids: list[str], category_id: str) -> None:
        changed = False
        for session_id in session_ids:
            session = self.manager.get(session_id)
            if session and session.category_id != category_id:
                session.category_id = category_id
                changed = True
        if changed:
            self.manager.save()
        self._refresh_tree()

        iids = [_sess_iid(sid) for sid in session_ids if self.tree.exists(_sess_iid(sid))]
        if iids:
            self.tree.selection_set(iids)
            self.tree.see(iids[0])

    # ---------- CRUD de categorias ----------
    def _new_category(self) -> None:
        name = dialogs.ask_string(self, "Nome da categoria:", "Nova categoria")
        if not name or not name.strip():
            return
        self.category_manager.add(Category(name=name.strip()))
        self._refresh_tree()

    def _rename_category(self, category_id: str) -> None:
        cat = self.category_manager.get(category_id)
        if not cat:
            return
        name = dialogs.ask_string(self, "Novo nome da categoria:", "Renomear categoria", initialvalue=cat.name)
        if not name or not name.strip():
            return
        self.category_manager.rename(category_id, name.strip())
        self._refresh_tree()

    def _delete_category(self, category_id: str) -> None:
        cat = self.category_manager.get(category_id)
        if not cat:
            return
        if not dialogs.ask_yesno(
            self,
            f"Excluir a categoria '{cat.name}'? As sessões dentro dela vão para \"Sem categoria\".",
            "Confirmar",
        ):
            return
        for s in self.manager.sessions:
            if s.category_id == category_id:
                s.category_id = ""
        self.manager.save()
        self.category_manager.delete(category_id)
        self._refresh_tree()

    # ---------- menu de contexto ----------
    def _on_right_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)

        menu = tk.Menu(self, tearoff=False)
        if item.startswith("sess:"):
            session_id = item.split(":", 1)[1]
            menu.add_command(label="Conectar", command=self._connect_selected)
            menu.add_command(label="Editar", command=self._edit_session)
            menu.add_command(label="Duplicar", command=self._duplicate_session)
            menu.add_separator()

            move_menu = tk.Menu(menu, tearoff=False)
            move_menu.add_command(
                label="Sem categoria", command=lambda: self._move_session_to_category(session_id, "")
            )
            for cat in self.category_manager.list_sorted():
                move_menu.add_command(
                    label=cat.name,
                    command=lambda cid=cat.id: self._move_session_to_category(session_id, cid),
                )
            menu.add_cascade(label="Mover para", menu=move_menu)
            menu.add_separator()
            menu.add_command(label="Excluir", command=self._delete_session)
        elif item.startswith("cat:"):
            cat_id = item.split(":", 1)[1]
            if cat_id != "none":
                menu.add_command(label="Renomear categoria", command=lambda: self._rename_category(cat_id))
                menu.add_command(label="Excluir categoria", command=lambda: self._delete_category(cat_id))
                menu.add_separator()
            menu.add_command(label="Nova categoria", command=self._new_category)

        menu.tk_popup(event.x_root, event.y_root)

    # ---------- seleção múltipla + arrastar-e-soltar (sessões -> categoria) ----------
    def _reset_drag_state(self) -> None:
        self._drag_candidates: list[str] = []
        self._drag_target: str | None = None
        self._drag_moved = False
        self._drag_collapse_to: str | None = None
        self._press_xy = (0, 0)

    def _flatten_visible_items(self) -> list[str]:
        result: list[str] = []

        def walk(parent: str) -> None:
            for child in self.tree.get_children(parent):
                result.append(child)
                if self.tree.item(child, "open"):
                    walk(child)

        walk("")
        return result

    def _select_range(self, anchor: str, target: str) -> None:
        flat = self._flatten_visible_items()
        if anchor not in flat or target not in flat:
            self.tree.selection_set(target)
            self.tree.focus(target)
            return
        i1, i2 = flat.index(anchor), flat.index(target)
        lo, hi = sorted((i1, i2))
        self.tree.selection_set(flat[lo : hi + 1])
        self.tree.focus(target)

    def _on_drag_start(self, event) -> str | None:
        # Clique na setinha de expandir/recolher: deixa o Treeview cuidar
        # disso nativamente (não assumimos seleção/arraste nesse caso).
        if self.tree.identify_element(event.x, event.y) == "Treeitem.indicator":
            self._reset_drag_state()
            return None

        # Nos demais casos assumimos manualmente a seleção (Ctrl/Shift/clique
        # simples) porque o binding padrão do Treeview colapsa a seleção
        # para um único item já no ButtonPress, o que impediria arrastar
        # vários itens de uma vez.
        item = self.tree.identify_row(event.y)
        self._reset_drag_state()
        self._press_xy = (event.x, event.y)

        if not item:
            self.tree.selection_set(())
            return "break"

        current_selection = set(self.tree.selection())
        ctrl = bool(event.state & 0x0004)
        shift = bool(event.state & 0x0001)

        if ctrl:
            if item in current_selection:
                self.tree.selection_remove(item)
            else:
                self.tree.selection_add(item)
            self.tree.focus(item)
        elif shift:
            anchor = self.tree.focus() or item
            self._select_range(anchor, item)
        elif item in current_selection and len(current_selection) > 1:
            # clique simples num item que já faz parte de uma seleção múltipla:
            # mantém a seleção toda (permite arrastar o grupo); se soltar sem
            # mover o mouse, colapsa para só este item (clique "normal").
            self._drag_candidates = [i for i in self.tree.selection() if i.startswith("sess:")]
            self._drag_collapse_to = item
        else:
            self.tree.selection_set(item)
            self.tree.focus(item)
            self._drag_candidates = [item] if item.startswith("sess:") else []

        return "break"

    def _on_drag_motion(self, event) -> None:
        if not self._drag_candidates:
            return
        if abs(event.x - self._press_xy[0]) > 3 or abs(event.y - self._press_xy[1]) > 3:
            self._drag_moved = True
        if not self._drag_moved:
            return

        target = self.tree.identify_row(event.y)
        if target == self._drag_target:
            return
        if self._drag_target:
            self._set_drop_tag(self._drag_target, False)
        if target and target not in self._drag_candidates:
            self._set_drop_tag(target, True)
            self._drag_target = target
        else:
            self._drag_target = None
        self.tree.configure(cursor="hand2")

    def _set_drop_tag(self, iid: str, on: bool) -> None:
        if not self.tree.exists(iid):
            return
        base_tags = [t for t in self.tree.item(iid, "tags") if t != "drop_target"]
        self.tree.item(iid, tags=base_tags + ["drop_target"] if on else base_tags)

    def _on_drag_release(self, event) -> None:
        candidates, target, moved = self._drag_candidates, self._drag_target, self._drag_moved
        collapse_to = self._drag_collapse_to
        if target:
            self._set_drop_tag(target, False)
        self.tree.configure(cursor="")
        self._reset_drag_state()

        if not moved:
            # foi só um clique, sem arrastar de verdade
            if collapse_to:
                self.tree.selection_set(collapse_to)
                self.tree.focus(collapse_to)
            return

        if not candidates or not target or target in candidates:
            return

        if target.startswith("cat:"):
            new_category_id = "" if target == NONE_CATEGORY_IID else target.split(":", 1)[1]
        elif target.startswith("sess:"):
            target_session = self.manager.get(target.split(":", 1)[1])
            new_category_id = target_session.category_id if target_session else ""
        else:
            return

        session_ids = [c.split(":", 1)[1] for c in candidates]
        self._move_sessions_to_category(session_ids, new_category_id)

    # ---------- abas de terminal ----------
    def _connect_selected(self) -> None:
        session = self._selected_session()
        if not session:
            dialogs.show_info(self, "Selecione uma sessão para conectar.", "Selecione")
            return

        self._hide_placeholder()

        tab_frame = ttk.Frame(self.notebook)
        terminal = SSHTerminalFrame(
            tab_frame,
            session,
            on_close=lambda tf=tab_frame: self._on_terminal_closed(tf),
        )
        terminal.pack(fill="both", expand=True)

        self.notebook.add(tab_frame, text=session.name)
        self.notebook.select(tab_frame)

        tab_id = str(tab_frame)
        self._open_terminals[tab_id] = terminal

        tab_frame.bind("<Destroy>", lambda _e, tf=tab_frame: self._forget_tab(tf), add="+")

    def _current_tab_frame(self):
        tabs = self.notebook.tabs()
        if not tabs:
            return None
        return self.notebook.select() or None

    def _close_current_tab(self) -> None:
        current = self._current_tab_frame()
        if not current:
            return
        terminal = self._open_terminals.get(current)
        if terminal:
            terminal.close()
        self.notebook.forget(current)
        self.nametowidget(current).destroy()

    def _on_terminal_closed(self, tab_frame) -> None:
        # A conexão caiu sozinha; deixamos a aba aberta mostrando o log final
        # (o usuário fecha manualmente com "Fechar aba").
        pass

    def _forget_tab(self, tab_frame) -> None:
        tab_id = str(tab_frame)
        self._open_terminals.pop(tab_id, None)
        if not self.notebook.tabs():
            self._show_placeholder()

    def _on_app_close(self) -> None:
        for terminal in list(self._open_terminals.values()):
            terminal.close()
        self.destroy()


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
