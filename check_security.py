#!/usr/bin/env python3
import os
import secrets
from pathlib import Path

print('=' * 60)
print('Security Check Report')
print('=' * 60)

# Check hardcoded secrets
web_config = Path('web/web_config.py')
if web_config.exists():
    content = web_config.read_text(encoding='utf-8')
    if 'your-secret-key-here' in content:
        print('[CRITICAL] Hardcoded SECRET_KEY found in web_config.py')
    else:
        print('[OK] SECRET_KEY looks good')

# Check test user
auth_file = Path('web/auth.py')
if auth_file.exists():
    content = auth_file.read_text(encoding='utf-8')
    if "username.lower() == 'test':" in content and 'return True' in content:
        print('[CRITICAL] Test user backdoor found in auth.py')
    else:
        print('[OK] Test user backdoor not found')

# Check password hash
user_model = Path('web/models/user_model.py')
if user_model.exists():
    content = user_model.read_text(encoding='utf-8')
    if 'sha256(password.encode())' in content:
        print('[WARNING] SHA256 password hashing (should use bcrypt)')
    else:
        print('[OK] Password hashing looks good')

# Check internal API key
points_api = Path('web/api/points_api.py')
if points_api.exists():
    content = points_api.read_text(encoding='utf-8')
    if 'your-internal-api-key' in content:
        print('[CRITICAL] Hardcoded internal API key found in points_api.py')
    else:
        print('[OK] Internal API key looks good')

print('=' * 60)
print('Generating secure keys for .env file:')
print('=' * 60)
print(f"FLASK_SECRET_KEY={secrets.token_urlsafe(32)}")
print(f"INTERNAL_API_KEY={secrets.token_urlsafe(32)}")
print('=' * 60)
