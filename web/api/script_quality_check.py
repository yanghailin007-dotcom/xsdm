"""
剧本质量评估API
在生成视频前对剧本进行严格的质量检查，确保符合视频生成要求
使用AI进行智能评估，加载完整的小说项目信息进行一致性检查
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from src.utils.logger import get_logger

script_quality_api = Blueprint('script_quality_api', __name__)
logger = get_logger("script_quality_api")


def get_novel_project_path():
    """获取小说项目目录路径"""
    # 获取工作目录下的小说项目文件夹
    import os
    work_dir = Path(__file__).parent.parent.parent.parent
    project_dir = work_dir / "小说项目"

    # 如果不存在，尝试在当前工作目录查找
    if not project_dir.exists():
        cwd = Path(os.getcwd())
        project_dir = cwd / "小说项目"

    return project_dir


def get_video_project_path():
    """获取视频项目目录路径"""
    import os
    work_dir = Path(__file__).parent.parent.parent.parent
    project_dir = work_dir / "视频项目"

    # 如果不存在，尝试在当前工作目录查找
    if not project_dir.exists():
        cwd = Path(os.getcwd())
        project_dir = cwd / "视频项目"

    return project_dir


def find_project_dir_by_title(novel_title: str) -> Optional[Path]:
    """根据小说标题查找项目目录"""
    project_path = get_novel_project_path()

    logger.info(f"find_project_dir_by_title: novel_title='{novel_title}', project_path={project_path}, exists={project_path.exists()}")

    # 检查项目路径是否存在
    if not project_path.exists():
        logger.error(f"小说项目目录不存在: {project_path}")
        return None

    # 精确匹配
    exact_match = project_path / novel_title
    logger.info(f"find_project_dir_by_title: 精确匹配路径={exact_match}, exists={exact_match.exists()}")
    if exact_match.exists() and exact_match.is_dir():
        logger.info(f"✅ 精确匹配找到项目目录: {exact_match}")
        return exact_match

    # 模糊匹配（处理可能的后缀差异）
    try:
        logger.info(f"find_project_dir_by_title: 开始模糊匹配，共有 {len(list(project_path.iterdir()))} 个项目")
        for item in project_path.iterdir():
            if item.is_dir():
                logger.info(f"  - 项目: {item.name}, 包含novel_title={novel_title in item.name}")
                if novel_title in item.name:
                    logger.info(f"✅ 模糊匹配找到项目目录: {item}")
                    return item
    except Exception as e:
        logger.warning(f"遍历项目目录时出错: {e}")

    logger.warning(f"⚠️ 未找到项目目录: {novel_title}")
    return None


def load_project_info(novel_title: str) -> Dict:
    """加载项目信息"""
    project_dir = find_project_dir_by_title(novel_title)
    if not project_dir:
        logger.warning(f"未找到项目目录: {novel_title}")
        return {}

    # 查找项目信息文件
    info_files = [
        project_dir / f"{novel_title}_项目信息.json",
        project_dir / "project_info" / f"{novel_title}_项目信息.json",
    ]

    for info_file in info_files:
        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"✅ 成功加载项目信息: {info_file}")
                    return data
            except Exception as e:
                logger.warning(f"无法加载项目信息 {info_file}: {e}")

    return {}


def load_worldview(novel_title: str) -> Dict:
    """加载世界观信息"""
    project_dir = find_project_dir_by_title(novel_title)
    if not project_dir:
        logger.warning(f"load_worldview: 未找到项目目录: {novel_title}")
        return {}

    logger.info(f"load_worldview: 项目目录 = {project_dir}")

    # 查找世界观文件
    worldview_paths = [
        project_dir / "worldview" / f"{novel_title}_世界观.json",
        project_dir / "worldview" / f"{novel_title}_世界观_*.json",
        project_dir / "materials" / "worldview" / f"{novel_title}_世界观.json",
    ]

    for path in worldview_paths:
        if path.exists() and path.is_file():
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logger.info(f"✅ 成功加载世界观: {path}")
                    return data
            except Exception as e:
                logger.warning(f"无法加载世界观 {path}: {e}")

    # 尝试glob模式
    for pattern in [project_dir / "worldview" / f"{novel_title}_世界观*.json",
                    project_dir / "materials" / "worldview" / "*.json"]:
        if pattern.parent.exists():
            matching_files = list(pattern.parent.glob(pattern.name))
            logger.info(f"load_worldview: glob模式 {pattern} 找到 {len(matching_files)} 个文件")
            for f in matching_files:
                if f.exists():
                    try:
                        with open(f, 'r', encoding='utf-8') as file:
                            data = json.load(file)
                            logger.info(f"✅ 成功加载世界观: {f}")
                            return data
                    except Exception as e:
                        logger.warning(f"无法加载世界观 {f}: {e}")

    # 直接glob搜索
    for f in project_dir.rglob("*世界观*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"✅ 成功加载世界观: {f}")
                return data
        except Exception as e:
            continue

    logger.warning(f"⚠️ 未找到世界观文件，项目目录: {project_dir}")
    return {}


def load_character_design(novel_title: str) -> Dict:
    """加载完整的角色设计信息"""
    project_dir = find_project_dir_by_title(novel_title)
    if not project_dir:
        logger.warning(f"load_character_design: 未找到项目目录: {novel_title}")
        return {}

    logger.info(f"load_character_design: 项目目录 = {project_dir}")

    # 查找角色设计文件
    try:
        all_json_files = list(project_dir.rglob("*.json"))
        logger.info(f"load_character_design: 项目中共有 {len(all_json_files)} 个JSON文件")
        character_files = [f for f in all_json_files if "角色" in f.name or "character" in f.name.lower()]
        logger.info(f"load_character_design: 找到 {len(character_files)} 个角色相关文件: {[str(f) for f in character_files]}")
    except Exception as e:
        logger.error(f"load_character_design: 遍历文件出错: {e}")

    for f in project_dir.rglob("*角色设计*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"✅ 成功加载角色设计: {f}")
                return data
        except Exception as e:
            logger.warning(f"无法加载角色设计 {f}: {e}")

    # 也尝试查找characters目录
    characters_dir = project_dir / "characters"
    if characters_dir.exists():
        for f in characters_dir.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logger.info(f"✅ 成功加载角色设计: {f}")
                    return data
            except Exception as e:
                logger.warning(f"无法加载角色设计 {f}: {e}")

    logger.warning(f"⚠️ 未找到角色设计文件，项目目录: {project_dir}")
    return {}


def load_growth_plan(novel_title: str) -> Dict:
    """加载成长路线/人物成长计划"""
    project_dir = find_project_dir_by_title(novel_title)
    if not project_dir:
        logger.warning(f"load_growth_plan: 未找到项目目录: {novel_title}")
        return {}

    logger.info(f"load_growth_plan: 项目目录 = {project_dir}")

    # 查找成长路线文件
    for f in project_dir.rglob("*成长路线*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"✅ 成功加载成长路线: {f}")
                return data
        except Exception as e:
            logger.warning(f"无法加载成长路线 {f}: {e}")

    # 尝试materials目录
    materials_dir = project_dir / "materials" / "phase_one_products"
    if materials_dir.exists():
        for f in materials_dir.glob("*成长*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logger.info(f"✅ 成功加载成长路线: {f}")
                    return data
            except Exception as e:
                logger.warning(f"无法加载成长路线 {f}: {e}")

    logger.warning(f"⚠️ 未找到成长路线文件，项目目录: {project_dir}")
    return {}


def load_market_analysis(novel_title: str) -> Dict:
    """加载市场分析信息"""
    project_dir = find_project_dir_by_title(novel_title)
    if not project_dir:
        logger.warning(f"load_market_analysis: 未找到项目目录: {novel_title}")
        return {}

    logger.info(f"load_market_analysis: 项目目录 = {project_dir}")

    # 查找市场分析文件
    for f in project_dir.rglob("*市场分析*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"✅ 成功加载市场分析: {f}")
                return data
        except Exception as e:
            logger.warning(f"无法加载市场分析 {f}: {e}")

    # 也可能在market_analysis目录下
    market_dir = project_dir / "market_analysis"
    if market_dir.exists():
        for f in market_dir.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logger.info(f"✅ 成功加载市场分析: {f}")
                    return data
            except Exception as e:
                continue

    # 尝试materials目录
    materials_market = project_dir / "materials" / "market_analysis"
    if materials_market.exists():
        for f in materials_market.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logger.info(f"✅ 成功加载市场分析: {f}")
                    return data
            except Exception as e:
                continue

    logger.warning(f"⚠️ 未找到市场分析文件，项目目录: {project_dir}")
    return {}


def load_stage_plans(novel_title: str) -> Dict:
    """加载阶段计划"""
    project_dir = find_project_dir_by_title(novel_title)
    if not project_dir:
        return {}

    plans_dir = project_dir / "plans"
    if not plans_dir.exists():
        plans_dir = project_dir / "stage_plan"
    if not plans_dir.exists():
        plans_dir = project_dir / "materials" / "phase_one_products"

    all_stages = {}

    stage_patterns = [
        ("opening", "*opening_stage*"),
        ("development", "*development_stage*"),
        ("climax", "*climax_stage*"),
        ("ending", "*ending_stage*"),
    ]

    if plans_dir.exists():
        for stage_name, pattern in stage_patterns:
            for f in plans_dir.glob(pattern):
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        all_stages[stage_name] = data
                        logger.info(f"✅ 成功加载{stage_name}阶段计划: {f}")
                        break
                except Exception as e:
                    logger.warning(f"无法加载{stage_name}阶段计划 {f}: {e}")

    return all_stages


def load_all_novel_data(novel_title: str) -> Dict:
    """加载所有小说项目数据"""
    logger.info(f"📂 开始加载小说项目数据: {novel_title}")

    data = {
        "project_info": load_project_info(novel_title),
        "worldview": load_worldview(novel_title),
        "characters": load_character_design(novel_title),
        "growth_plan": load_growth_plan(novel_title),
        "market_analysis": load_market_analysis(novel_title),
        "stage_plans": load_stage_plans(novel_title),
    }

    # 统计加载情况
    loaded_count = sum(1 for v in data.values() if v)
    total_count = len(data)
    logger.info(f"📊 数据加载完成: {loaded_count}/{total_count} 个文件加载成功")

    return data


@script_quality_api.route('/api/script/quality-check', methods=['POST'])
def check_script_quality():
    """
    剧本质量检查API（使用AI智能评估）

    请求体：
    {
        "novel_title": "小说标题",
        "episode_title": "分集标题",  // 可选
        "shots": [...],  // 待检查的镜头列表
        "auto_fix": true/false  // 是否自动修复（当分数<80时）
    }

    响应：
    {
        "success": true,
        "passed": true/false,
        "score": 85,  // 0-100分
        "detailed_scores": {...},
        "issues": [...],  // 发现的问题列表
        "warnings": [...],  // 警告信息
        "recommendations": [...],  // 改进建议
        "improved_shots": [...],  // 如果auto_fix=true且分数<80，返回改进后的镜头
        "design_file_issues": [...]  // 如果是原始设计问题，列出需要修改的设计文件
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')
        episode_title = data.get('episode_title', '')
        shots = data.get('shots', [])
        auto_fix = data.get('auto_fix', True)

        if not novel_title:
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        if not shots:
            return jsonify({"success": False, "error": "缺少镜头数据"}), 400

        logger.info(f"📋 [剧本质量检查] 检查项目: {novel_title} - {episode_title}, 镜头数: {len(shots)}")

        # 先验证项目目录是否存在
        project_dir = find_project_dir_by_title(novel_title)
        if not project_dir:
            return jsonify({
                "success": False,
                "error": f"未找到小说项目目录: {novel_title}",
                "details": f"请确保项目目录存在于 {get_novel_project_path()} 下"
            }), 404

        # 加载所有小说数据
        novel_data = load_all_novel_data(novel_title)

        # 检查是否有任何数据加载成功
        if not any(novel_data.values()):
            return jsonify({
                "success": False,
                "error": "未能加载任何项目数据",
                "details": "请检查项目文件是否存在（世界观、角色设计、成长路线、市场分析等）"
            }), 404

        # 执行质量检查（带超时保护，30秒超时）
        checker = ScriptQualityChecker(novel_data, novel_title)
        result = checker.check_with_timeout(shots, episode_title, timeout=30)

        # 如果分数低于80且开启自动修复
        if not result.get("passed") and result.get("score", 100) < 80 and auto_fix:
            logger.info(f"🔧 评分{result.get('score')}分低于80分，开始自动修复...")
            improved_result = checker.improve_script(shots, episode_title, result)
            result.update(improved_result)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"剧本质量检查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@script_quality_api.route('/api/script/quality-report', methods=['POST'])
def get_quality_report():
    """
    生成剧本质量报告（包含角色一致性、情节逻辑等详细分析）

    请求体：
    {
        "novel_title": "小说标题"
    }

    响应：
    {
        "success": true,
        "report": {
            "worldview": {...},
            "characters": {...},
            "growth_plan": {...},
            "market_analysis": {...},
            "quality_threshold": {...}
        }
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')

        if not novel_title:
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        logger.info(f"📊 [剧本质量报告] 生成报告: {novel_title}")

        # 加载所有小说数据
        novel_data = load_all_novel_data(novel_title)

        # 生成质量报告
        checker = ScriptQualityChecker(novel_data, novel_title)
        report = checker.generate_data_report()

        return jsonify({"success": True, "report": report}), 200

    except Exception as e:
        logger.error(f"生成质量报告失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@script_quality_api.route('/api/script/improve', methods=['POST'])
def improve_script():
    """
    根据问题清单改进剧本

    请求体：
    {
        "novel_title": "小说标题",
        "episode_title": "分集标题",
        "shots": [...],  // 原始镜头列表
        "issues": [...],  // 问题列表
        "improve_type": "script" / "design"  // 改进类型：script=改进剧本，design=修改设计文件
    }

    响应：
    {
        "success": true,
        "improved_shots": [...],  // 改进后的镜头
        "design_changes": [...]  // 如果improve_type=design，返回需要修改的设计文件
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')
        episode_title = data.get('episode_title', '')
        shots = data.get('shots', [])
        issues = data.get('issues', [])
        improve_type = data.get('improve_type', 'script')

        if not novel_title:
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        logger.info(f"🔧 [剧本改进] 改进项目: {novel_title} - {episode_title}, 类型: {improve_type}")

        # 加载所有小说数据
        novel_data = load_all_novel_data(novel_title)

        # 执行改进
        checker = ScriptQualityChecker(novel_data, novel_title)
        result = checker.improve_script(shots, episode_title, {"issues": issues})

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"剧本改进失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@script_quality_api.route('/api/script/apply-fixes', methods=['POST'])
def apply_script_fixes():
    """
    应用剧本修复并保存到文件

    请求体：
    {
        "novel_title": "小说标题",
        "episode_title": "分集标题",
        "original_shots": [...],  // 原始镜头列表
        "improved_shots": [...],  // 改进后的镜头列表
        "design_changes": [...],  // 需要修改的设计文件
        "apply_design_changes": true/false  // 是否同时修改设计文件
    }

    响应：
    {
        "success": true,
        "shots_saved": true,
        "design_files_updated": ["角色设计.json"],
        "summary": "已保存17个镜头，更新2个设计文件"
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')
        episode_title = data.get('episode_title', '')
        original_shots = data.get('original_shots', [])
        improved_shots = data.get('improved_shots', [])
        design_changes = data.get('design_changes', [])
        apply_design_changes = data.get('apply_design_changes', False)

        if not novel_title:
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        if not improved_shots:
            return jsonify({"success": False, "error": "没有改进后的镜头数据"}), 400

        logger.info(f"💾 [应用修复] 项目: {novel_title} - {episode_title}")
        logger.info(f"   - 原始镜头数: {len(original_shots)}")
        logger.info(f"   - 改进镜头数: {len(improved_shots)}")
        logger.info(f"   - 设计文件变更: {len(design_changes)}")

        # Debug: 打印第一个镜头的数据结构
        if original_shots:
            logger.info(f"   - 原始镜头示例: keys={list(original_shots[0].keys())}, shot_number={original_shots[0].get('shot_number')}")
        if improved_shots:
            logger.info(f"   - 改进镜头示例: keys={list(improved_shots[0].keys())}, index={improved_shots[0].get('index')}")

        updated_files = []
        summary_parts = []

        # 1. 应用镜头改进到原始镜头列表
        for improved_shot in improved_shots:
            idx = improved_shot.get('index', -1)
            if 0 <= idx < len(original_shots):
                # 更新镜头数据
                # 优先使用screen_action（如果_parse_improve_response已经映射了），否则使用description
                if improved_shot.get('screen_action'):
                    original_shots[idx]['screen_action'] = improved_shot['screen_action']
                elif improved_shot.get('description'):
                    original_shots[idx]['screen_action'] = improved_shot['description']

                # description字段也保留（如果有）
                if improved_shot.get('description'):
                    original_shots[idx]['description'] = improved_shot['description']

                if improved_shot.get('veo_prompt'):
                    original_shots[idx]['veo_prompt'] = improved_shot['veo_prompt']
                if improved_shot.get('dialogue'):
                    original_shots[idx]['dialogue'] = improved_shot['dialogue']
                if improved_shot.get('improvement_reason'):
                    original_shots[idx]['improvement_reason'] = improved_shot['improvement_reason']

                logger.info(f"  应用修复 镜头{idx+1}: screen_action存在={bool(original_shots[idx].get('screen_action'))}")

        logger.info(f"应用修复后，第一个镜头screen_action长度: {len(original_shots[0].get('screen_action', '')) if original_shots else 0}")

        summary_parts.append(f"已更新{len(improved_shots)}个镜头")

        # 2. 保存改进后的镜头到文件
        shots_saved = _save_shots_to_file(novel_title, episode_title, original_shots)
        if shots_saved:
            summary_parts.append(f"已保存镜头文件")
        else:
            summary_parts.append(f"镜头文件保存失败（仅内存更新）")

        # 3. 应用设计文件变更
        design_files_updated = []
        if apply_design_changes and design_changes:
            for change in design_changes:
                file_name = change.get('file', '')
                if file_name:
                    updated = _apply_design_file_change(novel_title, change)
                    if updated:
                        design_files_updated.append(file_name)

            if design_files_updated:
                summary_parts.append(f"更新{len(design_files_updated)}个设计文件")
                updated_files.extend(design_files_updated)

        return jsonify({
            "success": True,
            "shots_saved": shots_saved,
            "design_files_updated": design_files_updated,
            "updated_shots": original_shots,  # 返回更新后的镜头列表
            "summary": "、".join(summary_parts)
        }), 200

    except Exception as e:
        logger.error(f"应用修复失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500



def _find_matching_storyboard_file(shot: dict, storyboard_files: list) -> tuple:
    """
    为一个镜头找到匹配的storyboard文件
    返回 (file_path, existing_shot_index, existing_shot) 或 (None, None, None)
    """
    shot_number = shot.get("shot_number")
    shot_veo = shot.get("veo_prompt", "")
    shot_screen = shot.get("screen_action", "")

    # 优先尝试通过 shot_number 匹配，如果多个文件都有相同 shot_number，则通过内容匹配
    best_match = None
    best_score = 0

    for sb_file in storyboard_files:
        try:
            with open(sb_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
        except:
            continue

        existing_shots = file_data.get("shots", [])

        for i, existing_shot in enumerate(existing_shots):
            existing_number = existing_shot.get("shot_number")
            existing_veo = existing_shot.get("veo_prompt", "")
            existing_screen = existing_shot.get("screen_action", "")

            # 计算匹配分数
            score = 0
            if existing_number == shot_number:
                score += 10  # shot_number 匹配

            # veo_prompt 相似度（前50个字符）
            if shot_veo and existing_veo:
                min_len = min(len(shot_veo), len(existing_veo), 50)
                for j in range(min_len):
                    if shot_veo[j] == existing_veo[j]:
                        score += 1
                    else:
                        break

            # screen_action 相似度（前30个字符）
            if shot_screen and existing_screen:
                min_len = min(len(shot_screen), len(existing_screen), 30)
                for j in range(min_len):
                    if shot_screen[j] == existing_screen[j]:
                        score += 1
                    else:
                        break

            if score > best_score:
                best_score = score
                best_match = (sb_file, i, existing_shot)

    # 降低匹配阈值，只要有一些内容相似就匹配
    if best_score >= 20:  # 至少 shot_number 匹配 + 一些内容相似
        return best_match
    return None, None, None


def _save_shots_to_file(novel_title: str, episode_title: str, shots: list) -> bool:
    """保存镜头到视频项目的storyboard文件 - 智能匹配版本"""
    try:
        video_project_path = get_video_project_path()
        logger.info(f"_save_shots_to_file: 视频项目路径 = {video_project_path}, exists={video_project_path.exists()}")
        logger.info(f"_save_shots_to_file: novel_title={novel_title}, episode_title={episode_title}")
        logger.info(f"_save_shots_to_file: shots数量={len(shots)}")

        # 查找视频项目中的分集目录
        episode_dir = None
        if video_project_path.exists():
            # 精确匹配分集目录
            exact_episode = video_project_path / novel_title / episode_title
            logger.info(f"_save_shots_to_file: 精确匹配路径 = {exact_episode}, exists={exact_episode.exists()}")
            if exact_episode.exists():
                episode_dir = exact_episode
                logger.info(f"_save_shots_to_file: 精确匹配找到分集目录: {episode_dir}")
            else:
                # 模糊匹配 - 处理引号等特殊字符差异
                novel_dir = video_project_path / novel_title
                if novel_dir.exists():
                    logger.info(f"_save_shots_to_file: 开始模糊匹配")
                    for item in novel_dir.iterdir():
                        if item.is_dir():
                            item_name = item.name
                            # 直接子串匹配
                            if episode_title in item_name or item_name in episode_title:
                                episode_dir = item
                                logger.info(f"_save_shots_to_file: 模糊匹配找到分集目录: {episode_dir}")
                                break

                    # 如果还是没找到，尝试更宽松的匹配（移除引号）
                    if not episode_dir:
                        logger.info(f"_save_shots_to_file: 尝试宽松匹配")
                        # 标准化episode_title，移除各种引号
                        normalized_title = episode_title.replace("'", "").replace('"', "").replace("'", "").replace('"', "").replace("'", "")
                        for item in novel_dir.iterdir():
                            if item.is_dir():
                                normalized_item = item.name.replace("'", "").replace('"', "").replace("'", "").replace('"', "").replace("'", "")
                                if normalized_title in normalized_item or normalized_item in normalized_title:
                                    episode_dir = item
                                    logger.info(f"_save_shots_to_file: 宽松匹配找到分集目录: {episode_dir}")
                                    break

        if not episode_dir:
            logger.warning(f"未找到分集目录: {novel_title}/{episode_title}")
            return False

        # 查找storyboards目录
        storyboards_dir = episode_dir / "storyboards"
        if not storyboards_dir.exists():
            logger.warning(f"未找到storyboards目录: {storyboards_dir}")
            return False

        logger.info(f"_save_shots_to_file: storyboards目录 = {storyboards_dir}")

        # 获取现有的storyboard文件
        storyboard_files = list(storyboards_dir.glob("*.json"))
        logger.info(f"_save_shots_to_file: 找到 {len(storyboard_files)} 个storyboard文件")

        if not storyboard_files:
            logger.warning(f"_save_shots_to_file: 没有找到storyboard文件")
            return False

        # 统计每个storyboard文件的匹配数量，找到最匹配的文件
        file_match_counts = {}  # {file_path: count}

        for shot in shots:
            sb_file, _, _ = _find_matching_storyboard_file(shot, storyboard_files)
            if sb_file:
                file_match_counts[sb_file] = file_match_counts.get(sb_file, 0) + 1

        logger.info(f"_save_shots_to_file: 文件匹配统计: {[(f.name, c) for f, c in file_match_counts.items()]}")

        if not file_match_counts:
            logger.warning(f"_save_shots_to_file: 没有找到匹配的storyboard文件")
            return False

        # 找到匹配数量最多的文件，只更新这个文件
        best_file = max(file_match_counts.items(), key=lambda x: x[1])[0]
        logger.info(f"_save_shots_to_file: 选择最匹配的文件: {best_file.name} (匹配{file_match_counts[best_file]}个镜头)")

        # 只更新最匹配的文件
        try:
            with open(best_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
        except:
            logger.warning(f"无法读取文件: {best_file.name}")
            return False

        existing_shots = file_data.get("shots", [])
        updated = False

        for shot in shots:
            _, shot_idx, existing_shot = _find_matching_storyboard_file(shot, [best_file])
            if shot_idx is not None and 0 <= shot_idx < len(existing_shots):
                existing_shot = existing_shots[shot_idx]

                # 更新字段
                if shot.get("screen_action"):
                    old_action = existing_shot.get("screen_action", "")
                    existing_shot["screen_action"] = shot["screen_action"]
                    logger.info(f"  ✅ 更新镜头 {shot.get('shot_number')} ({shot_idx}): screen_action {len(old_action)}->{len(shot['screen_action'])}")
                    updated = True
                if shot.get("veo_prompt"):
                    existing_shot["veo_prompt"] = shot["veo_prompt"]
                if shot.get("dialogue"):
                    existing_shot["dialogue"] = shot["dialogue"]
                if shot.get("shot_type"):
                    existing_shot["shot_type"] = shot["shot_type"]
                if shot.get("duration"):
                    existing_shot["duration"] = shot["duration"]

        if updated:
            # 保存文件
            with open(best_file, 'w', encoding='utf-8') as f:
                json.dump(file_data, f, ensure_ascii=False, indent=2)
            logger.info(f"  ✅ 已保存文件: {best_file.name}")
            return True
        else:
            logger.warning(f"没有镜头需要更新")
            return False

    except Exception as e:
        logger.error(f"保存镜头文件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _apply_design_file_change(novel_title: str, change: dict) -> bool:
    """应用设计文件变更"""
    try:
        file_name = change.get('file', '')
        suggestion = change.get('suggestion', '')
        issue = change.get('issue', '')

        logger.info(f"_apply_design_file_change: file={file_name}, issue={issue}, suggestion={suggestion[:100] if suggestion else ''}")

        if not suggestion:
            logger.warning("_apply_design_file_change: 缺少suggestion内容")
            return False

        project_dir = find_project_dir_by_title(novel_title)
        if not project_dir:
            logger.warning(f"_apply_design_file_change: 未找到项目目录: {novel_title}")
            return False

        logger.info(f"_apply_design_file_change: 项目目录 = {project_dir}")

        # 确定要修改的目标文件
        design_file = None

        # 如果AI提到"剧本正文"或"剧本"，这通常意味着需要更新角色设计文件中的信息
        if '剧本' in file_name or '正文' in file_name or 'script' in file_name.lower():
            # 检查是否涉及角色姓名问题
            if '角色' in issue or '姓名' in issue or '林啸天' in suggestion or '叶辰' in suggestion or '林战' in suggestion or '叶凡' in suggestion:
                # 应该更新角色设计文件
                char_file = project_dir / "characters" / f"{novel_title}_角色设计.json"
                if char_file.exists():
                    design_file = char_file
                    logger.info(f"_apply_design_file_change: 角色姓名问题，使用角色设计文件: {design_file}")
                else:
                    # 尝试模糊匹配
                    for f in project_dir.rglob("*角色*.json"):
                        if f.is_file():
                            design_file = f
                            logger.info(f"_apply_design_file_change: 模糊匹配找到角色文件: {design_file}")
                            break

        # 如果还没找到，尝试精确匹配
        if not design_file:
            # 移除文件扩展名进行匹配
            file_stem = file_name.replace('.md', '').replace('.json', '').replace('剧本', '')

            # 常见路径
            possible_paths = [
                project_dir / "characters" / f"{novel_title}_角色设计.json",
                project_dir / "characters" / f"{file_stem}_角色设计.json",
                project_dir / "characters" / f"{novel_title}_{file_stem}.json",
                project_dir / "worldview" / f"{novel_title}_世界观.json",
                project_dir / "worldview" / f"{file_stem}_世界观.json",
                project_dir / "materials" / "phase_one_products" / f"{novel_title}_角色设计.json",
            ]

            for path in possible_paths:
                if path.exists():
                    design_file = path
                    logger.info(f"_apply_design_file_change: 精确匹配找到文件: {design_file}")
                    break

        # 如果还没找到，使用rglob模糊匹配
        if not design_file:
            keywords = ['角色', 'character', '世界观', 'worldview', '成长', 'growth']
            for keyword in keywords:
                if keyword in file_name.lower() or keyword in issue or keyword in suggestion:
                    for f in project_dir.rglob("*.json"):
                        if keyword in f.name.lower() or f'_{keyword}' in f.name.lower():
                            design_file = f
                            logger.info(f"_apply_design_file_change: 关键词匹配找到文件: {design_file}")
                            break
                if design_file:
                    break

        # 最后的默认：使用角色设计文件
        if not design_file:
            char_file = project_dir / "characters" / f"{novel_title}_角色设计.json"
            if char_file.exists():
                design_file = char_file
                logger.info(f"_apply_design_file_change: 默认使用角色设计文件: {design_file}")

        if not design_file:
            logger.warning(f"未找到设计文件: {file_name}")
            return False

        # 读取现有数据
        with open(design_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"_apply_design_file_change: 已读取文件，当前数据keys: {list(data.keys())}")

        # 添加改进建议注释
        if '_improvement_notes' not in data:
            data['_improvement_notes'] = []

        note = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "file_reference": file_name,
            "issue": issue,
            "suggestion": suggestion,
            "applied": True
        }
        data['_improvement_notes'].append(note)

        # 如果是角色姓名问题，也可以在文件中添加一个标记
        if '角色' in issue or '姓名' in issue:
            if '_pending_changes' not in data:
                data['_pending_changes'] = []
            data['_pending_changes'].append({
                "type": "character_name_consistency",
                "description": issue,
                "suggestion": suggestion,
                "timestamp": note["timestamp"]
            })

        # 保存更新后的文件
        with open(design_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 设计文件已更新: {design_file}")
        return True

    except Exception as e:
        logger.error(f"更新设计文件失败 {file_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


@script_quality_api.route('/api/script/check-design-consistency', methods=['POST'])
def check_design_consistency():
    """
    检查原始设计文件的一致性问题

    请求体：
    {
        "novel_title": "小说标题"
    }

    响应：
    {
        "success": true,
        "design_issues": [
            {
                "file": "角色设计.json",
                "issue_type": "character_inconsistency",
                "description": "主角在不同阶段的性格描述不一致",
                "suggestion": "统一主角的性格设定，确保成长路线合理"
            }
        ]
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')

        if not novel_title:
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        logger.info(f"🔍 [设计一致性检查] 检查项目: {novel_title}")

        # 加载所有小说数据
        novel_data = load_all_novel_data(novel_title)

        # 检查设计一致性
        checker = ScriptQualityChecker(novel_data, novel_title)
        issues = checker.check_design_consistency()

        return jsonify({"success": True, "design_issues": issues}), 200

    except Exception as e:
        logger.error(f"设计一致性检查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


class ScriptQualityChecker:
    """剧本质量检查器 - 使用AI进行智能评估"""

    # 质量权重配置
    WEIGHTS = {
        "worldview_consistency": 0.25,     # 世界观一致性 25%
        "character_consistency": 0.30,     # 角色一致性 30%
        "plot_logic": 0.25,                # 情节逻辑 25%
        "market_alignment": 0.10,          # 市场定位契合度 10%
        "visual_feasibility": 0.10,        # 视觉呈现可行性 10%
    }

    def __init__(self, novel_data: Dict, novel_title: str):
        self.novel_data = novel_data
        self.novel_title = novel_title

        # 提取各类数据
        self.project_info = novel_data.get("project_info", {})
        self.worldview = novel_data.get("worldview", {})
        self.characters = novel_data.get("characters", {})
        self.growth_plan = novel_data.get("growth_plan", {})
        self.market_analysis = novel_data.get("market_analysis", {})
        self.stage_plans = novel_data.get("stage_plans", {})

        # 预处理数据，构建检查用的上下文
        self._init_context()

    def _init_context(self):
        """初始化检查上下文"""
        # 提取基本信息
        self.novel_category = self.project_info.get("category", "玄幻")
        self.synopsis = self.project_info.get("synopsis", "")

        # 提取世界观信息
        self.era = self.worldview.get("era", "")
        self.core_conflict = self.worldview.get("core_conflict", "")
        self.overview = self.worldview.get("overview", "")
        self.hot_elements = self.worldview.get("hot_elements", [])
        self.power_system = self.worldview.get("power_system", "")
        self.social_structure = self.worldview.get("social_structure", "")
        self.main_plot_direction = self.worldview.get("main_plot_direction", "")

        # 提取角色信息
        self.main_character = self.characters.get("main_character", {})
        self.important_characters = self.characters.get("important_characters", [])

        # 提取成长路线信息
        self.stage_framework = self.growth_plan.get("stage_framework", {})
        self.character_growth_arcs = self.growth_plan.get("character_growth_arcs", {})
        self.emotional_development = self.growth_plan.get("emotional_development_journey", {})

        # 提取市场分析信息
        self.target_audience = self.market_analysis.get("target_audience", "")
        self.core_selling_points = self.market_analysis.get("core_selling_points", [])
        self.market_trends = self.market_analysis.get("market_trend_analysis", "")

    def _build_worldview_context(self) -> str:
        """构建世界观上下文"""
        if not self.worldview:
            return "暂无世界观信息"

        parts = []
        parts.append(f"## 世界观设定")
        parts.append(f"- 时代背景: {self.era}")
        parts.append(f"- 核心冲突: {self.core_conflict}")
        parts.append(f"- 世界概述: {self.overview}")
        parts.append(f"- 热门元素: {', '.join(self.hot_elements) if isinstance(self.hot_elements, list) else self.hot_elements}")
        parts.append(f"- 力量体系: {self.power_system}")
        parts.append(f"- 社会结构: {self.social_structure}")
        parts.append(f"- 主线方向: {self.main_plot_direction}")

        return "\n".join(parts)

    def _build_character_context(self) -> str:
        """构建角色上下文"""
        if not self.characters:
            return "暂无角色信息"

        parts = []

        # 主角信息
        if self.main_character:
            parts.append(f"## 主角设定")
            parts.append(f"- 姓名: {self.main_character.get('name', '未命名')}")
            parts.append(f"- 核心性格: {self.main_character.get('core_personality', '')}")

            living_chars = self.main_character.get("living_characteristics", {})
            if living_chars:
                parts.append(f"- 外形特征: {living_chars.get('physical_presence', '')}")
                parts.append(f"- 日常习惯: {', '.join(living_chars.get('daily_habits', []))}")
                parts.append(f"- 说话风格: {living_chars.get('speech_patterns', '')}")
                parts.append(f"- 情感触发点: {living_chars.get('emotional_triggers', '')}")

            soul_matrix = self.main_character.get("soul_matrix", [])
            if soul_matrix:
                parts.append(f"- 核心特质:")
                for trait in soul_matrix:
                    if isinstance(trait, dict):
                        parts.append(f"  * {trait.get('core_trait', '')}: {trait.get('behavioral_manifestations', [])}")
                    elif isinstance(trait, str):
                        parts.append(f"  * {trait}")

            parts.append(f"- 成长弧光: {self.main_character.get('growth_arc', '')}")
            parts.append(f"- 对话示例: {self.main_character.get('dialogue_style_example', '')}")

        # 重要角色信息
        if self.important_characters:
            parts.append(f"\n## 重要角色设定")
            for char in self.important_characters[:10]:  # 限制数量
                parts.append(f"\n### {char.get('name', '未命名')}")
                parts.append(f"- 角色: {char.get('role', '')}")
                parts.append(f"- 初始状态: {char.get('initial_state', {}).get('description', '')}")
                parts.append(f"- 修为等级: {char.get('initial_state', {}).get('cultivation_level', '')}")

                soul_matrix = char.get("soul_matrix", [])
                if soul_matrix:
                    first_trait = soul_matrix[0]
                    if isinstance(first_trait, dict):
                        parts.append(f"- 核心特质: {first_trait.get('core_trait', '')}")
                    elif isinstance(first_trait, str):
                        parts.append(f"- 核心特质: {first_trait}")

                dialogue = char.get("dialogue_style_example", "")
                if dialogue:
                    parts.append(f"- 对话风格: {dialogue}")

        return "\n".join(parts)

    def _build_growth_context(self) -> str:
        """构建成长路线上下文"""
        if not self.growth_plan:
            return "暂无成长路线信息"

        parts = []
        parts.append(f"## 角色成长路线")

        # 阶段框架
        if self.stage_framework:
            for stage_key, stage_data in self.stage_framework.items():
                if isinstance(stage_data, dict):
                    parts.append(f"\n### {stage_data.get('stage_name', stage_key)}")
                    parts.append(f"- 章节范围: {stage_data.get('chapter_range', '')}")
                    parts.append(f"- 核心目标: {', '.join(stage_data.get('core_objectives', []))}")
                    parts.append(f"- 成长主题: {', '.join(stage_data.get('key_growth_themes', []))}")

        # 主角成长弧光
        if self.character_growth_arcs:
            protagonist_arc = self.character_growth_arcs.get("protagonist", {})
            if protagonist_arc:
                parts.append(f"\n### 主角成长弧光")
                parts.append(f"- 整体弧光: {protagonist_arc.get('overall_arc', '')}")
                stage_growth = protagonist_arc.get("stage_specific_growth", {})
                if stage_growth:
                    for stage, growth in stage_growth.items():
                        parts.append(f"- {stage}: {growth.get('personality_development', '')}")

        return "\n".join(parts)

    def _build_market_context(self) -> str:
        """构建市场定位上下文"""
        if not self.market_analysis:
            return "暂无市场分析信息"

        parts = []
        parts.append(f"## 市场定位分析")
        parts.append(f"- 目标受众: {self.target_audience}")

        if self.core_selling_points:
            parts.append(f"- 核心卖点:")
            for i, point in enumerate(self.core_selling_points, 1):
                parts.append(f"  {i}. {point}")

        parts.append(f"- 市场趋势: {self.market_trends}")

        return "\n".join(parts)

    def _build_script_summary(self, shots: List[Dict], episode_title: str) -> str:
        """构建剧本摘要"""
        parts = []

        parts.append(f"# 剧本质量检查任务")
        parts.append(f"\n## 基本信息")
        parts.append(f"- 小说标题: {self.novel_title}")
        parts.append(f"- 分集标题: {episode_title}")
        parts.append(f"- 类型: {self.novel_category}")
        parts.append(f"- 镜头数量: {len(shots)}")

        # 添加完整的项目上下文
        parts.append(f"\n{self._build_worldview_context()}")
        parts.append(f"\n{self._build_character_context()}")
        parts.append(f"\n{self._build_growth_context()}")
        parts.append(f"\n{self._build_market_context()}")

        # 添加镜头脚本
        parts.append(f"\n## 待检查镜头脚本")
        parts.append(f"以下是当前分集的镜头列表，请检查其与上述设定的一致性：\n")

        for idx, shot in enumerate(shots[:50]):  # 分析最多50个镜头
            # Defensive: ensure shot is a dict
            if not isinstance(shot, dict):
                logger.warning(f"  跳过非字典类型的镜头: {type(shot)}")
                continue
            desc = shot.get("description", "")
            prompt_text = shot.get("veo_prompt", "") or shot.get("generation_prompt", "") or shot.get("screen_action", "")
            shot_type = shot.get("shot_type", "中景")
            scene = shot.get("scene", "")
            character = shot.get("character", "")
            action = shot.get("action", "")
            dialogue = shot.get("dialogue", "")

            parts.append(f"\n### 镜头{idx + 1} ({shot_type})")
            if scene:
                parts.append(f"- 场景: {scene}")
            if character:
                parts.append(f"- 角色: {character}")
            if action:
                parts.append(f"- 动作: {action}")
            if dialogue:
                parts.append(f"- 对话: {dialogue}")
            parts.append(f"- 描述: {desc}")
            if prompt_text and prompt_text != desc:
                parts.append(f"- 生成提示词: {prompt_text}")

        if len(shots) > 50:
            parts.append(f"\n... (还有 {len(shots) - 50} 个镜头未列出)")

        return "\n".join(parts)

    def check_with_timeout(self, shots: List[Dict], episode_title: str = "", timeout: int = 30) -> Dict:
        """
        使用AI执行剧本质量检查（带超时保护）

        Args:
            shots: 镜头列表
            episode_title: 分集标题
            timeout: 超时时间（秒）
        """
        import threading
        import queue

        result_queue = queue.Queue()

        def worker():
            try:
                result = self.check(shots, episode_title)
                result_queue.put(result)
            except Exception as e:
                logger.error(f"AI检查异常: {e}")
                result_queue.put(self._basic_check(shots, episode_title))

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

        # 等待结果或超时
        thread.join(timeout=timeout)

        if thread.is_alive():
            logger.warning(f"AI检查超时（{timeout}秒），使用基础检查")
            # 线程仍在运行，返回基础检查结果
            return self._basic_check(shots, episode_title)

        try:
            return result_queue.get_nowait()
        except queue.Empty:
            return self._basic_check(shots, episode_title)

    def check(self, shots: List[Dict], episode_title: str = "") -> Dict:
        """
        使用AI执行剧本质量检查

        返回:
            {
                "passed": bool,
                "score": int,
                "detailed_scores": dict,
                "issues": List[Dict],
                "warnings": List[Dict],
                "recommendations": List[str]
            }
        """
        try:
            from src.core.APIClient import APIClient
            from config.config import CONFIG

            ai_client = APIClient(CONFIG)

            # 构建剧本摘要
            script_summary = self._build_script_summary(shots, episode_title)

            # 构建AI提示词
            user_prompt = self._build_quality_check_prompt(script_summary, episode_title)
            system_prompt = """你是一位专业的剧本质量评估专家，精通小说改编、角色一致性检查、世界观设定分析。你需要严格检查剧本与原始设计文件的一致性，找出所有不一致之处。"""

            # 调用AI进行分析
            logger.info(f"🤖 正在调用AI进行剧本质量评估...")
            response = ai_client.call_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                purpose="剧本质量检查"
            )

            if not response:
                logger.warning("AI调用失败，返回空响应")
                return self._basic_check(shots, episode_title)

            logger.info(f"🤖 AI响应: {response[:500]}...")

            # 解析AI响应
            result = self._parse_ai_response(response)

            return result

        except Exception as e:
            logger.error(f"AI质量检查失败，使用基础检查: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # AI失败时使用基础检查
            return self._basic_check(shots, episode_title)

    def _build_quality_check_prompt(self, script_summary: str, episode_title: str) -> str:
        """构建质量检查提示词"""
        # 获取世界一致性要求
        world_requirements = self._get_world_consistency_requirements()

        return f"""请对以下视频剧本进行全面的质量评估。

{script_summary}

## 【世界一致性强制检查标准】
每个镜头必须符合以下世界观设定，请在评分时严格检查：
{world_requirements}

请从以下5个维度进行评估（每项0-100分）：

1. **世界观一致性** (25%权重)
   - 场景元素是否符合世界观设定（时代背景、力量体系、社会结构）
   - 是否出现与世界观冲突的元素
   - 场景转换是否符合世界逻辑
   - **每个镜头是否包含体现世界观的描述细节**

2. **角色一致性** (30%权重)
   - 角色行为是否符合其性格设定（核心特质、行为表现）
   - 角色外观描述是否一致
   - 角色对话风格是否符合设定
   - 角色成长是否符合成长路线规划
   - 是否出现未定义的角色

3. **情节逻辑** (25%权重)
   - 情节发展是否合理
   - 镜头之间是否有逻辑连贯性
   - 场景转换是否自然
   - 是否符合主线方向

4. **市场定位契合度** (10%权重)
   - 剧情是否体现核心卖点
   - 是否符合目标受众偏好
   - 热门元素是否得到体现

5. **视觉呈现可行性** (10%权重)
   - 描述是否足够生动具体
   - 是否便于视频生成
   - 镜头类型是否恰当

请严格按照以下JSON格式回复，不要添加任何其他内容：

```json
{{
    "worldview_consistency": {{
        "score": 85,
        "issues": ["具体问题描述1", "具体问题描述2"],
        "praise": ["做得好的地方1"]
    }},
    "character_consistency": {{
        "score": 90,
        "issues": [],
        "praise": ["角色性格一致"]
    }},
    "plot_logic": {{
        "score": 80,
        "issues": ["镜头3到镜头4的转换突兀"],
        "praise": []
    }},
    "market_alignment": {{
        "score": 75,
        "issues": ["核心卖点体现不足"],
        "praise": []
    }},
    "visual_feasibility": {{
        "score": 85,
        "issues": [],
        "praise": ["画面感强"]
    }},
    "overall_recommendations": ["改进建议1", "改进建议2"],
    "design_file_issues": [
        {{
            "file": "世界观设定",
            "issue_type": "missing_info",
            "description": "如果评分低是因为原始设计信息缺失，请指出",
            "suggestion": "建议补充的内容"
        }}
    ]
}}
```

注意：
- 评分要客观公正，不要轻易给满分
- 问题要具体，指出具体哪个镜头、哪行描述有问题
- 如果发现是原始设计文件的问题（如角色设定矛盾、世界观缺失），请在design_file_issues中列出
- 如果评分低于80分，必须在overall_recommendations中给出具体可行的改进建议
"""

    def _parse_ai_response(self, response: str) -> Dict:
        """解析AI响应"""
        import re

        # 尝试提取JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = response.strip()

        try:
            data = json.loads(json_str)

            # 提取各维度评分
            scores = {}
            issues = []
            warnings = []
            recommendations = []
            design_issues = []

            for category in ["worldview_consistency", "character_consistency", "plot_logic",
                            "market_alignment", "visual_feasibility"]:
                if category in data:
                    cat_data = data[category]
                    scores[category] = cat_data.get("score", 70)

                    # 转换问题为标准格式
                    for issue in cat_data.get("issues", []):
                        severity = "critical" if scores[category] < 60 else "warning" if scores[category] < 80 else "info"
                        issues.append({
                            "severity": severity,
                            "category": category,
                            "message": issue,
                            "suggestion": f"请优化{category}相关内容"
                        })

            # 添加总体建议
            recommendations.extend(data.get("overall_recommendations", []))

            # 添加设计文件问题
            design_issues.extend(data.get("design_file_issues", []))

            # 计算总分
            total_score = sum(
                scores.get(cat, 70) * self.WEIGHTS.get(cat, 0.2)
                for cat in scores
            )

            # 判断是否通过
            severe_issues = [i for i in issues if i.get("severity") == "critical"]
            passed = total_score >= 80 and len(severe_issues) == 0

            return {
                "success": True,
                "passed": passed,
                "score": round(total_score),
                "detailed_scores": {k: round(v) for k, v in scores.items()},
                "issues": issues,
                "warnings": warnings,
                "recommendations": recommendations,
                "design_file_issues": design_issues
            }

        except json.JSONDecodeError as e:
            logger.warning(f"AI响应JSON解析失败: {e}, 响应内容: {response[:500]}")
            # 返回默认结果
            return {
                "success": True,
                "passed": True,
                "score": 70,
                "detailed_scores": {},
                "issues": [],
                "warnings": [{"message": "AI解析失败，请手动检查"}],
                "recommendations": ["请检查剧本质量"],
                "design_file_issues": []
            }

    def _basic_check(self, shots: List[Dict], episode_title: str) -> Dict:
        """基础检查（AI失败时的备用方案）"""
        issues = []
        warnings = []
        recommendations = []

        if len(shots) == 0:
            issues.append({
                "severity": "critical",
                "category": "plot_logic",
                "message": "没有镜头数据",
                "suggestion": "请先生成镜头数据"
            })
            return {
                "success": True,
                "passed": False,
                "score": 0,
                "detailed_scores": {},
                "issues": issues,
                "warnings": warnings,
                "recommendations": recommendations,
                "design_file_issues": []
            }

        # 检查镜头描述长度
        short_descriptions = 0
        for shot in shots:
            desc = shot.get("description", "")
            if len(desc) < 10:
                short_descriptions += 1

        if short_descriptions > len(shots) * 0.5:
            issues.append({
                "severity": "warning",
                "category": "visual_feasibility",
                "message": f"有{short_descriptions}个镜头描述过短",
                "suggestion": "建议增加更多细节描述"
            })

        score = max(60, 100 - short_descriptions * 5)

        return {
            "success": True,
            "passed": score >= 60,
            "score": score,
            "detailed_scores": {},
            "issues": issues,
            "warnings": warnings,
            "recommendations": ["建议使用AI检查功能获得详细分析"],
            "design_file_issues": []
        }

    def improve_script(self, shots: List[Dict], episode_title: str, check_result: Dict) -> Dict:
        """
        改进剧本

        返回:
            {
                "improved_shots": [...],  # 改进后的镜头
                "improvements_summary": str,  # 改进摘要
                "design_changes": [...]  # 需要修改的设计文件
            }
        """
        try:
            from src.core.APIClient import APIClient
            from config.config import CONFIG

            ai_client = APIClient(CONFIG)

            # 构建改进提示词
            issues = check_result.get("issues", [])
            recommendations = check_result.get("recommendations", [])

            # 构建原始剧本摘要
            script_summary = self._build_script_summary(shots, episode_title)

            # 构建问题摘要
            issues_summary = "\n".join([
                f"- {i.get('category', 'unknown')}: {i.get('message', str(i))}" if isinstance(i, dict) else f"- {i}"
                for i in issues
            ])
            recommendations_summary = "\n".join([
                f"{i+1}. {r if isinstance(r, str) else str(r)}"
                for i, r in enumerate(recommendations)
            ])

            # 获取视觉化的世界观元素
            visual_world_elements = self._get_visual_world_elements()

            # 获取角色名称映射
            character_name_mapping = self._get_character_name_mapping()

            user_prompt = f"""任务：改进以下{len(shots)}个镜头的剧本描述。

## 当前剧本（{len(shots)}个镜头）
{script_summary}

## 需要改进的问题
{issues_summary}

## 【强制】角色名称要求 - 必须使用正确的角色名
以下角色名称必须准确使用，不可使用通用称呼（如"族长"、"少年"、"主角"等）：
{character_name_mapping}

**注意：**
- 必须使用角色具体名字，不能用"族长"、"少年"、"主角"等通用称呼
- 例如：用"林战"而不是"族长"，用"叶凡"而不是"少年"或"叶辰"

## 【强制】世界一致性要求 - 每个镜头必须包含
{self._get_world_consistency_requirements()}

## 【重要】veo_prompt必须包含的视觉元素
为确保所有镜头生成的视频画面处于同一个世界，每个镜头的veo_prompt**必须**包含以下视觉元素：
**{visual_world_elements}**

这些视觉元素应该自然融入到每个镜头的画面描述中，确保所有镜头的视频风格统一。

## 你的任务
请对上述全部{len(shots)}个镜头逐一进行改进，每个镜头都要生成更详细、更有画面感的描述。

**关键要求：**
1. 每个镜头的screen_action描述必须融入世界观元素
2. **每个镜头的veo_prompt必须包含统一的视觉世界观元素**（{visual_world_elements}），确保所有镜头生成的视频画面风格一致
3. **必须使用具体的角色名字，禁止使用"族长"、"少年"、"主角"等通用称呼**
4. veo_prompt应该用简体中文描述，包含：场景环境+人物动作+视觉氛围+世界览权重元素
5. 突出"迪化流"、"偷听心声"等特色元素的视觉表现

【强制要求】你必须返回JSON格式的结果，其中improved_shots数组必须包含全部{len(shots)}个镜头，不能缺少任何一个！

JSON格式示例：
```json
{{
    "improved_shots": [
        {{
            "index": 1,
            "description": "第1个镜头的详细改进描述（中文），使用具体角色名字...",
            "veo_prompt": "第1个镜头的简体中文提示词，必须包含{visual_world_elements}等视觉元素，使用具体角色名字...",
            "improvement_reason": "改进原因"
        }},
        {{
            "index": 2,
            "description": "第2个镜头的详细改进描述（中文），使用具体角色名字...",
            "veo_prompt": "第2个镜头的简体中文提示词，必须包含{visual_world_elements}等视觉元素，使用具体角色名字...",
            "improvement_reason": "改进原因"
        }}
        // ... 继续到第{len(shots)}个镜头
    ],
    "improvements_summary": "本次改进的整体说明",
    "design_change_suggestions": []
}}
```

请直接返回上述JSON格式，不要添加任何其他文字说明。"""

            system_prompt = f"""你是一位专业的剧本编辑，擅长根据反馈改进剧本质量。你深刻理解世界观设定、角色一致性、情节逻辑，能够精准地修正问题。

【最关键指令】你必须严格按照用户要求的JSON格式返回结果，不能有任何文字说明在JSON之外。improved_shots数组必须包含全部镜头的改进内容，绝对不能为空。每个镜头都必须包含详细的改进后描述。

【角色名称强制要求】所有角色必须使用具体名字，禁止使用通用称呼如"族长"、"少年"、"主角"等。例如：
- 用"林战"而不是"族长"
- 用"叶凡"而不是"少年"或"主角"

【veo_prompt关键要求】每个镜头的veo_prompt必须：
1. 使用简体中文描述
2. 包含统一的视觉世界观元素：{visual_world_elements}
3. 使用具体角色名字，不用通用称呼
这确保所有镜头生成的视频画面风格一致，处于同一个世界中。

注意：index从1开始编号（第1个镜头用index:1，第2个用index:2，以此类推）。"""

            logger.info(f"🔧 正在调用AI改进剧本...")
            response = ai_client.call_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5,
                purpose="剧本改进"
            )

            if not response:
                logger.error("AI改进失败：返回空响应")
                return {
                    "improved_shots": [],
                    "improvements_summary": "AI改进失败：返回空响应",
                    "design_changes": []
                }

            logger.info(f"AI改进响应长度: {len(response)}")

            # 使用APIClient的JSON解析方法
            parsed_data = ai_client.parse_json_response(response)

            if not parsed_data:
                logger.error(f"AI改进响应JSON解析失败，响应前500字符: {response[:500]}")
                return {
                    "improved_shots": [],
                    "improvements_summary": "AI返回内容无法解析",
                    "design_changes": []
                }

            improved_shots_data = parsed_data.get("improved_shots", [])
            improved_shots = []

            logger.info(f"_parse_improve_response: improved_shots数量={len(improved_shots_data)}")

            if len(improved_shots_data) == 0:
                logger.error(f"AI未返回任何改进镜头! 完整响应前1000字符: {response[:1000]}")
                return {
                    "improved_shots": [],
                    "improvements_summary": parsed_data.get("improvements_summary", "AI未返回改进内容"),
                    "design_changes": parsed_data.get("design_change_suggestions", [])
                }

            for item in improved_shots_data:
                idx = item.get("index", -1)
                logger.info(f"  处理镜头: index={idx}, 有description={bool(item.get('description'))}")

                # AI返回的index是1-based（1表示第一个镜头），转换为0-based
                if idx > 0:
                    array_idx = idx - 1
                elif idx == 0:
                    array_idx = 0
                else:
                    logger.warning(f"  跳过无效index: {idx}")
                    continue

                if 0 <= array_idx < len(shots):
                    # 创建改进后的镜头
                    improved_shot = shots[array_idx].copy()
                    improved_shot["index"] = array_idx
                    improved_shot["original_index"] = idx

                    # AI返回的是description，需要映射到screen_action
                    if item.get("description"):
                        improved_shot["screen_action"] = item["description"]
                        improved_shot["description"] = item["description"]
                    if item.get("veo_prompt"):
                        improved_shot["veo_prompt"] = item["veo_prompt"]
                    improved_shot["improvement_reason"] = item.get("improvement_reason", "")
                    improved_shots.append(improved_shot)
                    logger.info(f"  ✅ 解析镜头 {idx}: screen_action长度={len(improved_shot.get('screen_action', ''))}")
                else:
                    logger.warning(f"  索引 {array_idx} 超出范围 (0-{len(shots)-1})")

            design_changes = []
            for change in parsed_data.get("design_change_suggestions", []):
                # Defensive: handle both dict and string types
                if isinstance(change, dict):
                    design_changes.append({
                        "file": change.get("file", ""),
                        "issue": change.get("issue", ""),
                        "suggestion": change.get("suggestion", "")
                    })
                elif isinstance(change, str):
                    design_changes.append({
                        "file": "",
                        "issue": "",
                        "suggestion": change
                    })

            logger.info(f"_parse_improve_response: 解析到 {len(improved_shots)} 个改进镜头")

            return {
                "improved_shots": improved_shots,
                "improvements_summary": parsed_data.get("improvements_summary", ""),
                "design_changes": design_changes
            }

        except Exception as e:
            logger.error(f"剧本改进失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

            return {
                "improved_shots": [],
                "improvements_summary": f"改进失败: {str(e)}",
                "design_changes": []
            }

    def _get_world_consistency_requirements(self) -> str:
        """获取世界一致性要求，用于改进剧本时强制包含"""
        requirements = []

        # 时代背景
        if self.era:
            requirements.append(f"- **时代背景**: {self.era}")

        # 核心冲突
        if self.core_conflict:
            requirements.append(f"- **核心冲突**: {self.core_conflict}")

        # 热门元素
        if self.hot_elements:
            elements_str = "、".join(self.hot_elements) if isinstance(self.hot_elements, list) else str(self.hot_elements)
            requirements.append(f"- **热门元素**: {elements_str}")

        # 力量体系特征
        if self.power_system:
            requirements.append(f"- **力量体系**: {self.power_system}")

        # 社会结构
        if self.social_structure:
            requirements.append(f"- **社会结构**: {self.social_structure}")

        # 主线方向
        if self.main_plot_direction:
            # 取初期部分作为当前阶段参考
            early_plot = self.main_plot_direction.split("；")[0] if "；" in self.main_plot_direction else self.main_plot_direction
            requirements.append(f"- **主线方向**: {early_plot}")

        if not requirements:
            return "- 暂无世界观设定要求"

        return "\n".join(requirements)

    def _get_visual_world_elements(self) -> str:
        """获取视觉化的世界观元素，用于veo_prompt确保画面风格统一"""
        visual_elements = []

        # 从时代背景提取视觉元素
        if self.era:
            if "东方玄幻" in self.era or "修仙" in self.era:
                visual_elements.append("东方玄幻修仙世界风格")
                visual_elements.append("灵气氤氲的氛围")
                visual_elements.append("古典仙侠建筑风格")
            if "高武" in self.era:
                visual_elements.append("高武世界的气势恢宏")
                visual_elements.append("强者威压的视觉表现")

        # 从力量体系提取视觉元素
        if self.power_system and ("灵气" in self.power_system or "修仙" in self.power_system):
            visual_elements.append("空气中弥漫的灵气粒子效果")
            visual_elements.append("修仙者的气场光晕")

        # 从社会结构提取视觉元素
        if self.social_structure:
            if "黑暗森林" in self.social_structure:
                visual_elements.append("压抑紧张的环境氛围")
                visual_elements.append("危机四伏的世界观")

        # 如果没有提取到任何元素，使用默认
        if not visual_elements:
            visual_elements = [
                "东方玄幻修仙世界风格",
                "灵气氤氲的氛围",
                "古典仙侠建筑风格"
            ]

        return "、".join(visual_elements)

    def _get_character_name_mapping(self) -> str:
        """获取角色名称映射，确保生成时使用正确的角色名"""
        name_info = []

        # 主角信息
        if self.main_character:
            main_name = self.main_character.get("name", "")
            if main_name:
                name_info.append(f"主角：{main_name}")
                # 添加外形特征描述，帮助AI识别
                living_chars = self.main_character.get("living_characteristics", {})
                physical = living_chars.get("physical_presence", "")
                if physical:
                    name_info.append(f"  - 外形：{physical}")

        # 重要角色信息
        if self.important_characters:
            name_info.append("\n重要角色：")
            for char in self.important_characters[:15]:  # 限制数量
                char_name = char.get("name", "")
                char_role = char.get("role", "")
                if char_name:
                    desc = char.get("initial_state", {}).get("description", "")
                    name_info.append(f"- {char_name}（{char_role}）")
                    if desc:
                        name_info.append(f"  - 外形：{desc}")

        if not name_info:
            return "暂无角色信息"

        return "\n".join(name_info)

    def check_design_consistency(self) -> List[Dict]:
        """检查设计文件一致性"""
        issues = []

        # 检查角色设定一致性
        if self.main_character:
            name = self.main_character.get("name", "")
            if not name:
                issues.append({
                    "file": "角色设计.json",
                    "issue_type": "missing_info",
                    "description": "主角缺少姓名",
                    "suggestion": "请补充主角姓名"
                })

        # 检查世界观完整性
        if self.worldview:
            if not self.era:
                issues.append({
                    "file": "世界观.json",
                    "issue_type": "missing_info",
                    "description": "世界观缺少时代背景设定",
                    "suggestion": "请补充时代背景(era)字段"
                })
            if not self.core_conflict:
                issues.append({
                    "file": "世界观.json",
                    "issue_type": "missing_info",
                    "description": "世界观缺少核心冲突设定",
                    "suggestion": "请补充核心冲突(core_conflict)字段"
                })

        # 检查成长路线完整性
        if self.growth_plan and not self.stage_framework:
            issues.append({
                "file": "成长路线.json",
                "issue_type": "missing_info",
                "description": "成长路线缺少阶段框架",
                "suggestion": "请补充stage_framework字段"
            })

        # 检查市场分析完整性
        if not self.market_analysis:
            issues.append({
                "file": "市场分析.json",
                "issue_type": "missing_file",
                "description": "缺少市场分析文件",
                "suggestion": "请生成市场分析文件，包含目标受众和核心卖点"
            })

        return issues

    def generate_data_report(self) -> Dict:
        """生成数据报告"""
        return {
            "novel_title": self.novel_title,
            "category": self.novel_category,
            "synopsis": self.synopsis,
            "worldview": {
                "era": self.era,
                "core_conflict": self.core_conflict,
                "overview": self.overview,
                "hot_elements": self.hot_elements,
                "power_system": self.power_system,
                "social_structure": self.social_structure,
                "main_plot_direction": self.main_plot_direction
            },
            "main_character": {
                "name": self.main_character.get("name", ""),
                "core_personality": self.main_character.get("core_personality", ""),
                "living_characteristics": self.main_character.get("living_characteristics", {}),
                "growth_arc": self.main_character.get("growth_arc", "")
            },
            "important_characters_count": len(self.important_characters),
            "character_names": [c.get("name", "") for c in self.important_characters[:10]],
            "growth_stages": list(self.stage_framework.keys()) if self.stage_framework else [],
            "market_analysis": {
                "target_audience": self.target_audience,
                "core_selling_points": self.core_selling_points,
                "market_trends": self.market_trends
            },
            "data_completeness": {
                "project_info": bool(self.project_info),
                "worldview": bool(self.worldview),
                "characters": bool(self.characters),
                "growth_plan": bool(self.growth_plan),
                "market_analysis": bool(self.market_analysis),
                "stage_plans": bool(self.stage_plans)
            }
        }


def register_script_quality_routes(app):
    """注册剧本质量检查路由"""
    app.register_blueprint(script_quality_api)

    logger.info("=" * 60)
    logger.info("📋 已注册剧本质量检查API路由:")
    for rule in app.url_map.iter_rules():
        if 'api/script' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
