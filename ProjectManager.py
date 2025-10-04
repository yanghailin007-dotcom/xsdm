"""项目管理器类 - 专注项目管理"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

class ProjectManager:
    def __init__(self):
        # 内化质量阈值配置
        self.quality_thresholds = {
            "excellent": 9.0,
            "good": 8.5,
            "acceptable": 8.0,
            "needs_optimization": 7.5,
            "needs_rewrite": 6.0
        }
        
        # 其他相关配置
        self.optimization_settings = {
            "quality_thresholds": self.quality_thresholds
        }
    
    def find_existing_projects(self, creative_seed: str = None) -> List[Dict]:
        """查找现有项目"""
        projects = []
        if not os.path.exists("小说项目"):
            return projects
            
        safe_seed = re.sub(r'[\\/*?:"<>|]', "_", creative_seed) if creative_seed else ""
        
        for filename in os.listdir("小说项目"):
            if filename.endswith("_项目信息.json"):
                try:
                    with open(f"小说项目/{filename}", 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    project_seed = data.get("novel_info", {}).get("creative_seed", "")
                    project_title = data.get("novel_info", {}).get("title", "")
                    progress = data.get("progress", {})
                    
                    # 如果提供了creative_seed，只匹配相关项目
                    if creative_seed and safe_seed not in filename and creative_seed != project_seed:
                        continue
                        
                    projects.append({
                        "filename": filename,
                        "title": project_title,
                        "seed": project_seed,
                        "completed_chapters": progress.get("completed_chapters", 0),
                        "total_chapters": progress.get("total_chapters", 0),
                        "stage": progress.get("stage", "未知"),
                        "timestamp": data.get("timestamp", "")
                    })
                except Exception as e:
                    print(f"读取项目文件 {filename} 失败: {e}")
        
        # 按时间倒序排序
        projects.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return projects
    
    def load_project(self, filename: str) -> Optional[Dict]:
        """加载项目数据"""
        try:
            with open(f"小说项目/{filename}", 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 构建完整的novel_data结构
            novel_data = {
                # 基本信息
                "novel_title": project_data["novel_info"]["title"],
                "novel_synopsis": project_data["novel_info"]["synopsis"],
                "creative_seed": project_data["novel_info"]["creative_seed"],
                "selected_plan": project_data["novel_info"]["selected_plan"],
                "category": project_data["novel_info"].get("category", "未分类"),
                
                # 新增：添加novel_info键以保持兼容性
                "novel_info": project_data["novel_info"],
                
                # 核心数据
                "market_analysis": project_data.get("market_analysis", {}),
                "global_growth_plan": project_data.get("global_growth_plan", {}),
                "overall_stage_plans": project_data.get("overall_stage_plans", {}),
                "stage_writing_plans": project_data.get("stage_writing_plans", {}),
                "core_worldview": project_data.get("core_worldview", {}),
                "character_design": project_data.get("character_design", {}),
                
                # 修复：正确加载进度信息
                "current_progress": project_data.get("progress", {
                    "completed_chapters": 0,
                    "total_chapters": 0,
                    "stage": "大纲阶段",
                    "current_stage": "第一阶段"
                }),
                
                # 初始化其他必要字段
                "generated_chapters": {},
                "plot_progression": project_data.get("plot_progression", []),
                "subplot_tracking": project_data.get("subplot_settings", {
                    "ratio": {"emotional": 0.3, "foreshadowing": 0.3},
                    "subplot_chapters": {"emotional": [], "foreshadowing": []}
                }),
                "quality_statistics": project_data.get("quality_statistics", {})
            }
            
            # 加载章节具体内容
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
            chapters_dir = f"小说项目/{safe_title}_章节"
            
            if os.path.exists(chapters_dir):
                generated_chapters = {}
                for chapter_file in os.listdir(chapters_dir):
                    if chapter_file.endswith('.txt'):
                        try:
                            with open(f"{chapters_dir}/{chapter_file}", 'r', encoding='utf-8') as f:
                                chapter_data = json.load(f)
                                chapter_num = chapter_data.get("chapter_number")
                                if chapter_num:
                                    generated_chapters[chapter_num] = {
                                        "chapter_title": chapter_data.get("chapter_title", ""),
                                        "content": chapter_data.get("content", ""),
                                        "word_count": chapter_data.get("word_count", 0),
                                        "quality_assessment": chapter_data.get("quality_assessment", {}),
                                        "optimization_info": chapter_data.get("optimization_info", {}),
                                        "chapter_design": chapter_data.get("chapter_design", {}),
                                        "design_followed": chapter_data.get("design_followed", True),
                                        "base_settings_used": chapter_data.get("base_settings_used", {}),
                                        "key_events": chapter_data.get("key_events", []),
                                        "next_chapter_hook": chapter_data.get("next_chapter_hook", ""),
                                        "connection_to_previous": chapter_data.get("connection_to_previous", ""),
                                        "plot_advancement": chapter_data.get("plot_advancement", ""),
                                        "character_development": chapter_data.get("character_development", ""),
                                        "quality_score": chapter_data.get("quality_score", 0),
                                        "previous_chapter_summary": chapter_data.get("previous_chapter_summary", "")
                                    }
                        except Exception as e:
                            print(f"加载章节文件 {chapter_file} 失败: {e}")
                
                novel_data["generated_chapters"] = generated_chapters
                
                # 修复：如果进度信息中章节数为0，但实际有章节，则更新进度
                if novel_data["current_progress"]["total_chapters"] == 0 and generated_chapters:
                    novel_data["current_progress"]["total_chapters"] = max(generated_chapters.keys())
                    novel_data["current_progress"]["completed_chapters"] = len(generated_chapters)
                    novel_data["current_progress"]["stage"] = "写作中"
                    print(f"🔄 自动修复进度信息: {len(generated_chapters)}/{max(generated_chapters.keys())}章")

            print(f"✓ 项目加载成功: {novel_data['novel_title']}")
            print(f"  - 世界观数据: {len(novel_data['core_worldview'])} 项")
            print(f"  - 角色设定: {len(novel_data['character_design'])} 个角色")
            print(f"  - 写作计划: {len(novel_data['stage_writing_plans'])} 个阶段")
            print(f"  - 已生成章节: {len(novel_data['generated_chapters'])} 章")
            print(f"  - 当前进度: {novel_data['current_progress']['completed_chapters']}/{novel_data['current_progress']['total_chapters']}章")
            print(f"  - 当前阶段: {novel_data['current_progress']['stage']}")

            return novel_data
        except Exception as e:
            print(f"❌❌ 加载项目失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_single_chapter(self, novel_title: str, chapter_number: int, chapter_data: Dict):
        """保存单章内容"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        chapter_dir = f"小说项目/{safe_title}_章节"
        os.makedirs(chapter_dir, exist_ok=True)
        
        # 提取所有章节特定的信息
        chapter_json_data = {
            "chapter_number": chapter_number,
            "chapter_title": chapter_data["chapter_title"],
            "content": chapter_data["content"],
            "word_count": chapter_data.get("word_count", 0),
            "quality_assessment": chapter_data.get("quality_assessment", {}),
            "optimization_info": chapter_data.get("optimization_info", {}),
            "chapter_design": chapter_data.get("chapter_design", {}),
            "design_followed": chapter_data.get("design_followed", True),
            "base_settings_used": chapter_data.get("base_settings_used", {}),
            "generation_time": datetime.now().isoformat(),
            
            # 章节特定的信息
            "key_events": chapter_data.get("key_events", []),
            "next_chapter_hook": chapter_data.get("next_chapter_hook", ""),
            "connection_to_previous": chapter_data.get("connection_to_previous", ""),
            "plot_advancement": chapter_data.get("plot_advancement", ""),
            "character_development": chapter_data.get("character_development", ""),
            
            # 质量评分
            "quality_score": chapter_data.get("quality_assessment", {}).get("overall_score", 0),
            
            # 衔接信息
            "previous_chapter_summary": chapter_data.get("previous_chapters_summary", ""),
        }
        
        try:
            filename = f"{chapter_dir}/第{chapter_number:03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', chapter_data['chapter_title'])}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(chapter_json_data, f, ensure_ascii=False, indent=2)
            print(f"  已保存: {filename}")
        except Exception as e:
            print(f"保存第{chapter_number}章失败: {e}")
    
    def save_project_progress(self, novel_data: Dict):
        """保存项目整体进度"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
        os.makedirs("小说项目", exist_ok=True)
        
        # 计算质量统计
        quality_stats = self.calculate_quality_statistics(novel_data)
        
        # 确保进度信息存在
        current_progress = novel_data.get("current_progress", {
            "completed_chapters": 0,
            "total_chapters": 0,
            "stage": "大纲阶段",
            "current_stage": "第一阶段"
        })
        
        # 如果有章节但进度信息不正确，自动修复
        generated_chapters = novel_data.get("generated_chapters", {})
        if generated_chapters:
            if current_progress["total_chapters"] == 0:
                current_progress["total_chapters"] = max(generated_chapters.keys())
            if current_progress["completed_chapters"] == 0:
                current_progress["completed_chapters"] = len(generated_chapters)
            if current_progress["stage"] == "未开始" or current_progress["stage"] == "大纲阶段":
                current_progress["stage"] = "写作中"
        
        # 构建完整的项目数据
        data = {
            "novel_info": {
                "title": novel_data["novel_title"],
                "synopsis": novel_data["novel_synopsis"],
                "creative_seed": novel_data["creative_seed"],
                "selected_plan": novel_data["selected_plan"],
                "category": novel_data.get("category", "未分类") 
            },
            
            # 核心数据
            "market_analysis": novel_data.get("market_analysis", {}),
            "global_growth_plan": novel_data.get("global_growth_plan", {}),
            "overall_stage_plans": novel_data.get("overall_stage_plans", {}),
            "stage_writing_plans": novel_data.get("stage_writing_plans", {}),
            "core_worldview": novel_data.get("core_worldview", {}),
            "character_design": novel_data.get("character_design", {}),
            
            # 修复：使用正确的进度信息
            "progress": current_progress,
            
            # 其他数据...
            "chapter_index": [
                {
                    "chapter_number": chapter_num,
                    "chapter_title": chapter_data["chapter_title"],
                    "filename": f"第{chapter_num:03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', chapter_data['chapter_title'])}.txt",
                    "quality_score": chapter_data.get("quality_assessment", {}).get("overall_score", 0),
                    "word_count": chapter_data.get("word_count", 0)
                }
                for chapter_num, chapter_data in sorted(generated_chapters.items())
            ],
            
            "quality_statistics": quality_stats,
            "plot_progression": novel_data.get("plot_progression", []),
            "subplot_settings": {
                "ratio": novel_data.get("subplot_tracking", {}).get("ratio", {"emotional": 0.3, "foreshadowing": 0.3}),
                "subplot_chapters": novel_data.get("subplot_tracking", {}).get("subplot_chapters", {"emotional": [], "foreshadowing": []})
            },
            
            "timestamp": datetime.now().isoformat(),
            "file_structure": {
                "chapters_directory": f"{safe_title}_章节",
                "total_chapters": len(generated_chapters)
            },
            "category_info": {
                "name": novel_data.get("category", "未分类"),
                "subplot_ratio": novel_data.get("subplot_tracking", {}).get("ratio", {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1})
            }
        }
        
        try:
            with open(f"小说项目/{safe_title}_项目信息.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 项目进度已保存: 小说项目/{safe_title}_项目信息.json")
            print(f"  - 进度信息: {current_progress['completed_chapters']}/{current_progress['total_chapters']}章")
            print(f"  - 当前阶段: {current_progress['stage']}")
        except Exception as e:
            print(f"保存项目信息文件失败: {e}")

    def calculate_quality_statistics(self, novel_data: Dict) -> Dict:
        """计算质量统计信息"""
        generated_chapters = novel_data.get("generated_chapters", {})
        if not generated_chapters:
            return {}
        
        scores = []
        optimized_count = 0
        ai_scores = []
        detailed_scores = {
            "plot_coherence": [],
            "character_consistency": [],
            "chapter_connection": [],
            "writing_quality": [],
            "ai_artifacts_detected": [],
            "emotional_impact": []
        }
        
        for chapter_num, chapter_data in generated_chapters.items():
            assessment = chapter_data.get("quality_assessment", {})
            overall_score = assessment.get("overall_score", 0)
            scores.append(overall_score)
            
            # 收集详细分数
            detailed = assessment.get("detailed_scores", {})
            for key in detailed_scores.keys():
                if key in detailed:
                    detailed_scores[key].append(detailed[key])
            
            # 特别收集AI痕迹分数
            ai_score = detailed.get('ai_artifacts_detected', 2)
            ai_scores.append(ai_score)
            
            # 统计优化章节
            if chapter_data.get("optimization_info", {}).get("optimized", False):
                optimized_count += 1
        
        if not scores:
            return {}
        
        # 计算统计信息
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 2
        
        # 使用内化的质量阈值
        quality_thresholds = self.quality_thresholds
        
        # 计算质量分布
        quality_distribution = {
            "优秀": len([s for s in scores if s >= quality_thresholds["excellent"]]),
            "良好": len([s for s in scores if quality_thresholds["good"] <= s < quality_thresholds["excellent"]]),
            "合格": len([s for s in scores if quality_thresholds["acceptable"] <= s < quality_thresholds["good"]]),
            "需要优化": len([s for s in scores if s < quality_thresholds["acceptable"]])
        }
        
        # 计算AI痕迹分布
        ai_distribution = {
            "优秀(2分)": len([s for s in ai_scores if s == 2]),
            "良好(1.5-2分)": len([s for s in ai_scores if 1.5 <= s < 2]),
            "需改进(1-1.5分)": len([s for s in ai_scores if 1 <= s < 1.5]),
            "较差(<1分)": len([s for s in ai_scores if s < 1])
        }
        
        # 计算详细分数平均值
        avg_detailed_scores = {}
        for key, values in detailed_scores.items():
            if values:
                avg_detailed_scores[key] = round(sum(values) / len(values), 2)
        
        return {
            "total_chapters_assessed": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score,
            "optimized_chapters": optimized_count,
            "optimization_rate": round(optimized_count / len(scores) * 100, 1) if scores else 0,
            "quality_distribution": quality_distribution,
            "average_detailed_scores": avg_detailed_scores,
            "ai_quality": {
                "average_ai_score": round(avg_ai_score, 2),
                "ai_distribution": ai_distribution,
                "chapters_with_ai_artifacts": len([s for s in ai_scores if s < 2])
            },
            "last_assessment_time": datetime.now().isoformat()
        }
        
    def export_novel_overview(self, novel_data: Dict):
        """导出小说总览文件"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
        
        overview_data = {
            "novel_overview": {
                "title": novel_data["novel_title"],
                "synopsis": novel_data["novel_synopsis"],
                "total_chapters": novel_data["current_progress"]["total_chapters"],
                "completed_chapters": novel_data["current_progress"]["completed_chapters"],
                "total_word_count": sum(
                    chapter.get('word_count', 0) 
                    for chapter in novel_data["generated_chapters"].values()
                ),
                "selected_plan": novel_data["selected_plan"],
                "creative_seed": novel_data["creative_seed"]
            },
            "worldview_summary": novel_data.get("core_worldview", {}),
            "character_summary": novel_data.get("character_design", {}),
            "writing_plan_summary": {
                "total_stages": len(novel_data.get("stage_writing_plans", {})),
                "current_stage": novel_data["current_progress"].get("current_stage", "第一阶段")
            },
            "chapters_index": [
                {
                    "chapter_number": num,
                    "chapter_title": data["chapter_title"],
                    "word_count": data.get("word_count", 0),
                    "plot_advancement": data["plot_advancement"],
                    "next_chapter_hook": data.get("next_chapter_hook", ""),
                    "quality_score": data.get("quality_assessment", {}).get("overall_score", 0),
                    "ai_score": data.get("quality_assessment", {}).get("detailed_scores", {}).get("ai_artifacts_detected", 2),
                    "was_optimized": data.get("optimization_info", {}).get("optimized", False),
                    "filename": f"第{num:03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', data['chapter_title'])}.txt"
                }
                for num, data in sorted(novel_data["generated_chapters"].items())
            ],
            "generation_info": {
                "start_time": novel_data["current_progress"].get("start_time"),
                "completion_time": datetime.now().isoformat(),
                "creative_seed": novel_data["creative_seed"]
            }
        }
        
        try:
            with open(f"小说项目/{safe_title}_章节总览.json", 'w', encoding='utf-8') as f:
                json.dump(overview_data, f, ensure_ascii=False, indent=2)
            print(f"章节总览已导出到: 小说项目/{safe_title}_章节总览.json")
        except Exception as e:
            print(f"导出章节总览失败: {e}")

    def backup_project(self, novel_data: Dict, backup_type: str = "auto") -> bool:
        """备份项目"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_dir = f"小说项目/备份/{safe_title}"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # 备份项目信息
            backup_filename = f"{backup_dir}/{safe_title}_{backup_type}_备份_{timestamp}.json"
            
            # 创建备份数据
            backup_data = {
                "backup_info": {
                    "type": backup_type,
                    "timestamp": datetime.now().isoformat(),
                    "original_title": novel_data["novel_title"],
                    "completed_chapters": novel_data["current_progress"]["completed_chapters"],
                    "total_chapters": novel_data["current_progress"]["total_chapters"]
                },
                "novel_data": novel_data
            }
            
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 项目备份已创建: {backup_filename}")
            return True
            
        except Exception as e:
            print(f"❌ 项目备份失败: {e}")
            return False

    def cleanup_old_backups(self, novel_title: str, keep_count: int = 5) -> bool:
        """清理旧备份文件"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        backup_dir = f"小说项目/备份/{safe_title}"
        
        if not os.path.exists(backup_dir):
            return True
        
        try:
            # 获取所有备份文件
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith('.json') and safe_title in filename:
                    file_path = os.path.join(backup_dir, filename)
                    backup_files.append((file_path, os.path.getmtime(file_path)))
            
            # 按修改时间排序
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 删除多余的备份文件
            if len(backup_files) > keep_count:
                for file_path, _ in backup_files[keep_count:]:
                    os.remove(file_path)
                    print(f"🗑️  删除旧备份: {os.path.basename(file_path)}")
                
                print(f"✓ 备份清理完成，保留最新的 {keep_count} 个备份")
            
            return True
            
        except Exception as e:
            print(f"❌ 备份清理失败: {e}")
            return False

    def get_project_summary(self, novel_data: Dict) -> Dict:
        """获取项目摘要"""
        generated_chapters = novel_data.get("generated_chapters", {})
        quality_stats = self.calculate_quality_statistics(novel_data)
        
        # 计算总字数
        total_words = sum(
            chapter.get('word_count', 0) 
            for chapter in generated_chapters.values()
        )
        
        # 计算生成时间
        generation_time = None
        if novel_data["current_progress"].get("start_time"):
            try:
                start_time = datetime.fromisoformat(novel_data["current_progress"]["start_time"])
                end_time = datetime.now()
                generation_time = (end_time - start_time).total_seconds() / 60  # 分钟
            except:
                pass
        
        return {
            "project_info": {
                "title": novel_data["novel_title"],
                "category": novel_data.get("category", "未分类"),
                "total_chapters": novel_data["current_progress"]["total_chapters"],
                "completed_chapters": novel_data["current_progress"]["completed_chapters"],
                "completion_rate": round(
                    novel_data["current_progress"]["completed_chapters"] / 
                    novel_data["current_progress"]["total_chapters"] * 100, 1
                ) if novel_data["current_progress"]["total_chapters"] > 0 else 0,
                "current_stage": novel_data["current_progress"].get("stage", "未知"),
                "total_words": total_words
            },
            "quality_info": quality_stats,
            "generation_info": {
                "start_time": novel_data["current_progress"].get("start_time"),
                "generation_time_minutes": round(generation_time, 1) if generation_time else None,
                "average_words_per_chapter": round(
                    total_words / len(generated_chapters), 1
                ) if generated_chapters else 0
            },
            "content_info": {
                "worldview_elements": len(novel_data.get("core_worldview", {})),
                "character_count": len(novel_data.get("character_design", {})),
                "stage_plans": len(novel_data.get("stage_writing_plans", {})),
                "plot_points": len(novel_data.get("plot_progression", []))
            }
        }

    def validate_project_structure(self, novel_data: Dict) -> Dict:
        """验证项目结构完整性"""
        issues = []
        warnings = []
        
        # 检查必要字段
        required_fields = [
            "novel_title", "novel_synopsis", "creative_seed", "selected_plan",
            "core_worldview", "character_design", "current_progress"
        ]
        
        for field in required_fields:
            if field not in novel_data or not novel_data[field]:
                issues.append(f"缺少必要字段: {field}")
        
        # 检查进度信息
        progress = novel_data.get("current_progress", {})
        if not progress.get("total_chapters"):
            warnings.append("总章节数未设置")
        
        # 检查章节文件
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
        chapters_dir = f"小说项目/{safe_title}_章节"
        
        if os.path.exists(chapters_dir):
            chapter_files = [f for f in os.listdir(chapters_dir) if f.endswith('.txt')]
            memory_chapters = len(novel_data.get("generated_chapters", {}))
            
            if len(chapter_files) != memory_chapters:
                warnings.append(f"章节文件数量不一致: 内存中{memory_chapters}章，文件中{len(chapter_files)}章")
        else:
            if novel_data.get("generated_chapters"):
                issues.append("章节目录不存在，但内存中有章节数据")
        
        # 检查质量数据
        if not novel_data.get("chapter_quality_records"):
            warnings.append("缺少章节质量记录")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "summary": {
                "total_issues": len(issues),
                "total_warnings": len(warnings),
                "chapter_count": len(novel_data.get("generated_chapters", {})),
                "quality_records": len(novel_data.get("chapter_quality_records", {}))
            }
        }

    def repair_project_structure(self, novel_data: Dict) -> Dict:
        """修复项目结构问题"""
        print("🛠️ 开始修复项目结构...")
        
        repairs_made = []
        
        # 修复进度信息
        generated_chapters = novel_data.get("generated_chapters", {})
        if generated_chapters:
            if novel_data["current_progress"]["total_chapters"] == 0:
                novel_data["current_progress"]["total_chapters"] = max(generated_chapters.keys())
                repairs_made.append("修复总章节数")
            
            if novel_data["current_progress"]["completed_chapters"] == 0:
                novel_data["current_progress"]["completed_chapters"] = len(generated_chapters)
                repairs_made.append("修复完成章节数")
            
            if novel_data["current_progress"]["stage"] in ["未开始", "大纲阶段"]:
                novel_data["current_progress"]["stage"] = "写作中"
                repairs_made.append("修复进度阶段")
        
        # 修复缺失字段
        if "used_chapter_titles" not in novel_data:
            novel_data["used_chapter_titles"] = set()
            repairs_made.append("添加已使用标题集合")
        
        if "previous_chapter_endings" not in novel_data:
            novel_data["previous_chapter_endings"] = {}
            repairs_made.append("添加上一章结尾信息")
        
        if "plot_progression" not in novel_data:
            novel_data["plot_progression"] = []
            repairs_made.append("添加情节进展记录")
        
        # 重新计算质量统计
        if novel_data.get("generated_chapters"):
            novel_data["quality_statistics"] = self.calculate_quality_statistics(novel_data)
            repairs_made.append("重新计算质量统计")
        
        print(f"✓ 项目修复完成，共进行 {len(repairs_made)} 项修复")
        return {
            "repaired": True,
            "repairs_made": repairs_made,
            "novel_data": novel_data
        }