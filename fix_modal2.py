import re

# 读取文件
with open('web/templates/phase-one-setup-new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 6. 替换核心设定区块
content = content.replace(
    '<div style="margin-bottom: 32px; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;">\n                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">\n                            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white;">⚙️</div>\n                            <h4 style="color: #1f2937; margin: 0; font-size: 18px; font-weight: 700;">核心设定</h4>\n                        </div>',
    '<div class="editor-section">\n                        <div class="editor-section-header">\n                            <div class="editor-section-icon warning">⚙️</div>\n                            <h4 class="editor-section-title">核心设定</h4>\n                        </div>'
)

# 7. 替换大文本域
content = content.replace(
    '<textarea id="edit-core-setting" rows="20" style="width: 100%; padding: 24px; border: 2px solid #e5e7eb; border-radius: 16px; font-size: 16px; background: white; color: #1f2937; resize: vertical; min-height: 500px; max-height: 800px; transition: all 0.2s; font-family: inherit; line-height: 1.8; box-shadow: inset 0 2px 8px rgba(0,0,0,0.08); box-sizing: border-box;"',
    '<textarea id="edit-core-setting" class="editor-textarea large"'
)

# 8. 替换提示信息
content = content.replace(
    '<div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">\n                                <span style="color: #6b7280; font-size: 14px;">',
    '<div class="editor-hint">\n                                <span>'
)

# 9. 替换核心卖点区块
content = content.replace(
    '<div style="margin-bottom: 32px; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;">\n                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">\n                            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white;">💎</div>\n                            <h4 style="color: #1f2937; margin: 0; font-size: 18px; font-weight: 700;">核心卖点</h4>\n                        </div>',
    '<div class="editor-section">\n                        <div class="editor-section-header">\n                            <div class="editor-section-icon success">💎</div>\n                            <h4 class="editor-section-title">核心卖点</h4>\n                        </div>'
)

content = content.replace(
    '<div id="selling-points-container" style="margin-bottom: 16px; max-height: 240px; overflow-y: auto; border: 2px solid #f3f4f6; border-radius: 10px; background: #fafbfc; padding: 12px;">',
    '<div id="selling-points-container" class="selling-points-container">'
)

content = content.replace(
    '<div style="display: flex; gap: 12px;">\n                            <input type="text" id="new-selling-point" placeholder="输入新的卖点（如：爽文节奏、独特设定等）..." style="flex: 1; padding: 14px 16px; border: 2px solid #e5e7eb; border-radius: 10px; font-size: 15px; background: white; color: #1f2937; transition: all 0.2s; box-sizing: border-box;">\n                            <button type="button" onclick="addSellingPoint()" style="padding: 14px 20px; border: none; border-radius: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">➕ 添加卖点</button>\n                        </div>',
    '<div class="selling-point-input-group">\n                            <input type="text" id="new-selling-point" class="editor-input" placeholder="输入新的卖点（如：爽文节奏、独特设定等）...">\n                            <button type="button" class="editor-btn-primary" onclick="addSellingPoint()">➕ 添加卖点</button>\n                        </div>'
)

# 10. 替换故事线区块
content = content.replace(
    '<div style="margin-bottom: 32px; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;">\n                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">\n                            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white;">📖</div>\n                            <h4 style="color: #1f2937; margin: 0; font-size: 18px; font-weight: 700;">故事线时间轴</h4>\n                        </div>',
    '<div class="editor-section">\n                        <div class="editor-section-header">\n                            <div class="editor-section-icon danger">📖</div>\n                            <h4 class="editor-section-title">故事线时间轴</h4>\n                        </div>'
)

# 保存文件
with open('web/templates/phase-one-setup-new.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('第二部分替换完成')
