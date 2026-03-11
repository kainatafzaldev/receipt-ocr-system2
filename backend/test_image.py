import cv2
import base64
import numpy as np
import logging
import os
from image_preprocessor import ImagePreprocessor 

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def run_test(img_path):
    # Check if the file exists in the images subfolder
    if not os.path.exists(img_path):
        print(f"❌ Error: {img_path} not found.")
        print("Looking in: " + os.path.abspath(img_path))
        return

    preprocessor = ImagePreprocessor()
    
    print(f"⚙️ Processing {img_path}...")
    with open(img_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode('utf-8')

    processed_base64 = preprocessor.preprocess(img_base64)

    if processed_base64:
        # Save the result to see if the tilt is gone
        decoded_data = base64.b64decode(processed_base64)
        nparr = np.frombuffer(decoded_data, np.uint8)
        final_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        output_name = "debug_result.jpg"
        cv2.imwrite(output_name, final_img)
        print(f"✅ SUCCESS! Created '{output_name}'")
        print("Open this file to see if the text is now horizontal.")
    else:
        print("❌ FAILED: Preprocessing returned None.")

if __name__ == "__main__":
    # Path updated based on your 'images' folder screenshot
    run_test("images/1006-receipt.jpg")