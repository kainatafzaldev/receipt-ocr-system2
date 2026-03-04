# document_scanner.py - CamScanner-like document preprocessing with magnification and layout preservation
import cv2
import numpy as np
import imutils
import base64
import os
import logging
import traceback

logger = logging.getLogger(__name__)

class DocumentScanner:
    """
    Document scanner that automatically detects, crops, and enhances documents
    Includes magnification for small text and layout preservation for column structure
    """
    
    def base64_to_cv2(self, base64_string):
        """Convert base64 image to OpenCV format with better error handling"""
        try:
            logger.info(f"🔍 Converting base64 to image...")
            
            # Handle different base64 formats
            if 'base64,' in base64_string:
                base64_string = base64_string.split('base64,')[1]
            elif ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64 to bytes
            img_bytes = base64.b64decode(base64_string)
            logger.info(f"📦 Decoded {len(img_bytes)} bytes")
            
            # Convert to numpy array
            nparr = np.frombuffer(img_bytes, np.uint8)
            
            # Decode to OpenCV image
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("❌ cv2.imdecode returned None")
                return None
            
            logger.info(f"✅ Successfully loaded image: {img.shape}")
            return img
            
        except Exception as e:
            logger.error(f"❌ Error in base64_to_cv2: {e}")
            traceback.print_exc()
            return None
    
    def cv2_to_base64(self, img):
        """Convert OpenCV image to base64 string"""
        try:
            # Encode image to JPEG
            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Convert to base64
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return f"data:image/jpeg;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"❌ Error in cv2_to_base64: {e}")
            return None
    
    def resize_image(self, image, max_height=1200):
        """Resize image if too large while maintaining aspect ratio"""
        h, w = image.shape[:2]
        
        if h > max_height:
            scale = max_height / h
            new_w = int(w * scale)
            new_h = max_height
            resized = cv2.resize(image, (new_w, new_h))
            logger.info(f"📐 Resized from {w}x{h} to {new_w}x{new_h}")
            return resized
        return image
    
    # ============ MAGNIFICATION METHODS ============
    
    def magnify_image(self, image, scale_factor=2.0):
        """
        Magnify/enlarge the image to improve OCR accuracy for small text
        scale_factor: 1.5 = 150% larger, 2.0 = 200% larger, etc.
        """
        try:
            height, width = image.shape[:2]
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            # Use different interpolation methods based on scale
            if scale_factor > 2:
                # For large scaling, use Lanczos for better quality
                magnified = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            else:
                # For moderate scaling, use cubic interpolation
                magnified = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            logger.info(f"🔍 Magnified image from {width}x{height} to {new_width}x{new_height} ({scale_factor}x)")
            return magnified
        except Exception as e:
            logger.error(f"❌ Error magnifying image: {e}")
            return image
    
    def auto_detect_and_magnify(self, image):
        """
        Automatically detect if image needs magnification based on image size and text density
        """
        try:
            height, width = image.shape[:2]
            
            # Check if image is small (likely to have small text)
            if height < 800 or width < 600:
                # Small image - needs more magnification
                scale = 2.0
                logger.info(f"🔍 Small image detected ({width}x{height}), using {scale}x magnification")
                return self.magnify_image(image, scale)
            
            # Convert to grayscale for text density estimation
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Use edge detection to estimate text density
            edges = cv2.Canny(gray, 50, 150)
            
            # Calculate text area ratio
            text_pixels = np.count_nonzero(edges)
            total_pixels = edges.shape[0] * edges.shape[1]
            text_ratio = text_pixels / total_pixels
            
            logger.info(f"📊 Text density ratio: {text_ratio:.4f}")
            
            # Decide magnification factor based on text density
            if text_ratio > 0.15:
                # Dense text - might be small, magnify more
                scale = 1.8
                logger.info(f"🔍 High text density detected, using {scale}x magnification")
                return self.magnify_image(image, scale)
            elif text_ratio > 0.08:
                # Medium density - moderate magnification
                scale = 1.5
                logger.info(f"🔍 Medium text density detected, using {scale}x magnification")
                return self.magnify_image(image, scale)
            else:
                # Low density - text might already be large enough
                logger.info(f"✅ Text appears large enough, no magnification needed")
                return image
            
        except Exception as e:
            logger.error(f"❌ Error in auto magnify: {e}")
            return image
    
    def enhance_for_small_text(self, image):
        """
        Special enhancement for receipts with small text
        Combines magnification with sharpening
        """
        try:
            # Step 1: Magnify the image
            magnified = self.magnify_image(image, scale_factor=1.8)
            
            # Step 2: Convert to grayscale
            if len(magnified.shape) == 3:
                gray = cv2.cvtColor(magnified, cv2.COLOR_BGR2GRAY)
            else:
                gray = magnified
            
            # Step 3: Apply sharpening kernel for better text definition
            kernel = np.array([[-1,-1,-1],
                               [-1, 9,-1],
                               [-1,-1,-1]])
            sharpened = cv2.filter2D(gray, -1, kernel)
            
            # Step 4: Apply CLAHE for better contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(sharpened)
            
            logger.info(f"✨ Applied small text enhancement")
            
            # Convert back to BGR for consistency
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            return enhanced_bgr
            
        except Exception as e:
            logger.error(f"❌ Error in small text enhancement: {e}")
            return image
    
    # ============ NEW: LAYOUT PRESERVATION METHODS ============
    
    def detect_columns(self, image):
        """
        Detect column structure in receipt
        Returns vertical line positions
        """
        try:
            # Convert to binary if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Use vertical line detection to find column boundaries
            edges = cv2.Canny(gray, 50, 150)
            
            # Detect vertical lines
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
            vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, vertical_kernel)
            
            # Find column boundaries
            h_projection = np.sum(vertical_lines, axis=0)
            threshold = np.max(h_projection) * 0.3
            
            column_boundaries = []
            in_column = False
            start = 0
            
            for x, val in enumerate(h_projection):
                if val > threshold and not in_column:
                    in_column = True
                    start = x
                elif val <= threshold and in_column:
                    in_column = False
                    if x - start > 20:  # Minimum column width
                        column_boundaries.append((start, x))
            
            if column_boundaries:
                logger.info(f"📊 Detected {len(column_boundaries)} columns")
            
            return column_boundaries
            
        except Exception as e:
            logger.error(f"❌ Error detecting columns: {e}")
            return []
    
    def preserve_white_space(self, image):
        """
        Ensure whitespace between columns is preserved
        """
        try:
            # Convert to binary
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
            
            # Detect columns
            columns = self.detect_columns(binary)
            
            if columns:
                # Create a mask to protect column boundaries
                mask = np.ones_like(gray) * 255
                
                for start, end in columns:
                    # Add a small buffer to preserve column spacing
                    buffer = 5
                    cv2.rectangle(mask, 
                                 (max(0, start - buffer), 0), 
                                 (min(gray.shape[1], end + buffer), gray.shape[0]), 
                                 0, -1)
                
                # Apply gentle sharpening only within column areas
                sharpened = cv2.filter2D(gray, -1, np.array([[0,-1,0],[-1,5,-1],[0,-1,0]]))
                
                # Combine: keep original in column boundaries, enhanced elsewhere
                result = np.where(mask == 0, gray, sharpened)
                
                logger.info(f"✨ Preserved whitespace between columns")
                return result
            else:
                return gray
                
        except Exception as e:
            logger.error(f"❌ Error preserving whitespace: {e}")
            return image
    
    def enhance_for_layout_preservation(self, image):
        """
        Enhance image while preserving column structure and spacing
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Step 1: Gentle denoising (preserves edges)
            denoised = cv2.fastNlMeansDenoising(gray, None, 5, 7, 15)
            
            # Step 2: Adaptive thresholding that preserves structure
            # Using larger block size to maintain column alignment
            threshold = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 15, 5  # Larger block size = better layout preservation
            )
            
            # Step 3: Light morphological operation to connect broken text
            # BUT preserve gaps between columns
            kernel = np.ones((1, 1), np.uint8)  # Minimal kernel to avoid merging columns
            cleaned = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
            
            logger.info(f"📐 Layout-preserving enhancement applied")
            return cleaned
            
        except Exception as e:
            logger.error(f"❌ Error in layout enhancement: {e}")
            return image
    
    def enhance_for_ocr(self, image):
        """
        Enhance image specifically for OCR while preserving layout
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Step 1: Gentle denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 7, 7, 15)
            
            # Step 2: Preserve whitespace between columns
            with_spacing = self.preserve_white_space(denoised)
            
            # Step 3: Adaptive threshold with care for layout
            # Using different block sizes for different regions
            threshold = cv2.adaptiveThreshold(
                with_spacing, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 13, 4
            )
            
            # Step 4: Remove small noise but keep text connected
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
            
            # Step 5: Slight dilation to make text thicker
            dilate_kernel = np.ones((1, 1), np.uint8)
            dilated = cv2.dilate(cleaned, dilate_kernel, iterations=1)
            
            logger.info(f"✨ Enhanced for OCR with layout preservation")
            return dilated
            
        except Exception as e:
            logger.error(f"❌ Error in OCR enhancement: {e}")
            return image
    
    def order_points(self, pts):
        """Order points in consistent order: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sum and diff to find corners
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left
        rect[2] = pts[np.argmax(s)]  # bottom-right
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        
        return rect
    
    def scan_document(self, image):
        """
        Main scanning function - detects document, corrects perspective, enhances
        Returns scanned and enhanced document image
        """
        try:
            original = image.copy()
            h, w = original.shape[:2]
            
            # Step 1: Resize for processing (max height 500)
            scale = 500.0 / h
            new_w = int(w * scale)
            resized = cv2.resize(original, (new_w, 500))
            ratio = h / 500.0
            
            logger.info(f"📐 Resized to {new_w}x500 for processing")
            
            # Step 2: Convert to grayscale and blur
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Step 3: Edge detection
            edged = cv2.Canny(blurred, 75, 200)
            
            # Step 4: Find contours
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            
            # Step 5: Find document contour (largest quadrilateral)
            screen_contour = None
            for contour in contours:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                if len(approx) == 4:
                    screen_contour = approx
                    logger.info(f"✅ Found document contour with 4 points")
                    break
            
            # Step 6: If document found, apply perspective transform
            if screen_contour is not None:
                # Scale points back to original image size
                screen_contour = screen_contour.reshape(4, 2) * ratio
                
                # Order points
                rect = self.order_points(screen_contour)
                (tl, tr, br, bl) = rect
                
                # Calculate max width and height
                width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                max_width = max(int(width_a), int(width_b))
                
                height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                max_height = max(int(height_a), int(height_b))
                
                # Destination points for transform
                dst = np.array([
                    [0, 0],
                    [max_width - 1, 0],
                    [max_width - 1, max_height - 1],
                    [0, max_height - 1]
                ], dtype="float32")
                
                # Apply perspective transform
                M = cv2.getPerspectiveTransform(rect, dst)
                scanned = cv2.warpPerspective(original, M, (max_width, max_height))
                logger.info(f"🔄 Applied perspective correction")
                
                return scanned
            else:
                logger.warning("⚠️ No document contour found, using original image")
                return original
                
        except Exception as e:
            logger.error(f"❌ Error in scan_document: {e}")
            traceback.print_exc()
            return image
    
    def process_image(self, image_input):
        """
        Main entry point - processes image from either path or base64
        Returns enhanced base64 image with magnification and layout preservation
        """
        try:
            logger.info("🚀 Starting image processing with layout preservation...")
            
            # Handle different input types
            if isinstance(image_input, str):
                if image_input.startswith('data:image') or 'base64' in image_input:
                    # Base64 input
                    logger.info("📥 Processing base64 image")
                    img = self.base64_to_cv2(image_input)
                else:
                    # File path input
                    logger.info(f"📥 Processing image from path: {image_input}")
                    img = cv2.imread(image_input)
                    if img is None:
                        logger.error(f"❌ Could not read image from path: {image_input}")
                        return None
            else:
                # Assume it's already a numpy array
                logger.info("📥 Processing numpy array image")
                img = image_input
            
            if img is None:
                logger.error("❌ Failed to load image")
                return None
            
            logger.info(f"📷 Original image size: {img.shape}")
            
            # Step 1: AUTO MAGNIFY FOR SMALL TEXT
            img = self.auto_detect_and_magnify(img)
            
            # Step 2: Resize if too large (after magnification)
            img = self.resize_image(img, max_height=2000)
            
            # Step 3: Scan document (crop background)
            scanned = self.scan_document(img)
            
            # Step 4: Enhance for OCR with layout preservation
            enhanced = self.enhance_for_ocr(scanned)
            
            # Additional enhancement for small text if needed
            if img.shape[0] < 1000:  # If image is still small after magnification
                enhanced = self.enhance_for_small_text(enhanced)
            
            # Convert back to color for base64 (if grayscale)
            if len(enhanced.shape) == 2:
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            # Convert back to base64
            result_base64 = self.cv2_to_base64(enhanced)
            
            if result_base64:
                logger.info(f"✅ Document scanning complete with layout preservation")
                return result_base64
            else:
                logger.error("❌ Failed to convert result to base64")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error processing image: {e}")
            traceback.print_exc()
            return None