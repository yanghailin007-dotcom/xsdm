"""
创意工坊 API - 支持AI扩展、模板下载、文件上传
"""
import json
import os
from datetime import datetime
from flask import jsonify, request, send_file, session
from web.auth import login_required
from web.web_config import logger


def register_creative_workshop_routes(app, manager=None):
    """注册创意工坊API路由"""
    
    # 导入创意管理器
    try:
        from src.managers.CreativeIdeasManager import CreativeIdeasManager
        base_creative_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'creative_ideas')
        logger.info("✅ 创意工坊管理器初始化成功")
    except ImportError as e:
        logger.error(f"❌ 无法导入创意管理器: {e}")
        CreativeIdeasManager = None
        base_creative_dir = None

    def get_user_creative_manager():
        """获取当前用户的创意管理器（实现用户隔离）"""
        if not CreativeIdeasManager:
            return None
        
        # 获取当前用户名
        from web.utils.path_utils import get_current_username
        username = get_current_username()
        
        if not username:
            logger.warning("⚠️ 无法获取当前用户名，使用默认目录")
            username = "default"
        
        # 用户专属目录
        user_creative_dir = os.path.join(base_creative_dir, username)
        os.makedirs(user_creative_dir, exist_ok=True)
        
        return CreativeIdeasManager(user_creative_dir)

    @app.route('/creative-workshop')
    @login_required
    def creative_workshop_page():
        """创意工坊页面"""
        from flask import render_template
        return render_template('creative-workshop.html')

    @app.route('/api/creative-ideas', methods=['POST'])
    @login_required
    def create_creative_idea():
        """创建新创意（支持用户隔离）"""
        try:
            data = request.json or {}
            
            # 验证必需字段
            if not data.get('coreSetting'):
                return jsonify({"error": "核心设定不能为空"}), 400
            
            # 构建创意数据结构
            creative_data = {
                "coreSetting": data.get('coreSetting', ''),
                "coreSellingPoints": data.get('coreSellingPoints', ''),
                "completeStoryline": data.get('completeStoryline', {
                    "opening": {"stageName": "开篇", "summary": ""},
                    "development": {"stageName": "发展", "summary": ""},
                    "conflict": {"stageName": "冲突", "summary": ""},
                    "ending": {"stageName": "结局", "summary": ""}
                }),
                "novelTitle": data.get('novelTitle', ''),
                "synopsis": data.get('synopsis', ''),
                "totalChapters": data.get('totalChapters', 200),
                "createdAt": datetime.now().isoformat(),
                "lastUpdated": datetime.now().isoformat()
            }
            
            # 使用用户隔离的创意管理器
            creative_manager = get_user_creative_manager()
            if creative_manager:
                idea_id = creative_manager.add_creative_idea(creative_data)
                logger.info(f"✅ 用户创意创建成功: ID={idea_id}")
                
                return jsonify({
                    "success": True,
                    "message": "创意创建成功",
                    "idea_id": idea_id,
                    "creative": {
                        "id": idea_id,
                        "title": creative_data.get('novelTitle', ''),
                        "core_setting": creative_data.get('coreSetting', '')[:100] + "..."
                    }
                })
            else:
                # 如果没有管理器，直接保存到用户目录
                username = session.get('username', 'default')
                user_dir = os.path.join(base_creative_dir, username)
                os.makedirs(user_dir, exist_ok=True)
                
                # 生成文件名
                existing_files = [f for f in os.listdir(user_dir) if f.endswith('.json') and f != 'index.json']
                new_id = len(existing_files) + 1
                
                safe_title = "".join(c for c in (creative_data.get('novelTitle') or 'untitled') if c.isalnum() or c in (' ', '-', '_')).strip()[:30]
                filename = f"{new_id:03d}_{safe_title}.json"
                filepath = os.path.join(user_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(creative_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 用户创意直接保存成功: {filepath}")
                
                return jsonify({
                    "success": True,
                    "message": "创意创建成功",
                    "idea_id": new_id,
                    "creative": {
                        "id": new_id,
                        "title": creative_data.get('novelTitle', ''),
                        "core_setting": creative_data.get('coreSetting', '')[:100] + "..."
                    }
                })
                
        except Exception as e:
            logger.error(f"❌ 创建创意失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/ai-expand', methods=['POST'])
    @login_required
    def ai_expand_creative_idea():
        """使用AI扩展核心创意"""
        try:
            data = request.json or {}
            core_idea = data.get('core_idea', '').strip()
            
            if not core_idea:
                return jsonify({"error": "核心创意不能为空"}), 400
            
            logger.info(f"🤖 AI扩展创意: {core_idea[:50]}...")
            
            # 初始化AI客户端
            from src.core.APIClient import APIClient
            from config.config import CONFIG
            api_client = APIClient(CONFIG)
            
            # 构建AI提示词
            system_prompt = """你是一位专业的小说创意策划师，擅长将简短的核心创意扩展成完整的小说创意结构。

请根据用户提供的核心创意，生成以下内容：
1. 吸引人的小说标题
2. 详细的核心设定（扩展原创意）
3. 核心卖点（用+号分隔的关键词）
4. 小说简介
5. 四阶段故事线（开篇、发展、冲突、结局）

输出必须是严格的JSON格式：
{
    "novelTitle": "小说标题",
    "coreSetting": "详细的核心设定...",
    "coreSellingPoints": "卖点1+卖点2+卖点3",
    "synopsis": "简介...",
    "completeStoryline": {
        "opening": {"stageName": "阶段名称", "summary": "阶段概述..."},
        "development": {"stageName": "阶段名称", "summary": "阶段概述..."},
        "conflict": {"stageName": "阶段名称", "summary": "阶段概述..."},
        "ending": {"stageName": "阶段名称", "summary": "阶段概述..."}
    },
    "totalChapters": 200
}"""

            # 构建完整的prompt（系统提示词 + 用户输入）
            full_prompt = f"{system_prompt}\n\n用户核心创意：\n{core_idea}\n\n请根据以上要求，生成完整的创意JSON。"

            # 调用AI生成 - 使用chapter_content_generation类型
            response = api_client.generate_content_with_retry(
                "chapter_content_generation",
                full_prompt,
                purpose="创意扩展"
            )
            
            if not response:
                return jsonify({"error": "AI生成失败，请重试"}), 500
            
            # 记录AI返回的内容类型以便调试
            logger.info(f"📝 AI响应类型: {type(response)}")
            
            # 处理AI响应
            if isinstance(response, dict):
                # 如果已经是dict，直接使用
                creative_data = response
            elif isinstance(response, str):
                # 如果是字符串，尝试解析JSON
                try:
                    creative_data = json.loads(response)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON解析失败: {e}")
                    # 尝试从文本中提取JSON
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    if json_match:
                        try:
                            creative_data = json.loads(json_match.group(1))
                        except json.JSONDecodeError:
                            json_match = None
                    
                    if not json_match:
                        json_match = re.search(r'\{[\s\S]*\}', response)
                        if json_match:
                            try:
                                creative_data = json.loads(json_match.group())
                            except json.JSONDecodeError as e2:
                                logger.error(f"❌ JSON提取失败: {e2}")
                                return jsonify({"error": f"AI返回格式错误，无法解析JSON"}), 500
                        else:
                            logger.error(f"❌ 未找到JSON内容")
                            return jsonify({"error": "AI返回格式错误，未找到JSON内容"}), 500
            else:
                logger.error(f"❌ 未知的响应类型: {type(response)}")
                return jsonify({"error": "AI返回格式错误"}), 500
            
            # 验证必要字段
            required_fields = ['novelTitle', 'coreSetting', 'coreSellingPoints', 'completeStoryline']
            for field in required_fields:
                if field not in creative_data:
                    creative_data[field] = '' if field != 'completeStoryline' else {}
            
            # 确保四阶段结构完整
            storyline = creative_data.get('completeStoryline', {})
            for stage in ['opening', 'development', 'conflict', 'ending']:
                if stage not in storyline:
                    storyline[stage] = {"stageName": stage, "summary": ""}
            creative_data['completeStoryline'] = storyline
            
            # 设置默认值
            creative_data.setdefault('synopsis', '')
            creative_data.setdefault('totalChapters', 200)
            
            logger.info(f"✅ AI扩展成功: {creative_data.get('novelTitle', '未命名')}")
            
            return jsonify({
                "success": True,
                "creative_data": creative_data
            })
            
        except Exception as e:
            logger.error(f"❌ AI扩展创意失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/template')
    @login_required
    def download_creative_template():
        """下载创意模板"""
        try:
            format_type = request.args.get('format', 'json')
            
            # 示例创意数据
            template_data = {
                "novelTitle": "示例小说：逆天改命的我被全宗门偷听心声",
                "coreSetting": "主角重生为废柴弟子，获得心声外放系统，内心吐槽被全宗门偷听，众人以为他是隐世高人",
                "coreSellingPoints": "心声偷听+误会流+迪化+宗门群像",
                "synopsis": "林默重生到天玄宗外门，成了人人可欺的废柴弟子。然而他获得了一个奇怪的系统——心声外放。每当他在心里吐槽，全宗门都能听到。从此，天玄宗的画风变了...",
                "totalChapters": 200,
                "completeStoryline": {
                    "opening": {
                        "stageName": "心声初现，误会开始",
                        "summary": "第1-20章：主角觉醒心声外放系统，第一次吐槽被宗主听到，被误认为是在指点修炼。宗主按照他的'指点'突破，主角获得大量资源。"
                    },
                    "development": {
                        "stageName": "全宗偷听，集体迪化",
                        "summary": "第21-100章：心声范围扩大到全宗门，弟子们发现'高人'就在身边。主角的日常吐槽被解读成各种高深道理，宗门实力突飞猛进。"
                    },
                    "conflict": {
                        "stageName": "强敌来袭，身份危机",
                        "summary": "第101-160章：敌对宗门联合进攻，主角被迫'出手'。众人以为他在隐藏实力，实际上他真的只是废柴。危机中系统升级，获得真正实力。"
                    },
                    "ending": {
                        "stageName": "真相大白，逆天改命",
                        "summary": "第161-200章：主角的真正身份揭晓——他是上古大能转世。心声外放其实是恢复记忆的过程，最终带领宗门成为天下第一。"
                    }
                }
            }
            
            if format_type == 'json':
                # 返回JSON模板
                from io import BytesIO
                json_content = json.dumps(template_data, ensure_ascii=False, indent=2)
                buffer = BytesIO(json_content.encode('utf-8'))
                buffer.seek(0)
                
                return send_file(
                    buffer,
                    mimetype='application/json',
                    as_attachment=True,
                    download_name='创意模板.json'
                )
                
            elif format_type == 'excel':
                # 返回Excel模板
                try:
                    import pandas as pd
                    from io import BytesIO
                    
                    # 创建Excel工作簿
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        # 基本信息表
                        basic_info = pd.DataFrame({
                            '字段': ['小说标题', '核心设定', '核心卖点', '简介', '总章节数'],
                            '内容': [
                                template_data['novelTitle'],
                                template_data['coreSetting'],
                                template_data['coreSellingPoints'],
                                template_data['synopsis'],
                                template_data['totalChapters']
                            ]
                        })
                        basic_info.to_excel(writer, sheet_name='基本信息', index=False)
                        
                        # 故事线表
                        storyline_data = []
                        for stage_key, stage_value in template_data['completeStoryline'].items():
                            storyline_data.append({
                                '阶段': stage_key,
                                '阶段名称': stage_value['stageName'],
                                '阶段概述': stage_value['summary']
                            })
                        storyline_df = pd.DataFrame(storyline_data)
                        storyline_df.to_excel(writer, sheet_name='故事线', index=False)
                        
                        # 说明表
                        instructions = pd.DataFrame({
                            '说明': [
                                '请按照模板格式填写创意信息',
                                '基本信息表中：',
                                '  - 核心设定：用一句话概括小说的核心设定',
                                '  - 核心卖点：用+号分隔的关键词，如：迪化流+群像+心声偷听',
                                '故事线表中：',
                                '  - 阶段固定为：opening, development, conflict, ending',
                                '  - 每个阶段填写阶段名称和概述',
                                '填写完成后，保存为JSON或Excel格式上传'
                            ]
                        })
                        instructions.to_excel(writer, sheet_name='填写说明', index=False)
                    
                    buffer.seek(0)
                    return send_file(
                        buffer,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name='创意模板.xlsx'
                    )
                    
                except ImportError:
                    logger.warning("⚠️ 未安装 pandas/openpyxl，返回JSON格式")
                    return jsonify({"error": "Excel模板暂不可用，请使用JSON格式"}), 400
            else:
                return jsonify({"error": "不支持的格式"}), 400
                
        except Exception as e:
            logger.error(f"❌ 下载模板失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/upload', methods=['POST'])
    @login_required
    def upload_creative_file():
        """上传创意文件"""
        try:
            if 'file' not in request.files:
                return jsonify({"error": "没有上传文件"}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "未选择文件"}), 400
            
            # 读取文件内容
            if file.filename.endswith('.json'):
                content = file.read().decode('utf-8')
                data = json.loads(content)
            elif file.filename.endswith(('.xlsx', '.xls')):
                # Excel文件解析
                try:
                    import pandas as pd
                    from io import BytesIO
                    
                    buffer = BytesIO(file.read())
                    
                    # 读取基本信息
                    basic_df = pd.read_excel(buffer, sheet_name='基本信息')
                    info_dict = dict(zip(basic_df['字段'], basic_df['内容']))
                    
                    # 读取故事线
                    buffer.seek(0)
                    storyline_df = pd.read_excel(buffer, sheet_name='故事线')
                    storyline = {}
                    for _, row in storyline_df.iterrows():
                        storyline[row['阶段']] = {
                            "stageName": row['阶段名称'],
                            "summary": row['阶段概述']
                        }
                    
                    data = {
                        "novelTitle": info_dict.get('小说标题', ''),
                        "coreSetting": info_dict.get('核心设定', ''),
                        "coreSellingPoints": info_dict.get('核心卖点', ''),
                        "synopsis": info_dict.get('简介', ''),
                        "totalChapters": int(info_dict.get('总章节数', 200)),
                        "completeStoryline": storyline
                    }
                    
                except ImportError:
                    return jsonify({"error": "服务器未安装Excel解析库"}), 500
            else:
                return jsonify({"error": "不支持的文件格式"}), 400
            
            # 验证必要字段
            if not data.get('coreSetting'):
                return jsonify({"error": "文件中缺少核心设定"}), 400
            
            # 保存创意
            creative_manager = get_user_creative_manager()
            if creative_manager:
                data['lastUpdated'] = datetime.now().isoformat()
                idea_id = creative_manager.add_creative_idea(data)
                
                logger.info(f"✅ 文件上传成功: {file.filename} -> 创意ID={idea_id}")
                
                return jsonify({
                    "success": True,
                    "message": "创意导入成功",
                    "idea_id": idea_id
                })
            else:
                return jsonify({"error": "创意管理器初始化失败"}), 500
                
        except json.JSONDecodeError as e:
            return jsonify({"error": f"JSON解析错误: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"❌ 上传创意文件失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/user-list', methods=['GET'])
    @login_required
    def get_user_creative_ideas():
        """获取当前用户的创意列表（用户隔离）"""
        try:
            creative_manager = get_user_creative_manager()
            
            if creative_manager:
                data = creative_manager.load_creative_ideas()
                creative_works = data.get("creativeWorks", [])
                storage_format = data.get("format", "unknown")
                
                # 格式化为前端友好的格式
                formatted_ideas = []
                for i, work in enumerate(creative_works):
                    formatted_idea = {
                        "id": i + 1,
                        "core_setting": work.get("coreSetting", ""),
                        "core_selling_points": work.get("coreSellingPoints", ""),
                        "storyline": work.get("completeStoryline", {}),
                        "raw_data": work
                    }
                    
                    # 提取故事线阶段名称
                    storyline = work.get("completeStoryline", {})
                    stages = []
                    for stage_key in ["opening", "development", "conflict", "ending"]:
                        if stage_key in storyline:
                            stage_name = storyline[stage_key].get("stageName", stage_key)
                            stages.append(stage_name)
                    formatted_idea["stages_preview"] = stages
                    
                    formatted_ideas.append(formatted_idea)
                
                return jsonify({
                    "success": True,
                    "count": len(formatted_ideas),
                    "creative_ideas": formatted_ideas,
                    "storage_info": creative_manager.get_storage_info()
                })
            else:
                return jsonify({"error": "创意管理器初始化失败"}), 500
                
        except Exception as e:
            logger.error(f"❌ 获取用户创意列表失败: {e}")
            return jsonify({"error": str(e)}), 500

    logger.info("✅ 创意工坊API注册完成")
