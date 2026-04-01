# -*- coding: utf-8 -*-
"""
报告生成器 - 生成批次质量分析报告和可视化图表
"""
import json
import os
import matplotlib
matplotlib.use('Agg')  # 无GUI环境
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .chapter_analytics_service import ChapterMetrics, ChapterAnalyticsService


class BatchReportGenerator:
    """批次报告生成器"""
    
    # 专业配色方案
    COLORS = {
        'primary': '#2563EB',      # 主蓝
        'secondary': '#7C3AED',    # 紫
        'success': '#059669',      # 绿
        'warning': '#D97706',      # 橙
        'danger': '#DC2626',       # 红
        'neutral': '#6B7280',      # 灰
        'bg_light': '#F3F4F6',     # 浅灰背景
        'text': '#1F2937',         # 深灰文字
    }
    
    def __init__(self, novel_path: str, novel_title: str):
        self.novel_path = Path(novel_path)
        self.novel_title = novel_title
        self.analytics = ChapterAnalyticsService(novel_path)
        
        # 创建报告目录
        self.report_dir = self.novel_path / '分析报告'
        self.report_dir.mkdir(exist_ok=True)
    
    def generate_batch_report(self, start_chapter: int, end_chapter: int, 
                               window_num: int = 1, total_windows: int = 25) -> Optional[Dict]:
        """生成批次质量报告
        
        Args:
            start_chapter: 窗口起始章节
            end_chapter: 窗口结束章节
            window_num: 窗口序号（第几个窗口）
            total_windows: 总窗口数（200章共25个窗口）
        """
        print(f"[Report] 生成窗口{window_num}/{total_windows} (第{start_chapter}-{end_chapter}章)分析报告...")
        
        # 1. 分析批次数据
        metrics_list = self.analytics.analyze_batch(start_chapter, end_chapter)
        if not metrics_list:
            print(f"[Report] 未找到第{start_chapter}-{end_chapter}章数据")
            return None
        
        # 2. 生成汇总数据
        summary = self.analytics.get_batch_summary(metrics_list)
        summary['window_num'] = window_num
        summary['total_windows'] = total_windows
        summary['overlap_info'] = self._get_overlap_info(window_num, start_chapter)
        
        # 3. 生成图表
        chart_paths = self._generate_charts(metrics_list, summary, start_chapter, end_chapter, window_num)
        
        # 4. 生成Markdown报告
        report_path = self._generate_markdown_report(
            metrics_list, summary, chart_paths, start_chapter, end_chapter, window_num, total_windows
        )
        
        # 5. 保存JSON数据（供后续全书报告使用）
        json_path = self._save_json_data(summary, metrics_list, start_chapter, end_chapter, window_num)
        
        return {
            'window_num': window_num,
            'batch_range': f"{start_chapter}-{end_chapter}",
            'summary': summary,
            'chart_paths': chart_paths,
            'report_path': str(report_path),
            'json_path': str(json_path)
        }
    
    def _get_overlap_info(self, window_num: int, start_chapter: int) -> str:
        """获取与前一个窗口的重叠信息"""
        if window_num == 1:
            return "首个窗口，无重叠"
        # 窗口步长为8，所以重叠的2章是 start_chapter 和 start_chapter+1
        return f"与窗口{window_num-1}重叠: 第{start_chapter}-{start_chapter+1}章"
    
    def _generate_charts(self, metrics_list: List[ChapterMetrics], 
                        summary: Dict, start_ch: int, end_ch: int, 
                        window_num: int = 1) -> Dict:
        """生成分析图表"""
        charts = {}
        # 使用窗口编号命名，例如: batch_w01_001_010
        batch_name = f"batch_w{window_num:02d}_{start_ch:03d}_{end_ch:03d}"
        
        # 图1: 番茄算法合规性对比
        charts['compliance'] = self._gen_compliance_chart(summary, batch_name)
        
        # 图2: 各章番茄得分趋势
        charts['score_trend'] = self._gen_score_trend_chart(metrics_list, batch_name)
        
        # 图3: 情绪分布堆叠图
        charts['emotion'] = self._gen_emotion_chart(metrics_list, batch_name)
        
        # 图4: 综合雷达图
        charts['radar'] = self._gen_radar_chart(summary, batch_name)
        
        return charts
    
    def _gen_compliance_chart(self, summary: Dict, batch_name: str) -> str:
        """生成合规性对比图"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        comparison = summary['benchmark_comparison']
        metrics = ['对话比例', '爽点密度', '情绪密度', '钩子率']
        current = [
            comparison['dialogue']['current'],
            comparison['shuang_density']['current'] * 20,  # 缩放便于展示
            comparison['emotion_density']['current'] * 20,
            comparison['cliffhanger_rate']['current']
        ]
        benchmark = [
            comparison['dialogue']['benchmark'],
            comparison['shuang_density']['benchmark'] * 20,
            comparison['emotion_density']['benchmark'] * 20,
            comparison['cliffhanger_rate']['benchmark']
        ]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, current, width, label='本批次', 
                       color=self.COLORS['primary'], alpha=0.8)
        bars2 = ax.bar(x + width/2, benchmark, width, label='番茄标准',
                       color=self.COLORS['warning'], alpha=0.6)
        
        ax.set_ylabel('百分比 / 缩放值')
        ax.set_title(f'番茄算法合规性对比 (批次: {summary["chapter_range"]})', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(metrics)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        path = self.report_dir / f'{batch_name}_compliance.png'
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(path)
    
    def _gen_score_trend_chart(self, metrics_list: List[ChapterMetrics], 
                               batch_name: str) -> str:
        """生成番茄得分趋势图"""
        fig, ax = plt.subplots(figsize=(12, 5))
        
        chapters = [m.chapter_num for m in metrics_list]
        scores = [m.tomato_score for m in metrics_list]
        
        # 绘制趋势线
        ax.plot(chapters, scores, 'o-', linewidth=2.5, markersize=8,
               color=self.COLORS['primary'])
        ax.fill_between(chapters, scores, alpha=0.2, color=self.COLORS['primary'])
        
        # 阈值线
        ax.axhline(y=80, color=self.COLORS['success'], linestyle='--', 
                  alpha=0.7, label='优秀线(80)')
        ax.axhline(y=60, color=self.COLORS['warning'], linestyle='--',
                  alpha=0.7, label='及格线(60)')
        
        ax.set_xlabel('章节')
        ax.set_ylabel('番茄得分')
        ax.set_title('各章番茄算法得分趋势', fontsize=14, fontweight='bold', pad=20)
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        path = self.report_dir / f'{batch_name}_score_trend.png'
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(path)
    
    def _gen_emotion_chart(self, metrics_list: List[ChapterMetrics], 
                          batch_name: str) -> str:
        """生成情绪分布图"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        chapters = [f"C{m.chapter_num}" for m in metrics_list]
        emotion_types = ['震惊', '恐惧', '兴奋', '压抑', '爽感', '愤怒']
        colors = ['#EF4444', '#8B5CF6', '#F59E0B', '#6B7280', '#10B981', '#DC2626']
        
        # 准备数据
        data = {et: [] for et in emotion_types}
        for m in metrics_list:
            for et in emotion_types:
                data[et].append(m.emotion_breakdown.get(et, 0))
        
        # 堆叠柱状图
        bottom = np.zeros(len(metrics_list))
        for et, color in zip(emotion_types, colors):
            ax.bar(chapters, data[et], bottom=bottom, label=et, 
                  color=color, alpha=0.8)
            bottom += np.array(data[et])
        
        ax.set_ylabel('情绪词出现次数')
        ax.set_title('各章情绪词分布', fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', ncol=3)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        path = self.report_dir / f'{batch_name}_emotion.png'
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(path)
    
    def _gen_radar_chart(self, summary: Dict, batch_name: str) -> str:
        """生成雷达图"""
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        
        categories = ['核心设定', '对话互动', '情绪调动', '节奏把控', '爽点密度', '钩子设计']
        
        # 计算各维度得分（简化版）
        comp = summary['benchmark_comparison']
        values = [
            90,  # 核心设定（假设固定高分）
            min(100, comp['dialogue']['current'] * 1.5),  # 对话
            min(100, comp['emotion_density']['current'] * 30),  # 情绪
            summary['avg_tomato_score'],  # 节奏（用平均分代表）
            min(100, comp['shuang_density']['current'] * 50),  # 爽点
            comp['cliffhanger_rate']['current'],  # 钩子
        ]
        values += values[:1]  # 闭合
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        ax.plot(angles, values, 'o-', linewidth=2.5, color=self.COLORS['secondary'])
        ax.fill(angles, values, alpha=0.25, color=self.COLORS['secondary'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11)
        ax.set_ylim(0, 100)
        ax.set_title(f'综合质量雷达图 (均分: {summary["avg_tomato_score"]})',
                    fontsize=14, fontweight='bold', pad=30)
        
        plt.tight_layout()
        path = self.report_dir / f'{batch_name}_radar.png'
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(path)
    
    def _generate_markdown_report(self, metrics_list: List[ChapterMetrics],
                                  summary: Dict, charts: Dict,
                                  start_ch: int, end_ch: int,
                                  window_num: int = 1, total_windows: int = 25) -> Path:
        """生成Markdown报告"""
        batch_name = f"batch_w{window_num:02d}_{start_ch:03d}_{end_ch:03d}"
        report_path = self.report_dir / f'{batch_name}_report.md'
        
        comp = summary['benchmark_comparison']
        overlap_info = summary.get('overlap_info', '')
        
        # 计算与前一个窗口的重叠章节数
        overlap_chapters = ""
        if window_num > 1:
            overlap_chapters = f" (含{start_ch}-{start_ch+1}章重叠)"
        
        # 生成问题章节表格
        problem_table = "| 章节 | 问题 | 状态 |\n|------|------|------|\n"
        if summary['problem_chapters']:
            for pc in summary['problem_chapters']:
                issues = "; ".join(pc['issues'])
                status = "🔴 需修复" if pc['score'] < 60 else "🟡 待优化"
                problem_table += f"| 第{pc['num']}章 | {issues[:50]}... | {status} |\n"
        else:
            problem_table += "| - | 无重大问题 | ✅ 通过 |\n"
        
        content = f"""# 《{self.novel_title}》质量诊断报告

## 批次信息
- **窗口编号**: 第{window_num}/{total_windows}个窗口
- **章节范围**: 第{start_ch}-{end_ch}章{overlap_chapters}
- **滑动窗口步长**: 8章 (重叠2章)
- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总字数**: {summary['total_words']:,} 字
- **平均章字数**: {summary['avg_word_count']} 字
- **重叠信息**: {overlap_info}

---

## 一、番茄算法合规性

| 指标 | 本批次均值 | 番茄标准 | 差距 | 状态 |
|------|-----------|----------|------|------|
| 对话比例 | {comp['dialogue']['current']}% | {comp['dialogue']['benchmark']}% | {comp['dialogue']['gap']:+.1f}% | {'✅' if comp['dialogue']['status']=='ok' else '🔴'} |
| 爽点密度 | {comp['shuang_density']['current']}/千字 | {comp['shuang_density']['benchmark']}/千字 | {comp['shuang_density']['gap']:+.2f} | {'✅' if comp['shuang_density']['status']=='ok' else '🔴'} |
| 情绪密度 | {comp['emotion_density']['current']}/千字 | {comp['emotion_density']['benchmark']}/千字 | {comp['emotion_density']['gap']:+.2f} | {'✅' if comp['emotion_density']['status']=='ok' else '🔴'} |
| 章末钩子率 | {comp['cliffhanger_rate']['current']}% | {comp['cliffhanger_rate']['benchmark']}% | {comp['cliffhanger_rate']['gap']:+.1f}% | {'✅' if comp['cliffhanger_rate']['status']=='ok' else '🔴'} |

### 合规性可视化
![合规性对比]({Path(charts['compliance']).name})

---

## 二、各章质量得分

**平均番茄得分**: {summary['avg_tomato_score']}/100

![得分趋势]({Path(charts['score_trend']).name})

### 问题章节明细
{problem_table}

---

## 三、情绪曲线分析

**情绪词总计**: {sum(summary['emotion_breakdown'].values())} 次

![情绪分布]({Path(charts['emotion']).name})

---

## 四、综合质量评估

![雷达图]({Path(charts['radar']).name})

### 维度评分
- **核心设定**: ★★★★★ (假设固定)
- **对话互动**: {'★' * int(comp['dialogue']['current']/20) + '☆' * (5-int(comp['dialogue']['current']/20))} ({comp['dialogue']['current']}%)
- **情绪调动**: {'★' * int(comp['emotion_density']['current']/0.6) + '☆' * (5-int(comp['emotion_density']['current']/0.6))} ({comp['emotion_density']['current']}/千字)
- **节奏把控**: {'★' * int(summary['avg_tomato_score']/20) + '☆' * (5-int(summary['avg_tomato_score']/20))} ({summary['avg_tomato_score']}/100)
- **爽点密度**: {'★' * int(comp['shuang_density']['current']/0.3) + '☆' * (5-int(comp['shuang_density']['current']/0.3))} ({comp['shuang_density']['current']}/千字)
- **钩子设计**: {'★' * int(comp['cliffhanger_rate']['current']/20) + '☆' * (5-int(comp['cliffhanger_rate']['current']/20))} ({comp['cliffhanger_rate']['current']}%)

---

## 五、下批次优化建议

"""
        
        # 根据问题生成建议
        suggestions = []
        if comp['dialogue']['status'] != 'ok':
            suggestions.append("1. **提升对话比例**: 当前对话比例偏低，建议增加角色对话和水友弹幕内容")
        if comp['shuang_density']['status'] != 'ok':
            suggestions.append("2. **增加爽点密度**: 每千字至少1.5个爽点，可在战斗/装逼场景增加震惊描写")
        if comp['cliffhanger_rate']['status'] != 'ok':
            suggestions.append("3. **章末钩子**: 每章结尾必须留悬念，如'系统警告/危机来袭/意外发现'")
        if not suggestions:
            suggestions.append("本批次整体质量良好，继续保持当前水准")
        
        content += '\n'.join(suggestions)
        
        content += f"""

---

*报告由AI小说生成系统自动生成*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return report_path
    
    def _save_json_data(self, summary: Dict, metrics_list: List[ChapterMetrics],
                       start_ch: int, end_ch: int, window_num: int = 1) -> Path:
        """保存JSON数据供后续全书报告使用"""
        batch_name = f"batch_w{window_num:02d}_{start_ch:03d}_{end_ch:03d}"
        json_path = self.report_dir / f'{batch_name}_data.json'
        
        data = {
            'batch_info': {
                'window_num': window_num,
                'range': f'{start_ch}-{end_ch}',
                'generated_at': datetime.now().isoformat(),
            },
            'summary': summary,
            'chapter_details': [m.to_dict() for m in metrics_list]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return json_path


class FinalReportGenerator:
    """全书报告生成器（200章完成后使用）
    
    滑动窗口说明:
    - 窗口大小: 10章
    - 重叠: 2章  
    - 步长: 8章
    - 200章共产生25个窗口
    """
    
    TOTAL_WINDOWS = 25  # 200章 / 8章步长 = 25个窗口
    
    def __init__(self, novel_path: str, novel_title: str):
        self.novel_path = Path(novel_path)
        self.novel_title = novel_title
        self.report_dir = self.novel_path / '分析报告'
    
    def generate_final_report(self) -> Optional[Dict]:
        """生成全书质量白皮书"""
        # 1. 读取所有窗口数据（25个窗口）
        window_data = self._load_all_windows()
        if not window_data:
            print("[FinalReport] 未找到窗口数据")
            return None
        
        print(f"[FinalReport] 已加载 {len(window_data)}/{self.TOTAL_WINDOWS} 个窗口数据")
        
        # 2. 聚合分析
        aggregated = self._aggregate_windows(window_data)
        
        # 3. 生成图表
        charts = self._generate_final_charts(aggregated)
        
        # 4. 生成报告
        report_path = self._generate_final_markdown(aggregated, charts)
        
        return {
            'report_path': str(report_path),
            'charts': charts,
            'aggregated_data': aggregated
        }
    
    def _load_all_windows(self) -> List[Dict]:
        """加载所有窗口数据（batch_w*_data.json）"""
        windows = []
        # 匹配 batch_w01_001_010_data.json 格式
        for json_file in sorted(self.report_dir.glob('batch_w*_data.json')):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    windows.append(data)
            except Exception as e:
                print(f"[FinalReport] 加载 {json_file} 失败: {e}")
        return windows
    
    def _aggregate_windows(self, windows: List[Dict]) -> Dict:
        """聚合所有窗口数据"""
        # 按窗口编号排序
        windows_sorted = sorted(windows, key=lambda x: x.get('batch_info', {}).get('window_num', 0))
        
        # 提取关键指标趋势
        tomato_scores = [w['summary']['avg_tomato_score'] for w in windows_sorted]
        dialogue_ratios = [w['summary']['avg_dialogue_ratio'] for w in windows_sorted]
        shuang_densities = [w['summary']['avg_shuang_density'] for w in windows_sorted]
        
        # 汇总情绪（需要去重，因为窗口有重叠）
        total_emotion = {}
        covered_chapters = set()
        
        for w in windows_sorted:
            # 解析章节范围
            range_str = w['batch_info']['range']  # "1-10" 或 "8-17"
            start, end = map(int, range_str.split('-'))
            
            # 只统计未被覆盖的章节（避免重叠章节重复计数）
            for ch_detail in w['chapter_details']:
                ch_num = ch_detail.get('chapter_num', 0)
                if ch_num not in covered_chapters:
                    covered_chapters.add(ch_num)
                    for emotion, count in ch_detail.get('emotion_breakdown', {}).items():
                        total_emotion[emotion] = total_emotion.get(emotion, 0) + count
        
        # 统计问题章节（也去重）
        all_problems = []
        problem_chapters_seen = set()
        for w in windows_sorted:
            for pc in w['summary'].get('problem_chapters', []):
                ch_num = pc.get('num', 0)
                if ch_num not in problem_chapters_seen:
                    problem_chapters_seen.add(ch_num)
                    all_problems.append(pc)
        
        # 实际总章节数应该是200
        total_chapters = len(covered_chapters)
        
        return {
            'total_windows': len(windows_sorted),
            'expected_windows': self.TOTAL_WINDOWS,
            'total_chapters': total_chapters,
            'total_words': sum(w['summary']['total_words'] for w in windows_sorted) // 10 * 8,  # 减去重叠部分
            'avg_tomato_score': round(sum(tomato_scores) / len(tomato_scores), 1) if tomato_scores else 0,
            'score_trend': tomato_scores,
            'dialogue_trend': dialogue_ratios,
            'shuang_trend': shuang_densities,
            'emotion_summary': total_emotion,
            'problem_chapters': all_problems,
            'problem_rate': len(all_problems) / total_chapters if total_chapters > 0 else 0,
            'final_rating': self._calc_final_rating(tomato_scores),
            'window_details': [
                {
                    'window_num': w['batch_info'].get('window_num', 0),
                    'range': w['batch_info']['range'],
                    'avg_score': w['summary']['avg_tomato_score']
                }
                for w in windows_sorted
            ]
        }
    
    def _calc_final_rating(self, scores: List[float]) -> str:
        """计算最终评级"""
        avg = sum(scores) / len(scores)
        if avg >= 85:
            return 'S'
        elif avg >= 75:
            return 'A'
        elif avg >= 65:
            return 'B'
        elif avg >= 55:
            return 'C'
        else:
            return 'D'
    
    def _generate_final_charts(self, aggregated: Dict) -> Dict:
        """生成全书图表"""
        charts = {}
        
        # 图1: 34个批次得分趋势
        fig, ax = plt.subplots(figsize=(14, 6))
        batches = list(range(1, len(aggregated['score_trend']) + 1))
        ax.plot(batches, aggregated['score_trend'], 'o-', 
               linewidth=2, markersize=6, color='#2563EB')
        ax.fill_between(batches, aggregated['score_trend'], alpha=0.2, color='#2563EB')
        ax.axhline(y=80, color='green', linestyle='--', alpha=0.5, label='优秀线')
        ax.axhline(y=60, color='orange', linestyle='--', alpha=0.5, label='及格线')
        ax.set_xlabel('批次')
        ax.set_ylabel('平均番茄得分')
        ax.set_title('全书34个批次质量得分趋势', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        path = self.report_dir / 'final_score_trend.png'
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        charts['score_trend'] = str(path)
        plt.close()
        
        return charts
    
    def _generate_final_markdown(self, aggregated: Dict, charts: Dict) -> Path:
        """生成全书白皮书"""
        report_path = self.report_dir / 'FINAL_REPORT.md'
        
        content = f"""# 《{self.novel_title}》全本质量白皮书

## 一、核心指标总览

| 指标 | 数值 |
|------|------|
| 总批次 | {aggregated['total_batches']} 个 |
| 总章节 | {aggregated['total_chapters']} 章 |
| 总字数 | {aggregated['total_words']:,} 字 |
| 平均番茄得分 | {aggregated['avg_tomato_score']}/100 |
| 问题章节率 | {aggregated['problem_rate']:.1%} |
| **综合评级** | **{aggregated['final_rating']}级** |

![全书得分趋势](final_score_trend.png)

---

## 二、与番茄Top10对比

（详细对比表格待补充）

---

## 三、优化建议（用于下一本）

（基于数据分析的建议待补充）

---

*全本分析报告 - 生成于 {datetime.now().strftime('%Y-%m-%d')}*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return report_path
