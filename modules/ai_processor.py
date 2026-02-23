import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi3"


class AIProcessor:
    """
    Gerencia a comunicação com o Ollama/Phi-3.
    Mantém o modelo carregado na RAM via keep_alive=-1 e faz warm-up na inicialização.
    """

    def __init__(self):
        print(f"--- [AI Init] Inicializando AIProcessor (modelo: {MODEL_NAME})...")
        self._warm_up_model()

    def _warm_up_model(self):
        """Força o carregamento do modelo na RAM sem gerar texto útil."""
        print("--- [AI Warm-up] Carregando modelo na RAM...")
        try:
            requests.post(OLLAMA_URL, json={
                "model": MODEL_NAME, "prompt": "oi",
                "stream": False, "keep_alive": -1,
                "options": {"num_predict": 1}
            }, timeout=120)
            print("--- [AI Warm-up] Modelo carregado e residente na RAM.")
        except requests.exceptions.RequestException as e:
            print(f"--- [AI Warm-up] Aviso: Ollama não respondeu ({e}). Será carregado na 1ª requisição.")

    def extract(self, raw_text: str) -> dict | None:
        """Envia texto OCR para o Phi-3 e retorna JSON estruturado com dados da NF."""

        system_prompt = (
            "You are a strict Brazilian invoice (Nota Fiscal) data extraction assistant. "
            "Extract invoice details from the provided text. "
            "Output ONLY a single valid JSON object — no markdown, no explanation, no extra text. "
            "If a field is not found in the text, use null or 'N/A'. Never omit a key. "
            "Expected JSON structure:\n"
            "{\n"
            '  "cnpj": "only digits of the emitter CNPJ",\n'
            '  "emissao": "emission date as YYYY-MM-DD or null",\n'
            '  "valor_total": float or null,\n'
            '  "valor_produtos": float or null,\n'
            '  "chave_acesso": "44-digit NF-e access key or N/A",\n'
            '  "descricao_operacao": "short description of the operation or N/A",\n'
            '  "forma_pagamento": "payment method or N/A"\n'
            "}"
        )

        user_prompt = (
            f"Extract all invoice fields from the text below.\n\n"
            f"Invoice text:\n{raw_text}\n\n"
            f"JSON Output:"
        )

        payload = {
            "model": MODEL_NAME,
            "prompt": user_prompt,
            "system": system_prompt,
            "format": "json",
            "stream": False,
            "keep_alive": -1,
            "options": {
                "temperature": 0.0,
                "num_predict": 400,  # Mais campos = um pouco mais de tokens
                "num_ctx": 2048,
            },
        }

        print(f"--- [AI] Enviando para {MODEL_NAME}...")

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=600)  # 10 min para CPU lenta
            response.raise_for_status()
            generated_text = response.json().get("response", "")
            data = _parse_json_from_string(generated_text)

            if not data:
                return {"cnpj": None, "emissao": None, "valor_total": 0.0,
                        "valor_produtos": None, "chave_acesso": "N/A",
                        "descricao_operacao": "N/A", "forma_pagamento": "N/A",
                        "status_validacao": "ERRO_JSON"}

            # Define status automaticamente se a IA não enviou
            if not data.get("status_validacao"):
                data["status_validacao"] = "OK" if data.get("cnpj") and data.get("valor_total") else "ERRO"

            return data

        except requests.exceptions.RequestException as e:
            print(f"!!! Erro de conexão com Ollama: {e}")
            return None


# Singleton de módulo — Streamlit/tkinter reutiliza pelo import
_processor = AIProcessor()


def extract_invoice_data(raw_text: str) -> dict | None:
    """Interface pública mantida para compatibilidade."""
    return _processor.extract(raw_text)


def _parse_json_from_string(text: str) -> dict | None:
    """Tenta extrair um objeto JSON de uma string que pode conter lixo."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"!!! Falha no parse JSON: {e}")
    return None
