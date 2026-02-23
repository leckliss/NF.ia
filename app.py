import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from modules.database import init_db, save_invoice, get_all_invoices, update_invoice
from modules.ocr_engine import OCREngine
from modules.ai_processor import extract_invoice_data

# --- Tema Global ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

init_db()
ocr_engine = OCREngine()

# Colunas visíveis na tabela → chave no dict do banco
COLS = [
    ("Arquivo",          "nome_arquivo"),
    ("CNPJ",             "cnpj"),
    ("Data Emissão",     "emissao"),
    ("Chave de Acesso",  "chave_acesso"),
    ("Descrição",        "descricao_operacao"),
    ("Vlr Produtos",     "valor_produtos"),
    ("Vlr Total",        "valor_total"),
    ("Pagamento",        "forma_pagamento"),
]
COL_LABELS  = [c[0] for c in COLS]
COL_KEYS    = [c[1] for c in COLS]
COL_WIDTHS  = [200, 130, 90, 160, 180, 90, 90, 100]


# ================================================================== #
#  MODAL DE EDIÇÃO                                                   #
# ================================================================== #
class EditInvoiceDialog(ctk.CTkToplevel):
    """Janela modal para corrigir os dados extraídos de uma nota fiscal."""

    FIELDS = [
        ("CNPJ",                 "cnpj"),
        ("Data de Emissão",      "emissao"),
        ("Chave de Acesso",      "chave_acesso"),
        ("Descrição da Operação","descricao_operacao"),
        ("Valor Produtos (R$)",  "valor_produtos"),
        ("Valor Total (R$)",     "valor_total"),
        ("Forma de Pagamento",   "forma_pagamento"),
        ("Status",               "status_validacao"),
    ]

    def __init__(self, parent, row_data: dict, on_save_callback):
        super().__init__(parent)
        self.title("✏️  Editar Nota Fiscal")
        self.geometry("460x460")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()

        self._on_save = on_save_callback
        self._invoice_id = int(row_data.get("id", 0))
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkComboBox] = {}

        self._build(row_data)

    def _build(self, d: dict):
        ctk.CTkLabel(self, text=f"Arquivo: {d.get('nome_arquivo', '')}",
                     font=ctk.CTkFont(size=11), text_color="gray60"
                     ).pack(anchor="w", padx=20, pady=(16, 8))

        scroll = ctk.CTkScrollableFrame(self, height=320)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        for label, key in self.FIELDS:
            ctk.CTkLabel(scroll, text=label, anchor="w",
                         font=ctk.CTkFont(size=11)).pack(fill="x", padx=4, pady=(6, 0))

            if key == "status_validacao":
                widget = ctk.CTkComboBox(scroll, values=["OK", "ERRO", "ERRO_JSON"], state="readonly")
                widget.set(d.get(key) or "OK")
            else:
                widget = ctk.CTkEntry(scroll)
                val = d.get(key)
                widget.insert(0, str(val) if val is not None else "")

            widget.pack(fill="x", padx=4, pady=(2, 0))
            self._entries[key] = widget

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(4, 16))
        ctk.CTkButton(btn_frame, text="💾  Salvar", command=self._save,
                      fg_color="#1f6aa5", hover_color="#144f7d").pack(side="left", expand=True, padx=(0, 6))
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy,
                      fg_color="transparent", border_width=1).pack(side="left", expand=True)

    def _save(self):
        data = {}
        for label, key in self.FIELDS:
            widget = self._entries[key]
            val = widget.get().strip() if hasattr(widget, "get") else ""
            if key in ("valor_total", "valor_produtos"):
                try:
                    data[key] = float(val.replace(",", ".")) if val else None
                except ValueError:
                    messagebox.showerror("Valor inválido", f"'{label}' deve ser um número.", parent=self)
                    return
            else:
                data[key] = val or None
        update_invoice(self._invoice_id, data)
        self._on_save()
        self.destroy()


