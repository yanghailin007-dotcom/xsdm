# PyInstaller hook for requests
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('requests')

# 确保包含这些隐藏导入
hiddenimports += [
    'requests',
    'requests.api',
    'requests.sessions',
    'requests.adapters',
    'requests.models',
    'requests.auth',
    'requests.cookies',
    'requests.structures',
    'requests.utils',
    'requests.hooks',
    'requests.exceptions',
    'requests.compat',
    'urllib3',
    'urllib3.util',
    'urllib3.util.ssl_',
    'urllib3.util.url',
    'urllib3.util.timeout',
    'urllib3.util.retry',
    'urllib3.connection',
    'urllib3.connectionpool',
    'urllib3.poolmanager',
    'urllib3.response',
    'urllib3.exceptions',
    'urllib3.fields',
    'urllib3.filepost',
    'charset_normalizer',
    'idna',
    'certifi',
]
