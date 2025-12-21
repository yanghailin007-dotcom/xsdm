"""
创意文件解析API
"""
import json
import os
from flask import jsonify, request
from datetime import datetime

from web.auth import login_required
from web.config import logger, CREATIVE_IDEAS_FILE
from web.managers.novel_manager import NovelGenerationManager


def register_creative_routes(app, manager: NovelGenerationManager):
    """注册创意相关API路由"""
    
    def load_creative_ideas_from_file(file_path: str = None) -> dict:
        """从文件加载创意数据"""
        if file_path is None:
            file_path = str(CREATIVE_IDEAS_FILE)

        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_path = os.path.join(project_root, file_path)

            if not os.path.exists(full_path):
                logger.info(f"创意文件不存在: {full_path}")
                return {"error": f"创意文件不存在: {file_path}"}

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析JSON格式的创意文件
            creative_data = json.loads(content)
            logger.info(f"✅ 成功加载创意文件: {full_path}")
            return creative_data

        except json.JSONDecodeError as e:
            logger.error(f"❌ 创意文件JSON解析错误: {e}")
            return {"error": f"创意文件JSON格式错误: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ 加载创意文件失败: {e}")
            return {"error": str(e)}

    @app.route('/api/creative-ideas', methods=['GET'])
    def get_creative_ideas():
        """获取创意文件内容"""
        try:
            creative_data = load_creative_ideas_from_file()

            if "error" in creative_data:
                return jsonify(creative_data), 404

            # 提取创意作品列表
            creative_works = creative_data.get("creativeWorks", [])

            # 格式化为前端友好的格式
            formatted_ideas = []
            for i, work in enumerate(creative_works):
                formatted_idea = {
                    "id": i + 1,
                    "core_setting": work.get("coreSetting", ""),
                    "core_selling_points": work.get("coreSellingPoints", ""),
                    "storyline": work.get("completeStoryline", {}),
                    "raw_data": work  # 保留原始数据以便传递给生成器
                }

                # 提取故事线阶段名称作为预览
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
                "creative_ideas": formatted_ideas
            })

        except Exception as e:
            logger.error(f"❌ 获取创意列表失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/<int:idea_id>', methods=['GET'])
    def get_creative_idea_detail(idea_id):
        """获取指定创意的详细信息"""
        try:
            creative_data = load_creative_ideas_from_file()

            if "error" in creative_data:
                return jsonify(creative_data), 404

            creative_works = creative_data.get("creativeWorks", [])

            if idea_id < 1 or idea_id > len(creative_works):
                return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404

            work = creative_works[idea_id - 1]

            # 详细格式化
            detail = {
                "id": idea_id,
                "core_setting": work.get("coreSetting", ""),
                "core_selling_points": work.get("coreSellingPoints", ""),
                "storyline": work.get("completeStoryline", {}),
                "raw_data": work
            }

            return jsonify({
                "success": True,
                "creative_idea": detail
            })

        except Exception as e:
            logger.error(f"❌ 获取创意详情失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/start-generation-from-idea', methods=['POST'])
    def start_generation_from_idea():
        """从创意文件中的创意开始生成小说"""
        try:
            data = request.json or {}
            idea_id = data.get("idea_id")
            
            # 修复：确保total_chapters是有效的整数
            total_chapters = data.get("total_chapters", 200)
            if total_chapters is None or total_chapters == "":
                total_chapters = 200
            try:
                total_chapters = int(total_chapters)
                if total_chapters <= 0:
                    total_chapters = 200
            except (ValueError, TypeError):
                total_chapters = 200

            if idea_id is None:
                return jsonify({"error": "缺少idea_id参数"}), 400

            # 加载创意数据
            creative_data = load_creative_ideas_from_file()

            if "error" in creative_data:
                return jsonify(creative_data), 404

            creative_works = creative_data.get("creativeWorks", [])

            if idea_id < 1 or idea_id > len(creative_works):
                return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404

            # 获取选定的创意
            selected_idea = creative_works[idea_id - 1]

            # 构建生成配置
            novel_config = {
                "title": f"创意{idea_id}的小说",  # 标题将由生成器根据创意内容生成
                "synopsis": selected_idea.get("coreSetting", "")[:200],
                "core_setting": selected_idea.get("coreSetting", ""),
                "core_selling_points": selected_idea.get("coreSellingPoints", "").split("+") if selected_idea.get("coreSellingPoints") else [],
                "total_chapters": total_chapters,
                "creative_seed": selected_idea,  # 传递完整的创意数据
                "use_creative_file": True
            }

            # 启动生成任务
            task_id = manager.start_generation(novel_config)

            logger.info(f"✅ 从创意ID {idea_id} 启动生成任务: {task_id}")

            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": f"已从创意 #{idea_id} 启动小说生成",
                "idea_preview": {
                    "core_setting": selected_idea.get("coreSetting", "")[:100] + "...",
                    "selling_points": selected_idea.get("coreSellingPoints", "")
                }
            })

        except Exception as e:
            logger.error(f"❌ 从创意启动生成失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/<int:idea_id>', methods=['PUT'])
    @login_required
    def update_creative_idea(idea_id):
        """更新指定创意"""
        try:
            data = request.json or {}
            
            # 验证必需字段
            required_fields = ['coreSetting', 'novelTitle']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"error": f"缺少必需字段: {field}"}), 400
            
            # 加载现有创意数据
            creative_data = load_creative_ideas_from_file()
            
            if "error" in creative_data:
                return jsonify(creative_data), 404
            
            creative_works = creative_data.get("creativeWorks", [])
            
            if idea_id < 1 or idea_id > len(creative_works):
                return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404
            
            # 更新创意数据
            updated_idea = creative_works[idea_id - 1]
            
            # 保留原始字段，更新提供的字段
            updated_idea["coreSetting"] = data.get("coreSetting", updated_idea.get("coreSetting", ""))
            updated_idea["novelTitle"] = data.get("novelTitle", updated_idea.get("novelTitle", ""))
            updated_idea["synopsis"] = data.get("synopsis", updated_idea.get("synopsis", ""))
            updated_idea["coreSellingPoints"] = data.get("coreSellingPoints", updated_idea.get("coreSellingPoints", ""))
            updated_idea["totalChapters"] = data.get("totalChapters", updated_idea.get("totalChapters", 200))
            
            # 更新故事线
            if data.get("completeStoryline"):
                updated_idea["completeStoryline"] = data["completeStoryline"]
            
            # 更新时间戳
            updated_idea["lastUpdated"] = datetime.now().isoformat()
            
            # 保存到文件
            try:
                with open(CREATIVE_IDEAS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(creative_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 创意ID {idea_id} 更新成功")
                
                return jsonify({
                    "success": True,
                    "message": f"创意 #{idea_id} 更新成功",
                    "updated_idea": {
                        "id": idea_id,
                        "core_setting": updated_idea.get("coreSetting", ""),
                        "novel_title": updated_idea.get("novelTitle", ""),
                        "last_updated": updated_idea.get("lastUpdated")
                    }
                })
                
            except Exception as save_error:
                logger.error(f"❌ 保存创意文件失败: {save_error}")
                return jsonify({"error": f"保存失败: {str(save_error)}"}), 500
                
        except Exception as e:
            logger.error(f"❌ 更新创意失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/creative-ideas/<int:idea_id>', methods=['DELETE'])
    @login_required
    def delete_creative_idea(idea_id):
        """删除指定创意"""
        try:
            # 加载现有创意数据
            creative_data = load_creative_ideas_from_file()
            
            if "error" in creative_data:
                return jsonify(creative_data), 404
            
            creative_works = creative_data.get("creativeWorks", [])
            
            if idea_id < 1 or idea_id > len(creative_works):
                return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404
            
            # 获取要删除的创意信息（用于日志）
            deleted_idea = creative_works[idea_id - 1]
            deleted_title = deleted_idea.get("coreSetting", "未知创意")[:50]
            
            # 从列表中移除创意
            creative_works.pop(idea_id - 1)
            
            # 保存到文件
            try:
                with open(CREATIVE_IDEAS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(creative_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 创意ID {idea_id} 删除成功: {deleted_title}...")
                
                return jsonify({
                    "success": True,
                    "message": f"创意 #{idea_id} 删除成功",
                    "deleted_idea": {
                        "id": idea_id,
                        "title_preview": deleted_title
                    }
                })
                
            except Exception as save_error:
                logger.error(f"❌ 保存创意文件失败: {save_error}")
                return jsonify({"error": f"保存失败: {str(save_error)}"}), 500
                
        except Exception as e:
            logger.error(f"❌ 删除创意失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500