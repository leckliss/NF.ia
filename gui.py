import sys
import os
# Desativar verificação de atualização do PaddleOCR
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

# Constantes
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
            # Nota: A inicialização do OCREngine pode ser pesada, idealmente em cache ou passada.
            # Para este MVP, iniciamos aqui ou confiamos que o módulo faça isso de forma eficiente.
            
            # Usar um singleton ou global para OCR no módulo seria melhor para desempenho,
            # garantindo que não recarregamos o modelo a cada clique.
            # Vamos assumir que o usuário aceita a espera ou podemos instanciar fora.
            # Para ser seguro e reutilizar a lógica:
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
        
        # Dados
        self.df_invoices = None
        
        # Configurar UI
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # Layout Principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Barra de Ferramentas / Área de Cabeçalho
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
        
        # Métricas
        self.lbl_metrics = QLabel("Total: 0 | Valor: R$ 0,00")
        self.lbl_metrics.setStyleSheet("font-size: 16px; font-weight: bold; color: #ccc;")
        header_layout.addWidget(self.lbl_metrics)

        main_layout.addLayout(header_layout)

        # Barra de Progresso e Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #aaa; font-style: italic;")
        main_layout.addWidget(self.lbl_status)

        # Divisor (Tabela vs Detalhes)
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Visualização de Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Data", "Emitente", "Valor (R$)", "Arquivo", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)

        # Área de Visualização de Detalhes
        detail_widget = QWidget()
        detail_layout = QHBoxLayout(detail_widget)
        
        # Esquerda: Visualizador de Doc
        self.lbl_doc_viewer = QLabel("Selecione uma nota para visualizar")
        self.lbl_doc_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_doc_viewer.setStyleSheet("background-color: #2b2b2b; border: 1px solid #444;")
        self.lbl_doc_viewer.setMinimumWidth(400)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.lbl_doc_viewer)
        detail_layout.addWidget(scroll_area, 2) # Ratio 2

        # Direita: Campos de Dados
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
        detail_layout.addWidget(data_frame, 1) # Proporção 1

        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 400]) # Divisão inicial

        main_layout.addWidget(splitter)

    def load_data(self):
        init_db() # Garantir que o DB existe
        self.df_invoices = get_all_invoices()
        
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.df_invoices))
        
        total_val = 0.0
        
        for idx, row in self.df_invoices.iterrows():
            # Calcular Status
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
        # Obter dados reais da fatura do DF usando o índice (assumindo que a ordem do DF corresponde à tabela, o que deve acontecer se recarregado)
        # Mais seguro usar ID se houver filtragem, mas para o MVP o mapeamento direto de índice serve se nenhuma classificação for aplicada.
        # Mas espere, crie um mapa ou apenas pegue do DF iloc[row_idx]
        if row_idx < len(self.df_invoices):
            row_data = self.df_invoices.iloc[row_idx]
            self.update_detail_view(row_data)

    def update_detail_view(self, row_data):
        # Atualizar Labels
        self.data_labels["CNPJ Emitente"].setText(str(row_data['cnpj_emitente']))
        self.data_labels["Nome Emitente"].setText(str(row_data['nome_emitente']))
        self.data_labels["Número Nota"].setText(str(row_data['numero_nota']))
        self.data_labels["Data Emissão"].setText(str(row_data['data_emissao']))
        val = row_data['valor_total']
        self.data_labels["Valor Total"].setText(f"R$ {val:,.2f}" if val else "R$ 0,00")
        self.data_labels["Resumo Serviço"].setText(str(row_data['resumo_servico']))
        
        # Exibir Arquivo
        f_path = row_data['file_path']
        if f_path and os.path.exists(f_path):
            self.display_file(f_path)
        else:
            self.lbl_doc_viewer.setText("Arquivo não encontrado")

    def display_file(self, path):
        try:
            # Verificar se é PDF
            if path.lower().endswith('.pdf'):
                doc = fitz.open(path)
                page = doc.load_page(0)  # carregar primeira página
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # zoom para melhor qualidade
                
                # Converter Pixmap do fitz para QImage
                # pix.samples são bytes
                # QImage(bytes, width, height, bytesPerLine, format)
                fmt = QImage.Format.Format_RGB888 if pix.alpha == 0 else QImage.Format.Format_RGBA8888
                qt_img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
                
                self.lbl_doc_viewer.setPixmap(QPixmap.fromImage(qt_img))
            else:
                # Arquivo de imagem
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
    # Configurar App
    app = QApplication(sys.argv)
    
    # Aplicar Tema Escuro
    try:
        if hasattr(qdarktheme, 'setup_theme'):
             qdarktheme.setup_theme()
        else:
            # Fallback para versões mais antigas
            app.setStyleSheet(qdarktheme.load_stylesheet())
    except Exception as e:
        print(f"Warning: Could not apply dark theme: {e}")
    
    window = InvoiceWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
