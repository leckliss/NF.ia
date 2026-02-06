import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = "phi3:3.8b"

def extract_invoice_data(raw_text):
    """
    Sends raw OCR text to Ollama (Phi-3) to extract structured invoice data.
    """
    
    system_prompt = (
        "You are a data extraction assistant. Output ONLY valid JSON. "
        "No markdown formatting, no conversational text. If a field is missing, use null."
    )
    
    user_prompt = f"""
    Extract the following fields from the invoice text below:
    - cnpj_emitente (numbers only)
    - nome_emitente (string)
    - numero_nota (string)
    - data_emissao (YYYY-MM-DD)
    - valor_total (float, e.g. 100.50)
    - resumo_servico (short string)

    Return JSON format:
    {{
        "cnpj_emitente": "...",
        "nome_emitente": "...",
        "numero_nota": "...",
        "data_emissao": "...",
        "valor_total": 0.0,
        "resumo_servico": "..."
    }}

    Invoice Text:
    {raw_text}
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": user_prompt,
        "system": system_prompt,
        "format": "json",
        "temperature": 0.1,
        "stream": False
    }
    
    print(f"Sending text to Ollama ({MODEL_NAME})...")
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result_json = response.json()
        generated_text = result_json.get("response", "")
        
        # Parse JSON from the response
        try:
            data = json.loads(generated_text)
            return data
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from LLM response: {generated_text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        return None
