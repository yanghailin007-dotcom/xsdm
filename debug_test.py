import re

with open("小说项目/yanghailin/神豪：全县无高铁，我修太空电梯/outline_vol1.md", "r", encoding="utf-8") as f:
    text = f.read()

with open("debug_responses/debug_test_result.txt", "w", encoding="utf-8") as out:
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "第1章" in line and "#" in line:
            out.write(f"Line {i+1}: {repr(line[:40])}\n")
            out.write(f"  starts with '#': {line.startswith('#')}\n")
            out.write(f"  starts with '###': {line.startswith('###')}\n")
            break

    chapter_number = 1
    pattern = re.compile(
        rf'^(#{3,4})\s*第{chapter_number}章[：:\s](.*?)\n(.*?)(?=^\1\s*第\d+章|\Z)',
        re.MULTILINE | re.DOTALL
    )
    m = pattern.search(text)
    out.write(f"\nFull pattern match: {m is not None}\n")

    p2 = re.compile(rf'^#{3,4}\s*第{chapter_number}章', re.MULTILINE)
    m2 = p2.search(text)
    out.write(f"Simple search: {m2 is not None}\n")
    if m2:
        out.write(f"  matched: {repr(m2.group(0))}\n")

    out.write(f"\nFirst 200 chars of file: {repr(text[:200])}\n")
