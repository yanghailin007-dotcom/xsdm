#!/usr/bin/env python3
"""
项目信息文件完整性检查工具
"""
import json
import sys
from pathlib import Path

def check_project_integrity(project_file: Path) -> dict:
    """检查单个项目文件的完整性"""
    issues = []
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"file": str(project_file), "status": "ERROR", "issues": [str(e)]}
    
    novel_info = data.get("novel_info", {})
    
    # 检查关键字段
    if not novel_info.get("title"):
        issues.append("MISSING: novel_info.title")
    if not novel_info.get("synopsis"):
        issues.append("MISSING: novel_info.synopsis")
    if not novel_info.get("creative_seed"):
        issues.append("MISSING: novel_info.creative_seed")
    if not novel_info.get("selected_plan"):
        issues.append("MISSING: novel_info.selected_plan")
    
    # 检查 selected_plan
    selected_plan = novel_info.get("selected_plan", {})
    if selected_plan:
        if not selected_plan.get("title"):
            issues.append("MISSING: selected_plan.title")
        if not selected_plan.get("synopsis"):
            issues.append("MISSING: selected_plan.synopsis")
        if not selected_plan.get("tags", {}).get("target_audience"):
            issues.append("MISSING: selected_plan.tags.target_audience")
        if not selected_plan.get("suggestions", {}).get("name"):
            issues.append("MISSING: selected_plan.suggestions.name (主角名)")
    
    status = "OK" if not issues else "ISSUES"
    return {"file": str(project_file), "status": status, "issues": issues}

def main():
    projects_dir = Path("小说项目")
    
    if not projects_dir.exists():
        print("ERROR: 小说项目目录不存在")
        sys.exit(1)
    
    # 查找所有项目信息文件
    project_files = list(projects_dir.rglob("*_项目信息.json"))
    project_files.extend(projects_dir.rglob("项目信息.json"))
    
    print(f"Found {len(project_files)} project files\n")
    
    has_issues = False
    for pf in sorted(project_files):
        result = check_project_integrity(pf)
        print(f"File: {result['file']}")
        print(f"Status: {result['status']}")
        
        for issue in result['issues']:
            print(f"  - {issue}")
        
        if result['issues']:
            has_issues = True
        print()
    
    if has_issues:
        print("WARNING: Some projects have missing fields")
    else:
        print("OK: All project files are complete")

if __name__ == "__main__":
    main()
