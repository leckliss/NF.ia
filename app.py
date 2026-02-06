import streamlit as st
import pandas as pd
import os
import base64
from modules.email_client import SmarterMailClient
from modules.ocr_engine import OCREngine
from modules.ai_processor import extract_invoice_data
from modules.database import init_db, save_invoice, get_all_invoices

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
st.set_page_config(page_title="Invoice Automator MVP", layout="wide")

# Initialize Database
init_db()

# ---------------------------------------------------------
# Resource Caching
# ---------------------------------------------------------
@st.cache_resource
def get_ocr_engine():
    return OCREngine()

# ---------------------------------------------------------
# UI Helper Functions
# ---------------------------------------------------------
def display_pdf(file_path):
    """Displays a PDF file in Streamlit using an iframe."""
    if not os.path.exists(file_path):
        st.error("Arquivo não encontrado.")
        return

    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar & Processing Pipeline
# ---------------------------------------------------------
st.sidebar.title("Menu")
if st.sidebar.button("🔄 Processar Novos E-mails"):
    st.sidebar.write("Iniciando processamento...")
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()

    # 1. Initialize Clients
    email_client = SmarterMailClient()
    ocr = get_ocr_engine()
    
    # 2. Search Messages
    status_text.text("Buscando e-mails...")
    msg_ids = email_client.search_unseen_invoices()
    
    if not msg_ids:
        status_text.text("Nenhum e-mail novo encontrado.")
        progress_bar.progress(100)
    else:
        total = len(msg_ids)
        for i, msg_id in enumerate(msg_ids):
            status_text.text(f"Processando Msg ID: {msg_id} ({i+1}/{total})")
            
            # 3. Download
            downloaded_files = email_client.download_attachment(msg_id)
            
            for f_path in downloaded_files:
                # 4. OCR
                status_text.text(f"Extraindo texto: {os.path.basename(f_path)}...")
                raw_text = ocr.extract_text(f_path)
                
                # 5. AI Extraction
                status_text.text(f"Processando com AI...")
                invoice_data = extract_invoice_data(raw_text)
                
                if invoice_data:
                    # 6. Save to DB
                    save_invoice(invoice_data, f_path)
            
            progress_bar.progress(int((i + 1) / total * 100))
        
        status_text.text("Processamento concluído!")
        st.toast("Processamento finalizado com sucesso!")
        st.rerun() # Refresh data

# ---------------------------------------------------------
# Main Layout
# ---------------------------------------------------------
st.title("📊 Invoice Processing Dashboard")

# Fetch Data
df = get_all_invoices()

# Metrics
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Total de Notas", len(df))
total_value = df['valor_total'].sum() if not df.empty else 0.0
col_m2.metric("Valor Total (R$)", f"R$ {total_value:,.2f}")

# Data Table with Selection
st.subheader("Notas Fiscais Processadas")

# Highlight rows with missing critical data (Visual Cue in generic table limits)
# We can use Pandas Styler but for st.dataframe selection, it's safer to just pass the df
# and maybe add a column 'Status'
if not df.empty:
    df['Status'] = df.apply(lambda x: '⚠️ Pendente' if (pd.isna(x['valor_total']) or pd.isna(x['cnpj_emitente'])) else '✅ OK', axis=1)
    
    # Selection Mode
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "file_path": st.column_config.TextColumn("Arquivo", help="Caminho do arquivo"),
            "valor_total": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        }
    )

    # ---------------------------------------------------------
    # Split View (Conference)
    # ---------------------------------------------------------
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_row = df.iloc[selected_idx]
        
        st.markdown("---")
        st.subheader("🔍 Conferência Detalhada")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.info(f"Visualizando: {os.path.basename(selected_row['file_path'])}")
            f_path = selected_row['file_path']
            if f_path.lower().endswith('.pdf'):
                display_pdf(f_path)
            else:
                st.image(f_path)
        
        with c2:
            st.info("Dados Extraídos (JSON)")
            
            # Check for nulls to highlight
            cnpj = selected_row['cnpj_emitente']
            val = selected_row['valor_total']
            
            if pd.isna(cnpj) or pd.isna(val) or val == 0:
                st.error("⚠️ Atenção: CNPJ ou Valor Total não identificados corretamente!")
            
            # Reconstruct JSON for display or fetch form DB fields
            data_preview = {
                "cnpj_emitente": selected_row['cnpj_emitente'],
                "nome_emitente": selected_row['nome_emitente'],
                "numero_nota": selected_row['numero_nota'],
                "data_emissao": selected_row['data_emissao'],
                "valor_total": selected_row['valor_total'],
                "resumo_servico": selected_row['resumo_servico']
            }
            st.json(data_preview)
            
            # Optional: Allow Manual Correction (Bonus, not strictly required but helpful MVP feature)
            # st.text_input("Corrigir CNPJ", value=selected_row['cnpj_emitente']) ...
            
else:
    st.info("Nenhuma nota processada ainda. Use o menu lateral para iniciar.")
