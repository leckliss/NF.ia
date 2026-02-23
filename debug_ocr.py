from paddleocr import PaddleOCR
import inspect
import sys
import traceback
import os

# Try to force disable MKLDNN via env var before importing paddle if possible (though too late maybe)
os.environ["DN_ENABLE_ONEDNN"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

try:
    import paddle
    paddle.set_device('cpu')
except Exception:
    pass

with open("debug_output_v2.txt", "w", encoding="utf-8") as f:
    try:
        f.write("Inspecting PaddleOCR V2...\n")
        # Initialize
        ocr = PaddleOCR(use_angle_cls=False, lang='pt')
        
        f.write(f"Type of ocr object: {type(ocr)}\n")
        
        import numpy as np
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        f.write("\n--- Test Call 1: ocr(img) ---\n")
        try:
            ocr.ocr(img)
            f.write("Call 1 success!\n")
        except Exception as e:
            f.write(f"Call 1 failed: {e}\n")
            f.write(traceback.format_exc())

        f.write("\n--- Test Call 2: ocr(img, cls=False) ---\n")
        try:
            ocr.ocr(img, cls=False)
            f.write("Call 2 success!\n")
        except Exception as e:
            f.write(f"Call 2 failed: {e}\n")
            f.write(traceback.format_exc())
            
        f.write("\n--- Test Call 3: predict(img) ---\n")
        try:
            if hasattr(ocr, 'predict'):
                ocr.predict(img)
                f.write("Call 3 success!\n")
            else:
                f.write("No predict method.\n")
        except Exception as e:
            f.write(f"Call 3 failed: {e}\n")
            f.write(traceback.format_exc())

    except Exception as e:
        f.write(f"Error initializing PaddleOCR: {e}\n")
        f.write(traceback.format_exc())
