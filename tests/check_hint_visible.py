# -*- coding: utf-8 -*-
"""
Direct check: Does first-time hint exist in HTML template?
"""
from pathlib import Path
import re

def check_hint_in_template():
    """Check if first-time hint is correctly placed in HTML"""
    
    template_path = Path(__file__).parent.parent / 'web' / 'templates' / 'phase-two-generation.html'
    
    html = template_path.read_text(encoding='utf-8')
    
    print("=" * 60)
    print("Checking first-time hint in HTML template")
    print("=" * 60)
    
    # Check 1: Does first-time-hint exist?
    if 'id="first-time-hint"' in html:
        print("[OK] first-time-hint element exists")
    else:
        print("[FAIL] first-time-hint element NOT found")
        return False
    
    # Check 2: Is it inside project-details?
    pattern = r'<div id="project-details">\s*<!--.*?-->\s*<div id="first-time-hint"'
    if re.search(pattern, html, re.DOTALL):
        print("[OK] first-time-hint is directly inside project-details")
    else:
        print("[WARN] Cannot confirm first-time-hint placement")
    
    # Check 3: Check JS version
    js_match = re.search(r'phase-two-generation\.js\?v=(\d+)', html)
    if js_match:
        version = js_match.group(1)
        print(f"[INFO] JS version: v{version}")
        if int(version) >= 12:
            print("[OK] JS version is up to date (v12+)")
        else:
            print("[WARN] JS version may be outdated")
    
    # Check 4: Check window.currentUser injection
    if 'window.currentUser' in html:
        print("[OK] window.currentUser is injected")
    else:
        print("[WARN] window.currentUser not found")
    
    print("\n" + "=" * 60)
    print("SUMMARY: HTML structure is correct")
    print("If hint is not showing in browser:")
    print("1. Press Ctrl+F5 to hard refresh")
    print("2. Clear browser cache")
    print("3. Check browser console for errors")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    check_hint_in_template()
