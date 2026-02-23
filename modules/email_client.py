
import requests
import os
import base64
import uuid
import shutil

class SmarterMailClient:
    def __init__(self):
        # Em produção, usaria variáveis de ambiente
        self.base_url = os.getenv("SMARTERMAIL_API_URL", "http://mail.exemplo.com/api/v1")
        self.username = os.getenv("SMARTERMAIL_USER", "usuario@dominio.com")
        self.password = os.getenv("SMARTERMAIL_PASS", "senha123")
        self.token = None
        self.download_folder = "downloads"
        
        # Garante pasta de downloads
        os.makedirs(self.download_folder, exist_ok=True)

    def login(self):
        """Autentica na API (Simulado/Real)."""
        # Exemplo de chamada real:
        # resp = requests.post(f"{self.base_url}/auth/login", json={"username": self.username, "password": self.password})
        # self.token = resp.json().get("access_token")
        self.token = "mock-token-xyz"
        print("Login efetuado (Mock).")

    def search_unseen_invoices(self):
        """Busca IDs de e-mails não lidos com 'Nota Fiscal'."""
        if not self.token:
            self.login()
        
        # Exemplo Real:
        # headers = {"Authorization": f"Bearer {self.token}"}
        # resp = requests.post(f"{self.base_url}/folders/inbox/search", headers=headers, json={"isRead": False, "subject": "Nota Fiscal"})
        # return [msg['id'] for msg in resp.json()['messages']]
        
        return [] # Retorna vazio na implementação padrão se não estiver usando Mock

    def get_message_attachment(self, message_id):
        """Baixa anexo de uma mensagem específica."""
        # Lógica real de baixar e decodificar Base64 iria aqui
        pass

    def get_mock_email(self):
        """
        Simula a chegada de um e-mail copiando um arquivo de exemplo 
        da raiz para a pasta de downloads.
        """
        print("Simulando recebimento de e-mail...")
        
        # Procura por arquivos de exemplo na raiz
        arquivos_exemplo = [f for f in os.listdir('.') if f.startswith('exemplo') and f.endswith(('.pdf', '.png', '.jpg'))]
        
        if not arquivos_exemplo:
            print("Nenhum arquivo 'exemplo.*' encontrado na raiz para simulação.")
            return []

        # Pega o primeiro encontrado
        origem = arquivos_exemplo[0]
        ext = os.path.splitext(origem)[1]
        
        # Cria um nome único como se fosse um anexo novo
        novo_nome = f"fatura_mock_{uuid.uuid4().hex[:8]}{ext}"
        destino = os.path.join(self.download_folder, novo_nome)
        
        shutil.copy(origem, destino)
        print(f"Arquivo simulado baixado: {destino}")
        
        return [destino]
