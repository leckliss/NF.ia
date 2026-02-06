# 🧾 MVP de Automação de Notas Fiscais (Invoice Automator)

Este projeto é um Mínimo Produto Viável (MVP) desenvolvido em Python para automatizar o processo de recebimento, leitura e extração de dados de notas fiscais recebidas por e-mail. Ele combina tecnologias de OCR e Inteligência Artificial Generativa (LLM) para estruturar dados a partir de documentos PDF ou imagens.

---

## 🚀 Funcionalidades Principais

*   **Monitoramento de E-mail**: Simula a conexão com o servidor SmarterMail para buscar e-mails não lidos marcados como "Nota Fiscal".
*   **Download Automático**: Baixa e decodifica anexos (PDFs) codificados em Base64.
*   **OCR Local (PaddleOCR)**: Transforma o conteúdo visual dos arquivos em texto bruto, suportando o idioma português e correção de ângulo.
*   **Extração Inteligente (Ollama/Phi-3)**: Utiliza um modelo de linguagem rodando localmente para interpretar o texto do OCR e extrair campos específicos (CNPJ, Valor, Data, etc.) em formato JSON estruturado.
*   **Split View de Conferência**: Interface gráfica que permite visualizar o documento original lado a lado com os dados extraídos para validação humana.
*   **Painel de Métricas**: Visualização rápida do total de notas processadas e valores financeiros.

---

## 🏗️ Arquitetura e Estrutura dos Módulos

O projeto segue uma arquitetura modular para facilitar a manutenção e escalabilidade.

### 1. `app.py` (Dashboard / Frontend)
O ponto de entrada da aplicação. Construído com **Streamlit**, ele orquestra o fluxo:
1.  Exibe o botão de ação manual "Processar Novos E-mails".
2.  Gerencia a barra de progresso visual.
3.  Consulta o banco de dados para mostrar a tabela de notas.
4.  Implementa a lógica de "Split View" para auditoria das notas.

### 2. `modules/email_client.py` (Integração de E-mail)
Responsável por:
*   Simular a autenticação e busca na API do SmarterMail.
*   Endpoint mockado: `/SearchMessages` e `/GetMessage`.
*   **Crucial**: Recebe o conteúdo do arquivo em string Base64 e o converte/decodifica para um arquivo PDF físico salvo na pasta `downloads/`.

### 3. `modules/ocr_engine.py` (Motor de OCR)
Wrapper em torno da biblioteca **PaddleOCR**.
*   Configurado com `lang='pt'` para melhor precisão em português.
*   Usa `use_angle_cls=True` para detectar se a nota está de cabeça para baixo ou rotacionada.
*   Retorna todo o texto encontrado no documento como uma única string concatenada.

### 4. `modules/ai_processor.py` (Cérebro da IA)
Conecta-se à API local do **Ollama**.
*   **Modelo de LLM**: `phi3:3.8b` (Modelo leve e eficiente).
*   **Engenharia de Prompt**: Utiliza um System Prompt rígido para forçar a saída estritamente em JSON, sem "conversa".
*   Campos extraídos: `cnpj_emitente`, `nome_emitente`, `numero_nota`, `data_emissao`, `valor_total`, `resumo_servico`.

### 5. `modules/database.py` (Persistência)
Gerencia um banco de dados **SQLite** simples (`data/invoices.db`).
*   Armazena os metadados da nota e o caminho do arquivo original.
*   Exporta dados diretamente para **Pandas DataFrame** para exibição no Streamlit.

---

## 🛠️ Configuração e Instalação

### Pré-requisitos
*   Python 3.10 ou superior.
*   [Ollama](https://ollama.com/) instalado e rodando.

### Passo a Passo

1.  **Clone o projeto ou navegue até a pasta**:
    ```bash
    cd c:\Users\erick\Projetos\lecklis\invoice_automator
    ```

2.  **Crie e ative um ambiente virtual (opcional, mas recomendado)**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    ```

3.  **Instale as dependências**:
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: A instalação do PaddleOCR/PaddlePaddle pode demorar um pouco dependendo da sua conexão.*

4.  **Configure o Modelo do Ollama**:
    Certifique-se de baixar o modelo Phi-3 no seu terminal:
    ```bash
    ollama pull phi3:3.8b
    ```
    Mantenha o servidor do Ollama rodando (geralmente ele roda em background na porta 11434).

5.  **Configure as Variáveis de Ambiente**:
    Crie um arquivo `.env` na raiz do projeto (baseado no `.env.example`):
    ```env
    SMARTERMAIL_URL=https://mail.exemplo.com/api/v1 # (URL Mockada no código atual)
    SMARTERMAIL_USER=seu_usuario
    SMARTERMAIL_PASS=sua_senha
    OLLAMA_URL=http://localhost:11434/api/generate
    ```

---

## ▶️ Como Rodar

Execute o comando abaixo para iniciar o Dashboard:

```bash
streamlit run app.py
```

O navegador abrirá automaticamente no endereço `http://localhost:8501`.

### Fluxo de Uso
1.  No menu lateral esquerdo, clique em **"🔄 Processar Novos E-mails"**.
    *   *Nota: Como este MVP usa dados mockados, ele simulará o download de uma nota fiscal de exemplo.*
2.  Aguarde a barra de progresso finalizar as etapas (Download -> OCR -> AI -> Banco).
3.  Verifique a tabela na tela principal.
4.  **Clique em uma linha da tabela** para abrir a conferência detalhada (PDF à esquerda, Dados à direita).
5.  Se houver dados faltantes (ex: Valor Total nulo), a linha será destacada com um alerta visual.

---
**Observação**: Este é um MVP. Em produção, a classe `SmarterMailClient` deve ter as chamadas à API descomentadas e a URL real configurada.
