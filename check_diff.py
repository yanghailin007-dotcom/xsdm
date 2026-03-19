import re

with open('web/templates/phase-two-generation-backup.html', 'r', encoding='utf-8', errors='ignore') as f:
    backup = f.read()

with open('web/templates/phase-two-generation.html', 'r', encoding='utf-8', errors='ignore') as f:
    current = f.read()

# 检查 project-select-card
print("=== project-select-card ===")
print(f"Backup: {'project-select-card' in backup}")
print(f"Current: {'project-select-card' in current}")

# 检查 projects-list 部分
print("\n=== projects-list content ===")
if 'id="projects-list"' in backup:
    print("Backup has projects-list")
else:
    print("Backup missing projects-list")
    
if 'id="projects-list"' in current:
    print("Current has projects-list")
else:
    print("Current missing projects-list")

# 检查 onclick="selectProject
print("\n=== selectProject onclick ===")
backup_matches = backup.count('onclick="selectProject')
current_matches = current.count('onclick="selectProject')
print(f"Backup: {backup_matches} occurrences")
print(f"Current: {current_matches} occurrences")
