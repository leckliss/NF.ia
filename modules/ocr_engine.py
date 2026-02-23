import os
import easyocr
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

class OCREngine:
    def __init__(self):
        print("--- [OCR Init] Inicializando EasyOCR (Modo CPU)...")
        # gpu=False garante que rode no processador sem dar erro
        self.reader = easyocr.Reader(['pt'], gpu=False)

    def extract_text(self, file_path):
        """Identifica a extensão e processa o arquivo."""
        print(f"--- [OCR] Processando: {file_path}")
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf':
                return self._process_pdf(file_path)
            else:
                return self._process_image(file_path)
        except Exception as e:
            print(f"!!! Erro no OCR: {e}")
            return None

    def _process_image(self, img_path):
        # detail=0 retorna só os textos; paragraph=True agrupa frases próximas
        resultados = self.reader.readtext(img_path, detail=0, paragraph=True)
        return "\n".join(resultados)

    def _process_pdf(self, pdf_path):
        texto_acumulado = []
        doc = fitz.open(pdf_path)
        
        for i, page in enumerate(doc):
            print(f"--- [OCR] Lendo página {i+1} de {len(doc)}...")
            # dpi=200 é o ponto ideal entre velocidade e qualidade
            pix = page.get_pixmap(dpi=200)
            
            modo = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(modo, [pix.width, pix.height], pix.samples)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            img_np = np.array(img)
            
            resultados = self.reader.readtext(img_np, detail=0, paragraph=True)
            texto_acumulado.append("\n".join(resultados))
            
        doc.close()
        return "\n".join(texto_acumulado)
