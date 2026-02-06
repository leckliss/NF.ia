# 🧾 MVP de Automação de Notas Fiscais (Invoice Automator)

Este projeto é um Mínimo Produto Viável (MVP) desenvolvido em Python para automatizar o processo de recebimento, leitura e extração de dados de notas fiscais recebidas por e-mail. Ele combina tecnologias de OCR e Inteligência Artificial Generativa (LLM) para estruturar dados a partir de documentos PDF ou imagens.

---

## 🚀 Funcionalidades Principais

*   **Automação Completa**: Monitora e-mails, baixa anexos PDF/Base64, executa OCR e extrai dados com IA.
*   **Interface Desktop Moderna (PyQt6)**: Dashboard nativo com tema escuro e alta performance.
*   **OCR & AI Local**: PaddleOCR para leitura + Ollama (Phi-3) para estruturação JSON.
*   **Split View**: Visualize o PDF da nota ao lado dos dados extraídos para conferência.
*   **Banco de Dados**: Histórico persistente em SQLite.

---

## 🏗️ Estrutura do Projeto

*   `gui.py`: **Aplicação Principal** (Desktop GUI em PyQt6).
*   `app.py`: Interface Web legada (Streamlit) - *Opcional*.
*   `modules/`: Lógica de negócio (Email, OCR, AI, DB).
*   `downloads/`: Armazena os PDFs processados.
*   `data/`: Banco de dados SQLite.

---

## 🛠️ Instalação

1.  **Pré-requisitos**:
    *   Python 3.10+
    *   [Ollama](https://ollama.com/) instalado com modelo `phi3:3.8b`.

2.  **Instalar Dependências**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar Variáveis**:
    Crie o arquivo `.env` (copie de `.env.example`) e ajuste suas credenciais.

4.  **Preparar Ollama**:
    ```bash
    ollama pull phi3:3.8b
    ollama serve
    ```

---

## ▶️ Como Rodar

### Interface Recomendada (Desktop)
Execute a nova interface moderna construída com PyQt6:

```bash
python gui.py
```

### Interface Web (Streamlit - Legado)
Caso prefira a versão web:
```bash
streamlit run app.py
```

---

## 📝 Uso
1.  Clique em **"Processar Novos E-mails"** na barra superior.
2.  Aguarde o processamento (Download -> OCR -> IA).
3.  Selecione uma nota na tabela para ver os detalhes e a imagem do documento abaixo.
