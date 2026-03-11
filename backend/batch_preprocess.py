import os
import cv2
import numpy as np
from PIL import Image
import base64
import logging
from image_preprocessor import ImagePreprocessor
from pathlib import Path
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class BatchPreprocessor:
    def __init__(self, input_folder="images", output_folder="preprocessed"):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.preprocessor = ImagePreprocessor()
        
        # Create output folders
        self.processed_folder = os.path.join(output_folder, "processed")
        self.comparison_folder = os.path.join(output_folder, "comparison")
        self.report_file = os.path.join(output_folder, "processing_report.txt")
        
        os.makedirs(self.processed_folder, exist_ok=True)
        os.makedirs(self.comparison_folder, exist_ok=True)
    
    def get_all_images(self):
        """Get all image files from input folder"""
        extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        images = []
        
        for ext in extensions:
            images.extend(Path(self.input_folder).glob(f'*{ext}'))
            images.extend(Path(self.input_folder).glob(f'*{ext.upper()}'))
        
        return sorted(images)
    
    def create_comparison_image(self, original_path, processed_path, output_path):
        """Create side-by-side comparison of original and processed"""
        original = cv2.imread(str(original_path))
        processed = cv2.imread(processed_path)
        
        if original is None or processed is None:
            return
        
        # Resize both to same height for comparison
        height = max(original.shape[0], processed.shape[0])
        width_orig = int(original.shape[1] * height / original.shape[0])
        width_proc = int(processed.shape[1] * height / processed.shape[0])
        
        original_resized = cv2.resize(original, (width_orig, height))
        processed_resized = cv2.resize(processed, (width_proc, height))
        
        # Create side-by-side image
        comparison = np.hstack((original_resized, processed_resized))
        
        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(comparison, 'ORIGINAL', (10, 30), font, 1, (0, 255, 0), 2)
        cv2.putText(comparison, 'PROCESSED', (width_orig + 10, 30), font, 1, (0, 255, 0), 2)
        
        cv2.imwrite(output_path, comparison)
    
    def process_single_image(self, image_path):
        """Process a single image and return metrics"""
        try:
            # Read image
            with open(image_path, 'rb') as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Get assessment
            assessment = self.preprocessor.quick_assessment(base64_image)
            
            # Apply preprocessing
            processed_base64 = self.preprocessor.preprocess(base64_image)
            
            if processed_base64:
                # Save processed image
                processed_filename = f"processed_{image_path.name}"
                processed_path = os.path.join(self.processed_folder, processed_filename)
                
                processed_data = base64.b64decode(processed_base64)
                with open(processed_path, 'wb') as f:
                    f.write(processed_data)
                
                # Create comparison image
                comparison_filename = f"compare_{image_path.name}"
                comparison_path = os.path.join(self.comparison_folder, comparison_filename)
                self.create_comparison_image(image_path, processed_path, comparison_path)
                
                return {
                    'success': True,
                    'filename': image_path.name,
                    'processed_path': processed_path,
                    'comparison_path': comparison_path,
                    'assessment': assessment
                }
            else:
                return {
                    'success': False,
                    'filename': image_path.name,
                    'error': 'Preprocessing failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'filename': image_path.name,
                'error': str(e)
            }
    
    def process_all(self):
        """Process all images in the folder"""
        print("\n" + "="*70)
        print("🖼️ BATCH IMAGE PREPROCESSING")
        print("="*70)
        
        images = self.get_all_images()
        
        if not images:
            print(f"\n❌ No images found in '{self.input_folder}' folder")
            print("Please add some receipt images to process")
            return
        
        print(f"\n📁 Found {len(images)} images to process")
        print(f"📂 Input folder: {self.input_folder}")
        print(f"📂 Output folder: {self.output_folder}")
        print("\n" + "-"*70)
        
        results = []
        successful = 0
        failed = 0
        
        for i, image_path in enumerate(images, 1):
            print(f"\n[{i}/{len(images)}] Processing: {image_path.name}")
            print("-"*50)
            
            result = self.process_single_image(image_path)
            results.append(result)
            
            if result['success']:
                successful += 1
                print(f"✅ SUCCESS: {result['filename']}")
                print(f"   📊 Quality: {result['assessment']['resolution_score']} resolution, "
                      f"{result['assessment']['blur_score']}, {result['assessment']['contrast_score']} contrast")
                print(f"   📄 Processed: {os.path.basename(result['processed_path'])}")
                print(f"   🖼️ Comparison: {os.path.basename(result['comparison_path'])}")
            else:
                failed += 1
                print(f"❌ FAILED: {result['filename']} - {result.get('error', 'Unknown error')}")
        
        # Generate report
        self.generate_report(results, successful, failed)
        
        print("\n" + "="*70)
        print(f"✅ BATCH PROCESSING COMPLETE")
        print(f"   Successful: {successful}/{len(images)}")
        print(f"   Failed: {failed}/{len(images)}")
        print(f"   Check '{self.output_folder}' folder for results")
        print("="*70)
    
    def generate_report(self, results, successful, failed):
        """Generate a detailed report"""
        with open(self.report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("IMAGE PREPROCESSING BATCH REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Total images: {len(results)}\n")
            f.write(f"Successful: {successful}\n")
            f.write(f"Failed: {failed}\n\n")
            
            f.write("-"*70 + "\n")
            f.write("DETAILED RESULTS:\n")
            f.write("-"*70 + "\n\n")
            
            for result in results:
                if result['success']:
                    f.write(f"✅ {result['filename']}\n")
                    f.write(f"   Resolution: {result['assessment']['resolution']} ({result['assessment']['resolution_score']})\n")
                    f.write(f"   Sharpness: {result['assessment']['blur_score']}\n")
                    f.write(f"   Contrast: {result['assessment']['contrast_score']}\n")
                    f.write(f"   Processed: {result['processed_path']}\n")
                    f.write(f"   Comparison: {result['comparison_path']}\n\n")
                else:
                    f.write(f"❌ {result['filename']} - {result.get('error', 'Unknown error')}\n\n")
            
            f.write("="*70 + "\n")

def main():
    # Create batch preprocessor
    batch = BatchPreprocessor(
        input_folder="images",      # Folder with your receipt images
        output_folder="preprocessed" # Folder for processed images
    )
    
    # Process all images
    batch.process_all()
    
    print("\n📊 Quick Access:")
    print("   1. Open 'preprocessed/comparison' folder to see before/after images")
    print("   2. Open 'preprocessed/processed' folder to see only enhanced images")
    print("   3. Read 'preprocessed/processing_report.txt' for detailed report")

if __name__ == "__main__":
    main()