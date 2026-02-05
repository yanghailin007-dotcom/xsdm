import re

# 读取文件
with open('web/templates/phase-one-setup-new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换模态框外层容器
content = content.replace(
    '<div id="creative-editor-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 999999; backdrop-filter: blur(4px);">',
    '<div id="creative-editor-modal" class="creative-editor-modal">'
)

content = content.replace(
    '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4); max-width: 1200px; width: 95vw; max-height: 90vh; overflow: hidden; border: 1px solid rgba(255,255,255,0.2);">',
    '<div class="creative-editor-content">'
)

# 2. 替换头部
content = content.replace(
    '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 32px; display: flex; justify-content: space-between; align-items: center; border-radius: 16px 16px 0 0;">',
    '<div class="creative-editor-header">'
)

content = content.replace(
    '<div style="display: flex; align-items: center; gap: 12px;">\n                    <div style="width: 40px; height: 40px; background: rgba(255,255,255,0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px;">',
    '<div class="creative-editor-header-left">\n                    <div class="creative-editor-icon">'
)

content = content.replace(
    '<h3 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">创意编辑器</h3>\n                        <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.9; font-weight: 400;">编辑您的小说创意设定</p>',
    '<h3 class="creative-editor-title">创意编辑器</h3>\n                        <p class="creative-editor-subtitle">编辑您的小说创意设定</p>'
)

content = content.replace(
    '</div>\n                <div style="display: flex; gap: 12px; align-items: center;">\n                    <button type="button" onclick="resetCreativeEditor()" style="background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.25); padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">🔄 重置</button>\n                    <button type="button" onclick="saveCreativeChanges()" style="background: rgba(255,255,255,0.25); color: white; border: 1px solid rgba(255,255,255,0.35); padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s;">💾 保存修改</button>\n                    <button type="button" onclick="closeCreativeEditor()" style="background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); font-size: 20px; cursor: pointer; padding: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 8px; transition: all 0.2s;">×</button>\n                </div>\n            </div>',
    '</div>\n                <div class="creative-editor-actions">\n                    <button type="button" class="modal-btn" onclick="resetCreativeEditor()">🔄 重置</button>\n                    <button type="button" class="modal-btn modal-btn-primary" onclick="saveCreativeChanges()">💾 保存修改</button>\n                    <button type="button" class="modal-btn modal-btn-close" onclick="closeCreativeEditor()">×</button>\n                </div>\n            </div>'
)

# 3. 替换内容区域
content = content.replace(
    '<div style="padding: 0; overflow-y: auto; max-height: calc(90vh - 100px); background: #fafbfc;">\n                <div style="padding: 32px;">',
    '<div class="creative-editor-body">\n                <div class="creative-editor-inner">'
)

# 4. 替换基本信息区块
content = content.replace(
    '<div style="margin-bottom: 32px; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;">\n                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">\n                            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white;">📝</div>\n                            <h4 style="color: #1f2937; margin: 0; font-size: 18px; font-weight: 700;">基本信息</h4>\n                        </div>',
    '<div class="editor-section">\n                        <div class="editor-section-header">\n                            <div class="editor-section-icon primary">📝</div>\n                            <h4 class="editor-section-title">基本信息</h4>\n                        </div>'
)

# 5. 替换表单网格
content = content.replace(
    '<div style="display: grid; gap: 20px;">\n                            <div>\n                                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151; font-size: 14px;">小说标题</label>\n                                <input type="text" id="edit-novel-title" value="" style="width: 100%; padding: 14px 16px; border: 2px solid #e5e7eb; border-radius: 10px; font-size: 15px; background: white; color: #1f2937; transition: all 0.2s; font-weight: 500; box-sizing: border-box;">\n                            </div>\n                            \n                            <div>\n                                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151; font-size: 14px;">小说简介</label>\n                                <textarea id="edit-novel-synopsis" rows="4" style="width: 100%; padding: 14px 16px; border: 2px solid #e5e7eb; border-radius: 10px; font-size: 15px; background: white; color: #1f2937; resize: vertical; min-height: 100px; transition: all 0.2s; font-family: inherit; line-height: 1.5; box-sizing: border-box;"></textarea>\n                            </div>\n                        </div>',
    '<div class="editor-form-grid">\n                            <div class="editor-form-group">\n                                <label class="editor-label">小说标题</label>\n                                <input type="text" id="edit-novel-title" class="editor-input" value="">\n                            </div>\n                            \n                            <div class="editor-form-group full-width">\n                                <label class="editor-label">小说简介</label>\n                                <textarea id="edit-novel-synopsis" class="editor-textarea" rows="4"></textarea>\n                            </div>\n                        </div>'
)

# 保存文件
with open('web/templates/phase-one-setup-new.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('创意编辑器模态框样式已更新')
