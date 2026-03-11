import cv2
import numpy as np
from PIL import Image
import logging
import io
import base64

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """
    Clean image preprocessing for receipts - Pure white background
    """
    
    def __init__(self):
        self.target_width = 1200
        
    def preprocess(self, image_data):
        """
        Clean image with pure white background
        """
        try:
            # Convert base64 to image
            if isinstance(image_data, str) and 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("❌ Could not decode image")
                return None
                
            logger.info("🔧 Cleaning image for pure white background...")
            
            # STEP 1: Resize if too small
            height, width = image.shape[:2]
            if width < self.target_width:
                scale = self.target_width / width
                new_width = self.target_width
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), 
                                 interpolation=cv2.INTER_CUBIC)
                logger.info(f"   📏 Resized: {width}x{height} → {new_width}x{new_height}")
            
            # STEP 2: Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # STEP 3: Apply Gaussian blur to remove noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # STEP 4: Adaptive thresholding for clean black/white
            binary = cv2.adaptiveThreshold(
                blurred, 
                255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                15,  # Block size
                5    # Constant subtracted from mean
            )
            
            # STEP 5: Remove small black specks from white background
            kernel = np.ones((2,2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # STEP 6: Remove small white holes in text
            closed = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
            
            # STEP 7: Convert back to BGR
            result = cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)
            
            logger.info("✅ Pure black & white image created")
            
            # Convert back to base64
            _, buffer = cv2.imencode('.jpg', result, [cv2.IMWRITE_JPEG_QUALITY, 100])
            enhanced_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return enhanced_base64
            
        except Exception as e:
            logger.error(f"❌ Preprocessing failed: {e}")
            return None
    
    def quick_assessment(self, image_data):
        """
        Quickly assess if image needs preprocessing
        """
        try:
            # Decode image
            if isinstance(image_data, str) and 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {'needs_preprocessing': True, 'reason': 'Invalid image'}
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = image.shape[:2]
            
            # Quality checks
            needs_preprocessing = False
            reasons = []
            
            # Check 1: Resolution too low?
            if width < 800:
                needs_preprocessing = True
                reasons.append(f"low resolution ({width}x{height})")
            
            # Check 2: Too blurry?
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 50:
                needs_preprocessing = True
                reasons.append(f"blurry (score: {laplacian_var:.1f})")
            
            # Check 3: Poor contrast?
            contrast = gray.std()
            if contrast < 30:
                needs_preprocessing = True
                reasons.append(f"low contrast (std: {contrast:.1f})")
            
            # Check 4: Too dark?
            brightness = gray.mean()
            if brightness < 50 or brightness > 200:
                needs_preprocessing = True
                reasons.append(f"poor brightness ({brightness:.1f})")
            
            return {
                'needs_preprocessing': needs_preprocessing,
                'reasons': ', '.join(reasons) if reasons else 'good quality',
                'resolution': f"{width}x{height}",
                'sharpness': round(laplacian_var, 1),
                'contrast': round(contrast, 1),
                'brightness': round(brightness, 1)
            }
            
        except Exception as e:
            logger.error(f"Assessment error: {e}")
            return {'needs_preprocessing': True, 'reason': 'Assessment failed'}