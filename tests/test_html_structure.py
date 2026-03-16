# -*- coding: utf-8 -*-
"""
Test: Check HTML structure for first-time hint
"""
from pathlib import Path
import re

def test_html_structure():
    """Test that first-time hint is in HTML template"""
    
    template_path = Path(__file__).parent.parent / 'web' / 'templates' / 'phase-two-generation.html'
    
    if not template_path.exists():
        print(f"[FAIL] Template not found: {template_path}")
        return False
    
    html_content = template_path.read_text(encoding='utf-8')
    
    # Check for first-time-hint element
    if 'id="first-time-hint"' in html_content:
        print("[PASS] first-time-hint element found in HTML")
    else:
        print("[FAIL] first-time-hint element NOT found in HTML")
        return False
    
    # Check for key content
    key_texts = ['从左侧选择项目开始', '项目列表', '设计蓝图']
    for text in key_texts:
        if text in html_content:
            print(f"[PASS] Found text: '{text}'")
        else:
            print(f"[WARN] Text not found: '{text}'")
    
    # Check for animation
    if 'pulse-hint' in html_content:
        print("[PASS] pulse-hint animation found")
    else:
        print("[WARN] pulse-hint animation not found")
    
    # Check structure: hint should be inside project-details
    project_details_pattern = r'<div id="project-details">(.*?)<div id="first-time-hint"'
    match = re.search(project_details_pattern, html_content, re.DOTALL)
    if match:
        print("[PASS] first-time-hint is inside project-details")
    else:
        print("[WARN] Cannot confirm first-time-hint is inside project-details")
    
    # Check if displayProjectDetails replaces innerHTML
    js_path = Path(__file__).parent.parent / 'static' / 'js' / 'phase-two-generation.js'
    if js_path.exists():
        js_content = js_path.read_text(encoding='utf-8')
        
        # Check if innerHTML is set
        if 'detailsDiv.innerHTML = html' in js_content:
            print("[INFO] JS: displayProjectDetails sets innerHTML (will replace hint)")
        
        # Check auto-select logic
        if 'checkAndAutoSelectProject' in js_content:
            print("[INFO] JS: checkAndAutoSelectProject exists (may auto-select on load)")
    
    return True

if __name__ == '__main__':
    result = test_html_structure()
    print(f"\n[RESULT] {'PASSED' if result else 'FAILED'}")
    exit(0 if result else 1)
