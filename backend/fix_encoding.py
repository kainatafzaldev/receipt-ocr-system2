"""
ENCODING FIX SCRIPT
Fixes UTF-8 BOM and encoding issues in all Python files
"""

import os
import sys

def fix_file_encoding(filepath):
    """Fix encoding issues in a single file"""
    try:
        # Try to read with different encodings
        content = None
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"  ✅ Successfully read with {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print(f"  ❌ Could not read file with any encoding")
            return False
        
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
            print(f"  ✅ Removed BOM character")
        
        # Write back with UTF-8 (no BOM)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Saved with UTF-8 encoding")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def fix_all_files():
    """Fix all Python files in the project"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = project_root
    project_dir = os.path.dirname(backend_dir)
    
    print("=" * 60)
    print("🔧 ENCODING FIX SCRIPT")
    print("=" * 60)
    print(f"Project root: {project_dir}")
    print(f"Backend dir: {backend_dir}")
    print("=" * 60)
    
    # Files to fix (all Python files)
    files_to_fix = []
    
    # Add main project files
    main_py = os.path.join(backend_dir, 'main.py')
    if os.path.exists(main_py):
        files_to_fix.append(main_py)
    
    # Add all Python files in backend
    for file in os.listdir(backend_dir):
        if file.endswith('.py'):
            files_to_fix.append(os.path.join(backend_dir, file))
    
    # Add root Python files
    for file in os.listdir(project_dir):
        if file.endswith('.py'):
            files_to_fix.append(os.path.join(project_dir, file))
    
    # Remove duplicates
    files_to_fix = list(set(files_to_fix))
    
    print(f"\nFound {len(files_to_fix)} Python files to check:\n")
    
    fixed_count = 0
    error_count = 0
    
    for filepath in files_to_fix:
        filename = os.path.basename(filepath)
        print(f"\n📄 Processing: {filename}")
        
        if fix_file_encoding(filepath):
            fixed_count += 1
        else:
            error_count += 1
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Files fixed: {fixed_count}")
    print(f"❌ Errors: {error_count}")
    print("=" * 60)
    
    return fixed_count, error_count

if __name__ == "__main__":
    fix_all_files()
    print("\n✨ Done! Now try running your project again.")