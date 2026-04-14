import json, pathlib, re

ch_path = pathlib.Path('小说项目/yanghailin/开局被炒，我反手做空百亿妖股/chapters/chapter_001.json')
with open(ch_path, 'rb') as f:
    raw_bytes = f.read()

# Find the 'content' field in raw bytes
m = re.search(b'"content"\s*:\s*"', raw_bytes)
if m:
    start = m.end()
    end = start
    while end < len(raw_bytes):
        if raw_bytes[end] == ord('\\') and end + 1 < len(raw_bytes):
            end += 2
        elif raw_bytes[end] == ord('"'):
            break
        else:
            end += 1
    content_bytes = raw_bytes[start:end]
    print('Content field length:', len(content_bytes))
    print('Newline bytes (0x0a) count:', content_bytes.count(b'\n'))
    print('Escaped newline (0x5c 0x6e) count:', content_bytes.count(b'\\n'))
    print('First 200 bytes:', content_bytes[:200])
else:
    print('content field not found')
