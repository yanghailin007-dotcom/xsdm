#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Writing Style System Self Check
Simple version without unicode characters
"""

import os
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent

def check_files():
    """Check if all required files exist"""
    print("\n" + "="*60)
    print("CHECKING FILE STRUCTURE")
    print("="*60)
    
    files = [
        ("web/models/writing_style_model.py", "Data Model"),
        ("web/api/writing_style_api.py", "API Endpoints"),
        ("web/routes/writing_style_routes.py", "Page Routes"),
        ("web/templates/components/writing-style-selector.html", "Selector Component"),
        ("web/templates/pages/v2/writing-style-library.html", "Library Page"),
    ]
    
    all_ok = True
    for file_path, desc in files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"[OK] {desc}: {file_path}")
        else:
            print(f"[MISSING] {desc}: {file_path}")
            all_ok = False
    
    return all_ok

def check_blueprint():
    """Check if blueprint is registered"""
    print("\n" + "="*60)
    print("CHECKING BLUEPRINT REGISTRATION")
    print("="*60)
    
    server_file = project_root / "web" / "web_server_refactored.py"
    if not server_file.exists():
        print("[ERROR] web_server_refactored.py not found")
        return False
    
    content = server_file.read_text(encoding='utf-8')
    
    checks = [
        ("writing_style_api", "Writing Style API"),
        ("writing_style_routes", "Writing Style Routes"),
    ]
    
    all_ok = True
    for keyword, desc in checks:
        if keyword in content:
            print(f"[OK] {desc} is registered")
        else:
            print(f"[MISSING] {desc} is not registered")
            all_ok = False
    
    return all_ok

def check_data_dir():
    """Check data directory"""
    print("\n" + "="*60)
    print("CHECKING DATA DIRECTORY")
    print("="*60)
    
    data_dir = project_root / "data" / "writing_styles"
    preset_dir = data_dir / "presets"
    
    if not data_dir.exists():
        print(f"[INFO] Data directory will be created on first run: {data_dir}")
        return True
    
    print(f"[OK] Data directory exists: {data_dir}")
    
    if preset_dir.exists():
        files = list(preset_dir.glob("*.json"))
        print(f"[OK] Preset directory has {len(files)} style files")
        
        # Check for fanqie style
        fanqie = preset_dir / "fanqie_light_fast_v1.json"
        if fanqie.exists():
            print("[OK] Fanqie Light Fast style exists")
        else:
            print("[INFO] Fanqie style will be created on first run")
    else:
        print("[INFO] Preset directory will be created on first run")
    
    return True

def test_model():
    """Test if model can be imported"""
    print("\n" + "="*60)
    print("TESTING DATA MODEL")
    print("="*60)
    
    try:
        sys.path.insert(0, str(project_root))
        from web.models.writing_style_model import get_writing_style_model
        
        model = get_writing_style_model()
        print("[OK] WritingStyleModel can be initialized")
        
        presets = model.get_all_presets()
        print(f"[OK] Loaded {len(presets)} preset styles")
        
        if presets:
            print(f"[OK] First style: {presets[0].get('style_name', 'Unknown')}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Model test failed: {e}")
        return False

def generate_report(results):
    """Generate report"""
    print("\n" + "="*60)
    print("SUMMARY REPORT")
    print("="*60)
    
    total = len([r for r in results if r])
    
    print(f"\nTotal Checks: {len(results)}")
    print(f"Passed: {total}")
    print(f"Failed: {len(results) - total}")
    
    report_file = project_root / "tests" / "writing_style_check_report.json"
    with open(report_file, 'w') as f:
        json.dump({
            "total": len(results),
            "passed": total,
            "failed": len(results) - total,
            "all_passed": all(results)
        }, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    return all(results)

def main():
    """Main function"""
    print("="*60)
    print("WRITING STYLE SYSTEM SELF CHECK")
    print("="*60)
    
    results = []
    
    results.append(check_files())
    results.append(check_blueprint())
    results.append(check_data_dir())
    results.append(test_model())
    
    success = generate_report(results)
    
    print("\n" + "="*60)
    if success:
        print("ALL CHECKS PASSED!")
        print("Writing Style System is ready.")
    else:
        print("SOME CHECKS FAILED!")
        print("Please fix the issues above.")
    print("="*60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
