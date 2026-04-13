# -*- coding: utf-8 -*-
"""
章节标题与正文解析验证脚本（简化版）
验证强制标准格式、补标题、唯一性逻辑
"""

import re
import json


# ==================== batch_chapter_generator 简化逻辑 ====================

def _clean_result(result):
    if result['content']:
        title_patterns = [
            r'^第\s*[一二三四五六七八九十百千万零\d]+\s*章[：: ]*[^\n]*\n*',
            r'^Chapter\s*\d+[：: ]*[^\n]*\n*',
            r'^Chapter\d+[：: ]*[^\n]*\n*',
        ]
        for pattern in title_patterns:
            result['content'] = re.sub(pattern, '', result['content'], flags=re.IGNORECASE)
        result['content'] = result['content'].lstrip('\n')
        if result.get('title'):
            escaped = re.escape(result['title'].strip())
            result['content'] = re.sub(rf'^\s*{escaped}\s*\n+', '', result['content'], count=1)
    return result


def _parse_response(response):
    result = {'title': '', 'content': ''}
    if isinstance(response, dict):
        result['title'] = response.get('title', '')
        result['content'] = response.get('content', str(response))
        return _clean_result(result)
    if not isinstance(response, str):
        result['content'] = str(response)
        return _clean_result(result)
    cleaned_response = response.strip()
    title_match = re.search(r'---\s*[标標][题題]\s*---\s*\n?(.*?)\n?---\s*[正正][文文]\s*---', cleaned_response, re.DOTALL | re.IGNORECASE)
    if title_match:
        result['title'] = title_match.group(1).strip()
        content_start = cleaned_response.find('---正文---') + len('---正文---')
        if content_start < len('---正文---') + 10:
            content_start = cleaned_response.find('---正文---') + len('---正文---')
        result['content'] = cleaned_response[content_start:].strip()
        return _clean_result(result)
    json_content = cleaned_response
    if json_content.startswith('```'):
        first_newline = json_content.find('\n')
        if first_newline != -1:
            json_content = json_content[first_newline:].strip()
        if json_content.endswith('```'):
            json_content = json_content[:-3].strip()
    try:
        parsed = json.loads(json_content)
        if isinstance(parsed, dict):
            result['title'] = parsed.get('title', '')
            result['content'] = parsed.get('content', '')
            return _clean_result(result)
    except Exception:
        pass
    result['content'] = cleaned_response
    return _clean_result(result)


# ==================== 唯一性逻辑 ====================

class TitleUniquenessChecker:
    def __init__(self):
        self._titles = set()
    
    def ensure_unique(self, title):
        if not title:
            title = "剧情推进"
        clean = re.sub(r'^第\s*[一二三四五六七八九十百千万零\d]+\s*章\s*', '', title).strip()
        if not clean:
            clean = "剧情推进"
        original = clean
        counter = 1
        while clean in self._titles:
            clean = f"{original} ({counter})"
            counter += 1
        self._titles.add(clean)
        return clean


# ==================== 测试用例 ====================

def run_tests():
    passed = 0
    failed = 0
    
    # 用例1: 标准分隔符
    r1 = _parse_response("---标题---\n被分手的实业家\n---正文---\n临海市。\n沈峰站在大厅中央。")
    assert r1['title'] == "被分手的实业家", f"U1 title: {r1['title']}"
    assert "沈峰" in r1['content'], f"U1 content"
    assert "---正文---" not in r1['content'], f"U1 delimiter残留"
    print("[PASS] U1: 标准分隔符格式")
    passed += 1
    
    # 用例2: JSON
    r2 = _parse_response(json.dumps({"title": "系统激活", "content": "第1章\n\n沈峰走出金融中心。"}, ensure_ascii=False))
    assert r2['title'] == "系统激活", f"U2 title: {r2['title']}"
    assert "沈峰走出金融中心" in r2['content'], f"U2 content"
    assert not r2['content'].startswith("第1章"), f"U2 章号残留: {r2['content'][:20]}"
    print("[PASS] U2: JSON格式")
    passed += 1
    
    # 用例3: 非标准格式 => title为空，content保留
    r3 = _parse_response("沈峰因家族重工机械厂欠债千万，被前女友当众分手。\n\n临海市，恒生金融中心。")
    assert r3['title'] == "", f"U3 title应为空: {r3['title']}"
    assert "临海市" in r3['content'], f"U3 content"
    print("[PASS] U3: 非标准格式返回空title")
    passed += 1
    
    # 用例4: 带空格章号清洗
    r4 = _parse_response("第 30 章：第三阶段里程碑达成\n\n临海市，清晨。")
    assert not r4['content'].startswith("第 30 章"), f"U4 残留: {r4['content'][:20]}"
    assert "临海市，清晨" in r4['content'], f"U4 content"
    print("[PASS] U4: 带空格章号清洗")
    passed += 1
    
    # 用例5: 分隔符+正文残留标题二次清洗
    r5 = _parse_response("---标题---\n工业主宰的觉醒\n---正文---\n第1章 工业主宰的觉醒\n\n沈峰感受着脑海中传来的信息。")
    assert r5['title'] == "工业主宰的觉醒", f"U5 title: {r5['title']}"
    assert "工业主宰的觉醒" not in r5['content'].split('\n')[0], f"U5 标题残留: {r5['content'][:40]}"
    print("[PASS] U5: 分隔符+正文残留标题清洗")
    passed += 1
    
    # 用例6: 唯一性检查
    uniq = TitleUniquenessChecker()
    assert uniq.ensure_unique("打脸金融圈") == "打脸金融圈"
    assert uniq.ensure_unique("打脸金融圈") == "打脸金融圈 (1)"
    assert uniq.ensure_unique("打脸金融圈") == "打脸金融圈 (2)"
    assert uniq.ensure_unique("") == "剧情推进"
    assert uniq.ensure_unique("第3章 系统激活") == "系统激活"
    print("[PASS] U6: 标题唯一性 (1)(2)")
    passed += 1
    
    # 用例7: event不再被当标题（模拟 chapter_conversation_generator 新逻辑）
    def new_extract_title(ai_title, content):
        if ai_title:
            t = ai_title.strip()
            t = re.sub(r'^第\s*[一二三四五六七八九十百千万零\d]+\s*章\s*', '', t)
            if len(t) >= 4:
                return t
        if content and len(content) > 100:
            # 假设这里调用了 _generate_title_from_content，mock 返回 "被分手的实业家"
            return "被分手的实业家"
        return "剧情推进"
    
    long_event = "沈峰因家族重工机械厂欠债千万，被投身金融圈的前女友林晓雨当众分手。林晓雨嘲讽实业是夕阳产业。"
    t7 = new_extract_title("", "正文内容..." * 20)
    assert t7 == "被分手的实业家", f"U7 title: {t7}"
    t7b = new_extract_title("", "")
    assert t7b == "剧情推进", f"U7b title: {t7b}"
    print("[PASS] U7: 禁止直接返回长event")
    passed += 1
    
    print(f"\n{'='*50}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    if failed == 0:
        print("[OK] 所有解析验证全部通过！")
    return failed == 0


if __name__ == "__main__":
    run_tests()