# ================================================================== #
#  JANELA PRINCIPAL                                                  #
# ================================================================== #
class NFApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NF.ia — Processador de Notas Fiscais")
        self.geometry("1280x700")
        self.minsize(1024, 580)

        self._selected_files: list[str] = []
        self._row_cache: dict[str, dict] = {}   # iid → dict completo da linha

        self._build_layout()
        self._load_table()

    # ------------------------------------------------------------------ #
    #  LAYOUT                                                              #
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_rowconfigure(10, weight=1)
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="🧾  NF.ia",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=20, pady=(28, 4))
        ctk.CTkLabel(sb, text="Processador de Notas Fiscais",
                     font=ctk.CTkFont(size=11), text_color="gray60").grid(row=1, column=0, padx=20, pady=(0, 24))
        ctk.CTkFrame(sb, height=1, fg_color="gray30").grid(row=2, column=0, sticky="ew", padx=16, pady=4)

        ctk.CTkButton(sb, text="📂  Selecionar Arquivos",
                      command=self._select_files, height=40).grid(row=3, column=0, padx=16, pady=(20, 8), sticky="ew")

        self._files_label = ctk.CTkLabel(sb, text="Nenhum arquivo selecionado",
                                         font=ctk.CTkFont(size=11), text_color="gray60", wraplength=180)
        self._files_label.grid(row=4, column=0, padx=16, pady=(0, 16))

        self._btn_process = ctk.CTkButton(
            sb, text="⚙️  Processar Notas", command=self._start_processing_thread,
            height=44, fg_color="#1f6aa5", hover_color="#144f7d",
            font=ctk.CTkFont(size=13, weight="bold"))
        self._btn_process.grid(row=5, column=0, padx=16, pady=4, sticky="ew")

        ctk.CTkButton(sb, text="🔄  Atualizar Tabela", command=self._load_table,
                      height=36, fg_color="transparent", border_width=1
                      ).grid(row=6, column=0, padx=16, pady=(12, 4), sticky="ew")

        ctk.CTkLabel(sb, text="Powered by EasyOCR + Phi-3",
                     font=ctk.CTkFont(size=9), text_color="gray50").grid(row=11, column=0, padx=16, pady=16)

    def _build_main_area(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=3)
        main.grid_columnconfigure(0, weight=1)

        # --- Log ---
        log_frame = ctk.CTkFrame(main)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text="📋  Log de Processamento",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self._log_box = ctk.CTkTextbox(log_frame, height=140,
                                       font=ctk.CTkFont(family="Consolas", size=11),
                                       state="disabled", wrap="word")
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # --- Tabela ---
        table_frame = ctk.CTkFrame(main)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Cabeçalho com ações
        header = ctk.CTkFrame(table_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(header, text="📊  Notas Processadas",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        # Dica de clipboard
        self._clip_label = ctk.CTkLabel(header, text="",
                                        font=ctk.CTkFont(size=10), text_color="#4caf50")
        self._clip_label.pack(side="left", padx=12)

        ctk.CTkButton(header, text="📂  Abrir Arquivo", width=130, height=30,
                      command=self._open_selected_file,
                      fg_color="transparent", border_width=1,
                      font=ctk.CTkFont(size=11)).pack(side="right", padx=(6, 0))
        ctk.CTkButton(header, text="✏️  Editar", width=90, height=30,
                      command=self._edit_selected_row,
                      fg_color="#2d6a4f", hover_color="#1b4332",
                      font=ctk.CTkFont(size=11)).pack(side="right", padx=(6, 0))

        # Treeview
        tv_container = ctk.CTkFrame(table_frame, fg_color="transparent")
        tv_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tv_container.grid_rowconfigure(0, weight=1)
        tv_container.grid_columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(tv_container, columns=COL_LABELS, show="headings", selectmode="browse")

        for label, width in zip(COL_LABELS, COL_WIDTHS):
            self._tree.heading(label, text=label)
            anchor = "w" if label in ("Arquivo", "Descrição", "Chave de Acesso") else "center"
            self._tree.column(label, width=width, anchor=anchor, minwidth=60)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e1e1e", foreground="#eeeeee",
                        fieldbackground="#1e1e1e", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#2b2b2b", foreground="#cccccc",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#1f6aa5")])

        scrollbar_y = ctk.CTkScrollbar(tv_container, command=self._tree.yview)
        scrollbar_x = ctk.CTkScrollbar(tv_container, orientation="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Clique simples → copia célula  |  Duplo clique → abre arquivo
        self._tree.bind("<ButtonRelease-1>", self._on_cell_click)
        self._tree.bind("<Double-1>", lambda e: self._open_selected_file())

    # ------------------------------------------------------------------ #
    #  SELEÇÃO / PROCESSAMENTO                                            #
    # ------------------------------------------------------------------ #
    def _select_files(self):
        files = filedialog.askopenfilenames(
            title="Selecionar Notas Fiscais",
            filetypes=[("PDF / Imagens", "*.pdf *.png *.jpg *.jpeg *.bmp *.tiff"), ("Todos", "*.*")],
        )
        if files:
            self._selected_files = list(files)
            count = len(self._selected_files)
            self._files_label.configure(text=f"{count} arquivo(s) selecionado(s)")
            self._log(f"✅ {count} arquivo(s) selecionado(s).")
        else:
            self._log("ℹ️ Seleção cancelada.")

    def _start_processing_thread(self):
        if not self._selected_files:
            self._log("⚠️  Nenhum arquivo selecionado.")
            return
        self._btn_process.configure(state="disabled", text="⏳  Processando...")
        threading.Thread(target=self._process_files, daemon=True).start()

    def _process_files(self):
        total = len(self._selected_files)
        self._log(f"\n🚀 Iniciando processamento de {total} arquivo(s)...\n")

        for i, file_path in enumerate(self._selected_files, start=1):
            nome = os.path.basename(file_path)
            self._log(f"[{i}/{total}] 📄 {nome}")
            try:
                self._log("       🔍 Extraindo texto com EasyOCR...")
                raw_text = ocr_engine.extract_text(file_path)
                if not raw_text or not raw_text.strip():
                    self._log("       ❌ OCR sem resultado. Pulando.\n")
                    continue
                self._log(f"       ✅ {len(raw_text)} chars extraídos.")

                self._log("       🤖 Enviando para o Phi-3...")
                invoice_data = extract_invoice_data(raw_text)
                if not invoice_data:
                    self._log("       ❌ IA sem resposta. Pulando.\n")
                    continue
                self._log(f"       ✅ IA respondeu OK.")

                self._log("       💾 Salvando no banco...")
                save_invoice(invoice_data, file_path)
                self._log(f"       ✅ Salvo!\n")

            except Exception as e:
                self._log(f"       💥 Erro: {e}\n")

        self._log("✅ Concluído!\n")
        self.after(0, self._load_table)
        self.after(0, lambda: self._btn_process.configure(state="normal", text="⚙️  Processar Notas"))
        self._selected_files = []
        self.after(0, lambda: self._files_label.configure(text="Nenhum arquivo selecionado"))

    # ------------------------------------------------------------------ #
    #  TABELA                                                              #
    # ------------------------------------------------------------------ #
    def _load_table(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._row_cache.clear()

        df = get_all_invoices()
        if df.empty:
            return

        for _, row in df.iterrows():
            def fmt_float(v):
                try:
                    return f"{float(v):.2f}" if v is not None else "—"
                except (ValueError, TypeError):
                    return "—"

            values = (
                row.get("nome_arquivo", ""),
                row.get("cnpj") or "—",
                row.get("emissao") or row.get("data_emissao") or "—",
                row.get("chave_acesso") or "—",
                row.get("descricao_operacao") or "—",
                fmt_float(row.get("valor_produtos")),
                fmt_float(row.get("valor_total") if row.get("valor_total") is not None else row.get("valor")),
                row.get("forma_pagamento") or "—",
            )
            status = row.get("status_validacao", "OK")
            tag = "ok" if status == "OK" else "erro"
            iid = self._tree.insert("", "end", values=values, tags=(tag,))
            self._row_cache[iid] = row.to_dict()

        self._tree.tag_configure("ok",   foreground="#4caf50")
        self._tree.tag_configure("erro", foreground="#f44336")

    def _get_selected_row(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Nenhuma linha selecionada",
                                   "Clique em uma nota antes de usar esta ação.", parent=self)
            return None
        return self._row_cache.get(sel[0])

    # ------------------------------------------------------------------ #
    #  COPIAR CÉLULA AO CLICAR                                            #
    # ------------------------------------------------------------------ #
    def _on_cell_click(self, event):
        """
        Identifica a célula clicada e copia seu valor para a área de transferência.
        Mostra feedback visual temporário no cabeçalho da tabela.
        """
        row_iid = self._tree.identify_row(event.y)
        col_id  = self._tree.identify_column(event.x)   # retorna "#1", "#2", ...

        if not row_iid or not col_id:
            return

        col_index = int(col_id.replace("#", "")) - 1
        if col_index < 0 or col_index >= len(COL_LABELS):
            return

        values = self._tree.item(row_iid, "values")
        if not values or col_index >= len(values):
            return

        cell_value = str(values[col_index])
        if cell_value == "—":
            return

        # Copia para o clipboard
        self.clipboard_clear()
        self.clipboard_append(cell_value)

        # Feedback visual temporário
        col_name = COL_LABELS[col_index]
        preview = cell_value if len(cell_value) <= 30 else cell_value[:27] + "..."
        self._clip_label.configure(text=f"📋 Copiado ({col_name}): {preview}")
        self.after(3000, lambda: self._clip_label.configure(text=""))

    # ------------------------------------------------------------------ #
    #  ABRIR ARQUIVO                                                       #
    # ------------------------------------------------------------------ #
    def _open_selected_file(self):
        """Abre o arquivo com o app padrão do Windows via os.startfile — instantâneo."""
        row = self._get_selected_row()
        if not row:
            return
        path = row.get("caminho_local", "")
        if not path or not os.path.exists(path):
            messagebox.showerror("Arquivo não encontrado",
                                 f"O arquivo não foi localizado:\n{path}", parent=self)
            return
        os.startfile(path)

    # ------------------------------------------------------------------ #
    #  EDITAR LINHA                                                        #
    # ------------------------------------------------------------------ #
    def _edit_selected_row(self):
        row = self._get_selected_row()
        if row:
            EditInvoiceDialog(self, row_data=row, on_save_callback=self._load_table)

    # ------------------------------------------------------------------ #
    #  LOG                                                                 #
    # ------------------------------------------------------------------ #
    def _log(self, message: str):
        def _insert():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", message + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _insert)


# ================================================================== #
if __name__ == "__main__":
    app = NFApp()
    app.mainloop()
