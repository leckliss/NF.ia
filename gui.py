import sys
import os
# Disable PaddleOCR update check
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import fitz  # PyMuPDF
import qdarktheme
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QProgressBar,
    QLabel, QSplitter, QMessageBox, QHeaderView, QScrollArea, QFrame,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QAction, QIcon, QColor

from modules.email_client import SmarterMailClient
from modules.ocr_engine import OCREngine
from modules.ai_processor import extract_invoice_data
from modules.database import init_db, save_invoice, get_all_invoices

# Constants
STATUS_PENDING = "⚠️ Pendente"
STATUS_OK = "✅ OK"

class ProcessingWorker(QThread):
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished_processing = pyqtSignal()
    
    def run(self):
        try:
            self.status_update.emit("Iniciando clientes...")
            email_client = SmarterMailClient()
            # Note: OCREngine initialization might be heavy, ideally cached or passed in.
            # For this MVP, we init here or rely on the module doing it efficiently.
            
            # Using a singleton or global for OCR in the module would be better for performance,
            # ensuring we don't reload the model every click. 
            # We'll assume the user is okay with the wait or we can instantiate outside.
            # To be safe and reuse logic:
            ocr = OCREngine() 

            self.status_update.emit("Buscando e-mails...")
            msg_ids = email_client.search_unseen_invoices()

            if not msg_ids:
                self.status_update.emit("Nenhum e-mail novo.")
                self.progress_update.emit(100)
                self.finished_processing.emit()
                return

            total = len(msg_ids)
            for i, msg_id in enumerate(msg_ids):
                self.status_update.emit(f"Baixando MSG ID: {msg_id} ({i+1}/{total})")
                downloaded_files = email_client.download_attachment(msg_id)

                for f_path in downloaded_files:
                    self.status_update.emit(f"OCR: {os.path.basename(f_path)}")
                    raw_text = ocr.extract_text(f_path)
                    
                    self.status_update.emit("Processando IA...")
                    invoice_data = extract_invoice_data(raw_text)
                    
                    if invoice_data:
                        save_invoice(invoice_data, f_path)
                
                self.progress_update.emit(int((i + 1) / total * 100))

            self.status_update.emit("Concluído!")
            self.finished_processing.emit()
            
        except Exception as e:
            self.status_update.emit(f"Erro: {str(e)}")
            self.finished_processing.emit()

class InvoiceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Invoice Automator Pro")
        self.resize(1200, 800)
        
        # Data
        self.df_invoices = None
        
        # Setup UI
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # Main Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Toolbar / Header Area
        header_layout = QHBoxLayout()
        
        self.btn_process = QPushButton("🔄 Processar Novos E-mails")
        self.btn_process.setMinimumHeight(40)
        self.btn_process.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #007bff; color: white; border-radius: 5px;")
        self.btn_process.clicked.connect(self.start_processing)
        
        self.btn_refresh = QPushButton("Atualizar Tabela")
        self.btn_refresh.setMinimumHeight(40)
        self.btn_refresh.clicked.connect(self.load_data)

        header_layout.addWidget(self.btn_process)
        header_layout.addWidget(self.btn_refresh)
        header_layout.addStretch()
        
        # Metrics
        self.lbl_metrics = QLabel("Total: 0 | Valor: R$ 0,00")
        self.lbl_metrics.setStyleSheet("font-size: 16px; font-weight: bold; color: #ccc;")
        header_layout.addWidget(self.lbl_metrics)

        main_layout.addLayout(header_layout)

        # Progress Bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #aaa; font-style: italic;")
        main_layout.addWidget(self.lbl_status)

        # Splitter (Table vs Details)
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Table View
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Data", "Emitente", "Valor (R$)", "Arquivo", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)

        # Detail View Area
        detail_widget = QWidget()
        detail_layout = QHBoxLayout(detail_widget)
        
        # Left: Doc Viewer
        self.lbl_doc_viewer = QLabel("Selecione uma nota para visualizar")
        self.lbl_doc_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_doc_viewer.setStyleSheet("background-color: #2b2b2b; border: 1px solid #444;")
        self.lbl_doc_viewer.setMinimumWidth(400)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.lbl_doc_viewer)
        detail_layout.addWidget(scroll_area, 2) # Ratio 2

        # Right: Data Fields
        data_frame = QFrame()
        data_frame.setStyleSheet("background-color: #2b2b2b; border: 1px solid #444; padding: 10px;")
        self.data_layout = QVBoxLayout(data_frame)
        self.data_labels = {}
        
        fields = ["CNPJ Emitente", "Nome Emitente", "Número Nota", "Data Emissão", "Valor Total", "Resumo Serviço"]
        for field in fields:
            lbl_title = QLabel(f"{field}:")
            lbl_title.setStyleSheet("font-weight: bold; color: #ddd;")
            lbl_value = QLabel("---")
            lbl_value.setWordWrap(True)
            lbl_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
            self.data_layout.addWidget(lbl_title)
            self.data_layout.addWidget(lbl_value)
            self.data_labels[field] = lbl_value
            
        self.data_layout.addStretch()
        detail_layout.addWidget(data_frame, 1) # Ratio 1

        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 400]) # Initial split

        main_layout.addWidget(splitter)

    def load_data(self):
        init_db() # Ensure DB exists
        self.df_invoices = get_all_invoices()
        
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.df_invoices))
        
        total_val = 0.0
        
        for idx, row in self.df_invoices.iterrows():
            # Calculate Status
            val = row['valor_total']
            formatted_val = f"R$ {val:,.2f}" if val is not None else "R$ 0,00"
            if val is not None:
                total_val += val
                
            status = STATUS_OK
            if val is None or row['cnpj_emitente'] is None:
                status = STATUS_PENDING
            
            # ID
            self.table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
            # Data
            self.table.setItem(idx, 1, QTableWidgetItem(str(row['data_emissao'])))
            # Emitente
            self.table.setItem(idx, 2, QTableWidgetItem(str(row['nome_emitente'])))
            # Valor
            self.table.setItem(idx, 3, QTableWidgetItem(formatted_val))
            # Arquivo
            filename = os.path.basename(row['file_path']) if row['file_path'] else ""
            self.table.setItem(idx, 4, QTableWidgetItem(filename))
            # Status
            item_status = QTableWidgetItem(status)
            if status == STATUS_PENDING:
                item_status.setForeground(QColor("orange"))
            else:
                item_status.setForeground(QColor("#00e676"))
            self.table.setItem(idx, 5, item_status)

        self.lbl_metrics.setText(f"Total: {len(self.df_invoices)} | Valor: R$ {total_val:,.2f}")

    def on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
            
        row_idx = selected_items[0].row()
        # Get actual invoice data from DF using the index (assuming DF order matches table, which it should if reloaded)
        # Safer to use ID if filtering was involved, but for MVP direct index mapping is fine if no sort applied.
        # But wait, create a map or just grab from DF iloc[row_idx]
        if row_idx < len(self.df_invoices):
            row_data = self.df_invoices.iloc[row_idx]
            self.update_detail_view(row_data)

    def update_detail_view(self, row_data):
        # Update Labels
        self.data_labels["CNPJ Emitente"].setText(str(row_data['cnpj_emitente']))
        self.data_labels["Nome Emitente"].setText(str(row_data['nome_emitente']))
        self.data_labels["Número Nota"].setText(str(row_data['numero_nota']))
        self.data_labels["Data Emissão"].setText(str(row_data['data_emissao']))
        val = row_data['valor_total']
        self.data_labels["Valor Total"].setText(f"R$ {val:,.2f}" if val else "R$ 0,00")
        self.data_labels["Resumo Serviço"].setText(str(row_data['resumo_servico']))
        
        # Display File
        f_path = row_data['file_path']
        if f_path and os.path.exists(f_path):
            self.display_file(f_path)
        else:
            self.lbl_doc_viewer.setText("Arquivo não encontrado")

    def display_file(self, path):
        try:
            # Check if PDF
            if path.lower().endswith('.pdf'):
                doc = fitz.open(path)
                page = doc.load_page(0)  # load first page
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # zoom for better quality
                
                # Convert fitz Pixmap to QImage
                # pix.samples is bytes
                # QImage(bytes, width, height, bytesPerLine, format)
                fmt = QImage.Format.Format_RGB888 if pix.alpha == 0 else QImage.Format.Format_RGBA8888
                qt_img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
                
                self.lbl_doc_viewer.setPixmap(QPixmap.fromImage(qt_img))
            else:
                # Image file
                self.lbl_doc_viewer.setPixmap(QPixmap(path).scaled(800, 1000, Qt.AspectRatioMode.KeepAspectRatio))
        except Exception as e:
            self.lbl_doc_viewer.setText(f"Erro ao abrir arquivo: {e}")

    def start_processing(self):
        self.btn_process.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Iniciando thread...")
        
        self.worker = ProcessingWorker()
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.lbl_status.setText)
        self.worker.finished_processing.connect(self.on_processing_finished)
        self.worker.start()

    def on_processing_finished(self):
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.load_data()
        QMessageBox.information(self, "Sucesso", "Processamento de notas finalizado!")

def main():
    # Setup App
    app = QApplication(sys.argv)
    
    # Apply Dark Theme
    try:
        if hasattr(qdarktheme, 'setup_theme'):
            qdarktheme.setup_theme()
        else:
            # Fallback for older versions
            app.setStyleSheet(qdarktheme.load_stylesheet())
    except Exception as e:
        print(f"Warning: Could not apply dark theme: {e}")
    
    window = InvoiceWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
