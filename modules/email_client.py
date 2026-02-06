import requests
import json
import base64
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SmarterMailClient:
    def __init__(self):
        self.base_url = os.getenv("SMARTERMAIL_URL", "http://localhost/api/v1")
        self.username = os.getenv("SMARTERMAIL_USER", "user")
        self.password = os.getenv("SMARTERMAIL_PASS", "pass")
        self.token = None
        self.download_folder = "downloads"
        os.makedirs(self.download_folder, exist_ok=True)

    def login(self):
        """
        Authenticates with SmarterMail and retrieves an AuthToken.
        Simulated/Generic implementation.
        """
        url = f"{self.base_url}/auth/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        # In a real scenario:
        # response = requests.post(url, json=payload)
        # response.raise_for_status()
        # self.token = response.json().get("accessToken")
        
        # Simulation for MVP robustness if API not available:
        self.token = "mock-token-12345"
        print(f"Logged in as {self.username}. Token: {self.token}")

    def search_unseen_invoices(self):
        """
        Searches for unread messages with subject containing "Nota Fiscal".
        Endpoint: POST /settings/sysadmin/search-messages (adjusted to generic /SearchMessages per prompt)
        """
        if not self.token:
            self.login()
            
        url = f"{self.base_url}/SearchMessages"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Search criteria: unread and subject match
        payload = {
            "folder": "Inbox",
            "isRead": False,
            "subject": "Nota Fiscal"
        }
        
        # Real call:
        # response = requests.post(url, json=payload, headers=headers)
        # return response.json().get("messageIds", [])
        
        # Mock Return for MVP demonstration
        print("Searching for unseen invoices...")
        return ["msg-001", "msg-002"]

    def download_attachment(self, message_id):
        """
        Fetches message details, finds PDF attachment, decodes Base64, and saves it.
        endpoint: POST /GetMessage
        """
        url = f"{self.base_url}/GetMessage"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"id": message_id}
        
        # Real call:
        # response = requests.post(url, json=payload, headers=headers)
        # data = response.json()
        
        # Mock Response Data simulating the structure described in prompt:
        # "O Mock/Simulação da resposta JSON deve prever um campo attachments contendo fileContent em Base64."
        
        # Simulating a PDF file content (empty PDF header for demo or just text)
        # Using a minimal valid PDF base64 for testing purposes would be better, 
        # but here is a safe dummy string or valid minimal PDF if possible.
        # Minimal PDF Base64:
        dummy_pdf_b64 = "JVBERi0xLjQNCiW0vuWgNCjEIDAgb2JqDQo8PA0KL1R5cGUgL0NhdGFsb2cNCi9QYWdlcyAyIDAgUg0KPj4NCmVuZG9iag0KMiAwIG9iag0KPDwNCi9UeXBlIC9QYWdlcw0KL0tpZHMgWzMgMCBSXQ0KL0NvdW50IDENCj4+DQplbmRvYWoNCjMgMCBvYmoNCjw8DQovVHlwZSAvUGFnZQ0KL1BhcmVudCAyIDAgUg0KL01lZGlhQm94IFswIDAgNjEyIDc5Ml0NCi9SZXNvdXJjZXMgPDwNCi9Gb250IDw8DQovRjEgNCAwIFINCj4+DQo+Pg0KL0NvbnRlbnRzIDUgMCBSDQo+Pg0KZW5kb2JqDQo0IDAgb2JqDQo8PA0KL1R5cGUgL0ZvbnQNCi9TdWJ0eXBlIC9UeXBlMQ0KL0Jhc2VGb250IC9IZWx2ZXRpY2ENCj4+DQplbmRvYWoNCjUgMCBvYmoNCjw8IC9MZW5ndGggNDQgPj4NCnN0cmVhbQ0KQlQNCjcwIDcwIFREDQovRjEgMjQgVGYNCihOb3RhIEZpc2NhbCBUZXN0ZSkgVGoNCkVUDQplbmRzdHJlYW0NCmVuZG9iag0KeHJlZg0KMCA2DQowMDAwMDAwMDAwIDY1NTM1IGYNCjAwMDAwMDAwMTAgMDAwMDAgbg0KMDAwMDAwMDA2MCAwMDAwMCBuDQowMDAwMDAwMTU3IDAwMDAwIG4NCjAwMDAwMDAzMDIgMDAwMDAgbg0KMDAwMDAwMDM4OSAwMDAwMCBuDQp0cmFpbGVyDQo8PA0KL1NpemUgNg0KL1Jvb3QgMSAwIFINCj4+DQpzdGFydHhyZWYNCjQ4Mw0KJSVFT0Y="
        
        mock_data = {
            "id": message_id,
            "subject": "Nota Fiscal de Serviço",
            "attachments": [
                {
                    "fileName": "fatura.pdf",
                    "fileContent": dummy_pdf_b64 
                }
            ]
        }
        
        data = mock_data
        
        saved_files = []
        
        if "attachments" in data:
            for att in data["attachments"]:
                filename = att.get("fileName")
                content_b64 = att.get("fileContent")
                
                if filename and content_b64:
                    # CRUCIAL: Decode Base64 content
                    # We decoded the specific field 'fileContent' which contains the file bytes encoded as a base64 string.
                    try:
                        file_data = base64.b64decode(content_b64)
                        
                        # Generate unique name
                        unique_name = f"nota_{message_id}_{uuid.uuid4().hex[:8]}.pdf"
                        file_path = os.path.join(self.download_folder, unique_name)
                        
                        with open(file_path, "wb") as f:
                            f.write(file_data)
                        
                        saved_files.append(file_path)
                        print(f"Saved attachment: {file_path}")
                    except Exception as e:
                        print(f"Error decoding/saving attachment {filename}: {e}")
                        
        return saved_files
