import sqlite3
import pandas as pd
import os
import json

DB_PATH = "data/invoices.db"

def init_db():
    """Initializes the SQLite database and creates the invoices table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj_emitente TEXT,
            nome_emitente TEXT,
            numero_nota TEXT,
            data_emissao TEXT,
            valor_total REAL,
            resumo_servico TEXT,
            file_path TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_invoice(data_dict, file_path):
    """
    Saves the extracted invoice data and file path to the database.
    
    Args:
        data_dict (dict): Dictionary containing invoice data
        file_path (str): Path to the saved PDF/Image file
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Handle potential nulls or missing keys safely
    cursor.execute("""
        INSERT INTO invoices (
            cnpj_emitente, 
            nome_emitente, 
            numero_nota, 
            data_emissao, 
            valor_total, 
            resumo_servico, 
            file_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data_dict.get('cnpj_emitente'),
        data_dict.get('nome_emitente'),
        data_dict.get('numero_nota'),
        data_dict.get('data_emissao'),
        data_dict.get('valor_total'),
        data_dict.get('resumo_servico'),
        file_path
    ))
    
    conn.commit()
    conn.close()

def get_all_invoices():
    """Returns all invoices as a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM invoices ORDER BY processed_at DESC", conn)
    conn.close()
    return df
