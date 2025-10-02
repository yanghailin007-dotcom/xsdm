"""项目管理器类"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

class ProjectManager:
    def __init__(self, config):
        self.config = config
    
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
        """加载项目数据 - 修复版本：从章节文件加载所有具体内容"""
        try:
            with open(f"小说项目/{filename}", 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 加载章节具体内容
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", project_data["novel_info"]["title"])
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
                                    # 确保加载所有章节特定的信息
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
                
                project_data["generated_chapters"] = generated_chapters
            
            return project_data
        except Exception as e:
            print(f"❌❌ 加载项目失败: {e}")
            return None
    
    def save_single_chapter(self, novel_title: str, chapter_number: int, chapter_data: Dict):
        """保存单章内容 - 包含完整的设计方案和内容"""
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
        """保存项目整体进度 - 修复版本：不保存具体章节内容"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
        os.makedirs("小说项目", exist_ok=True)
        
        # 计算质量统计 - 只使用基本统计信息
        quality_stats = self.calculate_basic_quality_statistics(novel_data)
        
        data = {
            "novel_info": {
                "title": novel_data["novel_title"],
                "synopsis": novel_data["novel_synopsis"],
                "creative_seed": novel_data["creative_seed"],
                "selected_plan": novel_data["selected_plan"],
                "category": novel_data.get("category", "未分类") 
            },
            "market_analysis": novel_data["market_analysis"],
            "overall_stage_plan": novel_data["overall_stage_plan"],
            "core_worldview": novel_data["core_worldview"],
            "character_design": novel_data["character_design"],
            
            # 只保存章节的基本索引信息，不保存具体内容
            "chapter_index": [
                {
                    "chapter_number": chapter_num,
                    "chapter_title": chapter_data["chapter_title"],
                    "filename": f"第{chapter_num:03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', chapter_data['chapter_title'])}.txt",
                    "quality_score": chapter_data.get("quality_assessment", {}).get("overall_score", 0),
                    "word_count": chapter_data.get("word_count", 0)
                }
                for chapter_num, chapter_data in sorted(novel_data["generated_chapters"].items())
            ],
            
            # 只保存基本的质量记录
            "quality_statistics": quality_stats,
            "progress": novel_data["current_progress"],
            "plot_progression": [
                {
                    "chapter": item["chapter"],
                    "title": item["title"],
                    "key_events_count": len(item.get("key_events", []))
                }
                for item in novel_data.get("plot_progression", [])
            ],
            "subplot_settings": {
                "ratio": novel_data.get("subplot_tracking", {}).get("ratio", {"emotional": 0.3, "foreshadowing": 0.3}),
                "emotional_chapters_count": len(novel_data.get("subplot_tracking", {}).get("subplot_chapters", {}).get("emotional", [])),
                "foreshadowing_chapters_count": len(novel_data.get("subplot_tracking", {}).get("subplot_chapters", {}).get("foreshadowing", []))
            },
            "timestamp": datetime.now().isoformat(),
            "file_structure": {
                "chapters_directory": f"{safe_title}_章节",
                "total_chapters": len(novel_data["generated_chapters"])
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
        except Exception as e:
            print(f"保存项目信息文件失败: {e}")
            
    def calculate_basic_quality_statistics(self, novel_data: Dict) -> Dict:
        """计算基本质量统计信息 - 不包含详细内容"""
        if not novel_data["generated_chapters"]:
            return {}
        
        scores = []
        optimized_count = 0
        
        for chapter_num, chapter_data in novel_data["generated_chapters"].items():
            assessment = chapter_data.get("quality_assessment", {})
            overall_score = assessment.get("overall_score", 0)
            scores.append(overall_score)
            
            if chapter_data.get("optimization_info", {}).get("optimized", False):
                optimized_count += 1
        
        if not scores:
            return {}
        
        avg_score = sum(scores) / len(scores)
        
        return {
            "total_chapters": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "optimized_chapters": optimized_count,
            "optimization_rate": round(optimized_count / len(scores) * 100, 1) if scores else 0,
            "last_assessment_time": datetime.now().isoformat()
        }    
    # 在 project_manager.py 中修复 calculate_quality_statistics 方法
    def calculate_quality_statistics(self, novel_data: Dict) -> Dict:
        """计算质量统计信息 - 修复版本"""
        if not novel_data["generated_chapters"]:
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
        
        for chapter_num, chapter_data in novel_data["generated_chapters"].items():
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
        
        # 修复：使用正确的配置路径
        quality_thresholds  = self.config.get("optimization_settings", {}).get("quality_thresholds", {
            "excellent": 9.0,
            "good": 8.5,
            "acceptable": 8.0,
            "needs_optimization": 7.5,
            "needs_rewrite": 6.0
        })
        
        # 计算质量分布
        quality_distribution = {
            "优秀": len([s for s in scores if s >= quality_thresholds.get("excellent", 9.0)]),
            "良好": len([s for s in scores if quality_thresholds.get("good", 8.5) <= s < quality_thresholds.get("excellent", 9.0)]),
            "合格": len([s for s in scores if quality_thresholds.get("acceptable", 8.0) <= s < quality_thresholds.get("good", 8.5)]),
            "需要优化": len([s for s in scores if s < quality_thresholds.get("acceptable", 8.0)])
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
                avg_detailed_scores[key] = sum(values) / len(values)
        
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
                "selected_plan": novel_data["selected_plan"]
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