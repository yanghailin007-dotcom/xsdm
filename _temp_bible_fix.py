with open('web/services/market_driven/bible_reviewer.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        if has_block:
            block_dims = [d["name"] for d in report.get("dimensions", []) if d.get("verdict") == "BLOCK"]
            bible_path_abs = str(bible_path.resolve())
            msg = f"核心设定圣经审稿未通过，BLOCK 维度: {', '.join(block_dims)}。请人工修改 {bible_path_abs} 后重试。"
            logger.error(f"[BibleReviewer] {msg}")
            raise BibleReviewBlockedError(msg, report, report_path)
        
        warn_dims = [d["name"] for d in report.get("dimensions", []) if d.get("verdict") == "WARN"]'''

new = '''        # 废弃 BLOCK 熔断：统一降级为 WARN，让流程继续走到步骤6.5的设定审核
        if has_block:
            block_dims = [d["name"] for d in report.get("dimensions", []) if d.get("verdict") == "BLOCK"]
            for dim in report.get("dimensions", []):
                if dim.get("verdict") == "BLOCK":
                    dim["verdict"] = "WARN"
                    dim["suggestion"] = f"[原BLOCK已降级] {dim.get('suggestion', '')}"
            logger.warning(f"[BibleReviewer] 原BLOCK维度已降级为WARN: {', '.join(block_dims)}")
        
        warn_dims = [d["name"] for d in report.get("dimensions", []) if d.get("verdict") == "WARN"]'''

print('found:', old in content)
if old in content:
    content = content.replace(old, new)
    with open('web/services/market_driven/bible_reviewer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('done')
else:
    print('not found')
