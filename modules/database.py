
import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = os.path.join("data", "invoices.db")


def init_db():
    """
    Inicializa o banco de dados e cria a tabela 'invoices' com o schema expandido.
    Se a tabela já existir com colunas antigas, adiciona as novas via ALTER TABLE.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            data_processamento  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nome_arquivo        TEXT,
            caminho_local       TEXT,
            cnpj                TEXT,
            emissao             TEXT,
            valor_total         REAL,
            valor_produtos      REAL,
            chave_acesso        TEXT,
            descricao_operacao  TEXT,
            forma_pagamento     TEXT,
            status_validacao    TEXT DEFAULT 'OK'
        )
    """)

    # Migração não-destrutiva: adiciona colunas novas se a tabela já existir sem elas
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(invoices)")}
    new_cols = {
        "valor_produtos":     "REAL",
        "chave_acesso":       "TEXT",
        "descricao_operacao": "TEXT",
        "forma_pagamento":    "TEXT",
        "emissao":            "TEXT",
        "valor_total":        "REAL",
    }
    for col, col_type in new_cols.items():
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {col_type}")
            print(f"[DB] Coluna adicionada: {col}")

    conn.commit()
    conn.close()
    print(f"Banco de dados inicializado em: {DB_PATH}")


def save_invoice(data_dict: dict, caminho_arquivo: str):
    """
    Salva os dados extraídos de uma nota fiscal no banco de dados.
    Aceita tanto o schema antigo quanto o novo.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    nome_arquivo = os.path.basename(caminho_arquivo)

    try:
        cursor.execute("""
            INSERT INTO invoices (
                nome_arquivo, caminho_local,
                cnpj, emissao, valor_total, valor_produtos,
                chave_acesso, descricao_operacao, forma_pagamento,
                status_validacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome_arquivo,
            caminho_arquivo,
            data_dict.get("cnpj"),
            data_dict.get("emissao") or data_dict.get("data_emissao"),
            _to_float(data_dict.get("valor_total") or data_dict.get("valor")),
            _to_float(data_dict.get("valor_produtos")),
            data_dict.get("chave_acesso"),
            data_dict.get("descricao_operacao"),
            data_dict.get("forma_pagamento"),
            data_dict.get("status_validacao", "OK"),
        ))
        conn.commit()
        print(f"Nota salva: {nome_arquivo}")
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")
    finally:
        conn.close()


def update_invoice(invoice_id: int, data_dict: dict):
    """Atualiza os dados de uma nota existente no banco pelo ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE invoices
            SET cnpj = ?, emissao = ?, valor_total = ?, valor_produtos = ?,
                chave_acesso = ?, descricao_operacao = ?, forma_pagamento = ?,
                status_validacao = ?
            WHERE id = ?
        """, (
            data_dict.get("cnpj"),
            data_dict.get("emissao"),
            _to_float(data_dict.get("valor_total")),
            _to_float(data_dict.get("valor_produtos")),
            data_dict.get("chave_acesso"),
            data_dict.get("descricao_operacao"),
            data_dict.get("forma_pagamento"),
            data_dict.get("status_validacao", "OK"),
            invoice_id,
        ))
        conn.commit()
        print(f"Nota ID={invoice_id} atualizada.")
    except Exception as e:
        print(f"Erro ao atualizar nota ID={invoice_id}: {e}")
    finally:
        conn.close()


def get_all_invoices() -> pd.DataFrame:
    """Retorna todas as invoices como um pandas DataFrame, ordenadas por data."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM invoices ORDER BY data_processamento DESC", conn
        )
        return df
    except Exception as e:
        print(f"Erro ao ler do banco: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def _to_float(value) -> float | None:
    """Converte valor para float de forma segura."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    init_db()
