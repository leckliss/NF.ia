from paddleocr import PaddleOCR
import os
import logging

# Suppress PaddleOCR debug logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

class OCREngine:
    def __init__(self):
        # Instantiate PaddleOCR with requested parameters:
        # use_angle_cls=True (detect rotation/angle)
        # lang='pt' (Portuguese model)
        print("Initializing PaddleOCR (this may take a moment)...")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='pt', show_log=False)

    def extract_text(self, file_path):
        """
        Extracts text from a given PDF or Image file using PaddleOCR.
        Returns a single concatenated string.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Running OCR on {file_path}...")
        
        # paddleocr's ocr method handles PDF paths natively in newer versions,
        # but sometimes requires conversion. Assuming paddleocr supports the file.
        # It typically returns a list of results.
        result = self.ocr.ocr(file_path, cls=True)
        
        extracted_text = []
        
        # PaddleOCR result structure: list of pages -> list of lines -> [box, (text, score)]
        # Usually result is a list of lists.
        if result:
            for page in result:
                if page:
                    for line in page:
                        # line structure: [ [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', 0.99) ]
                        text_content = line[1][0]
                        extracted_text.append(text_content)
        
        full_text = "\n".join(extracted_text)
        return full_text
