import cv2
import numpy as np
from PIL import Image
import logging
import io
import base64

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """
    Smart image preprocessing for receipts
    - Handles faint/small text better
    - Uses gentle enhancement instead of aggressive thresholding
    """
    
    def __init__(self):
        self.target_width = 1600  # Increased from 1200 for better OCR
        
    def preprocess(self, image_data):
        """
        Smart enhancement that preserves faint text
        """
        try:
            # Decode base64
            if isinstance(image_data, str) and 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("❌ Could not decode image")
                return None
            
            height, width = image.shape[:2]
            logger.info(f"🔧 Starting preprocessing: {width}x{height}")
            
            # ── STEP 1: Upscale small images ──────────────────────────
            # Small receipts need 2x-3x upscaling for VLM to read them
            if width < self.target_width:
                scale = self.target_width / width
                new_width = self.target_width
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height),
                                   interpolation=cv2.INTER_CUBIC)
                logger.info(f"   📏 Upscaled: {width}x{height} → {new_width}x{new_height}")
            
            # ── STEP 2: Auto-rotate if tilted ─────────────────────────
            image = self._auto_deskew(image)
            
            # ── STEP 3: Convert to grayscale ──────────────────────────
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # ── STEP 4: Denoise (removes camera grain) ────────────────
            denoised = cv2.fastNlMeansDenoising(gray, h=10, 
                                                 templateWindowSize=7,
                                                 searchWindowSize=21)
            
            # ── STEP 5: CLAHE contrast enhancement ────────────────────
            # This is the KEY fix - makes faint text visible
            # Works on LOCAL regions so even faded parts get enhanced
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # ── STEP 6: Sharpen text edges ────────────────────────────
            sharpening_kernel = np.array([
                [ 0, -1,  0],
                [-1,  5, -1],
                [ 0, -1,  0]
            ])
            sharpened = cv2.filter2D(enhanced, -1, sharpening_kernel)
            
            # ── STEP 7: Smart thresholding based on image quality ─────
            # Check brightness to decide which method to use
            brightness = gray.mean()
            blurriness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if blurriness < 30:
                # Very blurry → use gentler adaptive threshold
                logger.info("   🔵 Using gentle threshold (blurry image)")
                binary = cv2.adaptiveThreshold(
                    sharpened, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    21,   # Larger block = more context per region
                    8     # Higher constant = more tolerant of faint text
                )
            elif brightness < 80:
                # Dark image → use OTSU which finds best threshold automatically
                logger.info("   🟡 Using OTSU threshold (dark image)")
                _, binary = cv2.threshold(
                    sharpened, 0, 255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
            else:
                # Normal image → standard adaptive threshold
                logger.info("   🟢 Using standard threshold (normal image)")
                binary = cv2.adaptiveThreshold(
                    sharpened, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    15,
                    5
                )
            
            # ── STEP 8: Light cleanup (very small kernel to avoid ─────
            # destroying thin characters like . , ' 1 i l)
            kernel_small = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)
            
            # ── STEP 9: Convert back to BGR for encoding ──────────────
            result = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
            
            logger.info("✅ Preprocessing complete")
            
            # Encode back to base64 (use PNG for lossless quality)
            _, buffer = cv2.imencode('.png', result)
            enhanced_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return enhanced_base64
            
        except Exception as e:
            logger.error(f"❌ Preprocessing failed: {e}")
            return None

    def _auto_deskew(self, image):
        """
        Auto-rotate tilted receipt images
        Receipts photographed at an angle lose text alignment
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.bitwise_not(gray)
            thresh = cv2.threshold(gray, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            coords = np.column_stack(np.where(thresh > 0))
            
            if len(coords) < 100:
                return image  # Not enough points to detect angle
            
            angle = cv2.minAreaRect(coords)[-1]
            
            # Normalize angle
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # Only rotate if meaningfully tilted (ignore tiny angles)
            if abs(angle) < 0.5 or abs(angle) > 45:
                return image
            
            logger.info(f"   📐 Deskewing: {angle:.1f}°")
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h),
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
            return rotated
            
        except Exception as e:
            logger.warning(f"⚠️ Deskew failed, using original: {e}")
            return image

    def quick_assessment(self, image_data):
        """
        Assess image quality — decides if preprocessing is needed
        """
        try:
            if isinstance(image_data, str) and 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {'needs_preprocessing': True, 'reason': 'Invalid image'}
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = image.shape[:2]
            
            needs_preprocessing = False
            reasons = []
            
            # Check 1: Low resolution
            if width < 1000:
                needs_preprocessing = True
                reasons.append(f"low resolution ({width}x{height})")
            
            # Check 2: Blurry
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 80:  # Raised from 50 — catches more blurry images
                needs_preprocessing = True
                reasons.append(f"blurry (score: {laplacian_var:.1f})")
            
            # Check 3: Low contrast
            contrast = gray.std()
            if contrast < 40:  # Raised from 30
                needs_preprocessing = True
                reasons.append(f"low contrast (std: {contrast:.1f})")
            
            # Check 4: Bad brightness
            brightness = gray.mean()
            if brightness < 60 or brightness > 210:
                needs_preprocessing = True
                reasons.append(f"poor brightness ({brightness:.1f})")

            # Check 5: NEW — detect if image is tilted
            try:
                edges = cv2.Canny(gray, 50, 150)
                lines = cv2.HoughLinesP(edges, 1, np.pi/180, 
                                         threshold=100, minLineLength=100, 
                                         maxLineGap=10)
                if lines is not None:
                    angles = []
                    for line in lines[:20]:
                        x1, y1, x2, y2 = line[0]
                        if x2 != x1:
                            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                            angles.append(angle)
                    if angles:
                        median_angle = np.median(angles)
                        if abs(median_angle) > 2:
                            needs_preprocessing = True
                            reasons.append(f"tilted ({median_angle:.1f}°)")
            except:
                pass
            
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