"""写作计划质量评估工具

用法：
    # 基础评估（规则式，不需要API）
    python tools/assess_writing_plan.py 小说项目/xxx/plans/xxx_opening_stage_writing_plan.json

    # AI深度评估（需要Anthropic API）
    python tools/assess_writing_plan.py xxx.json --deep --api-key YOUR_API_KEY

输出：
    - xxx_opening_stage_writing_plan_quality_report.json  # 详细报告
    - xxx_opening_stage_writing_plan_quality_report.txt   # 可读报告
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.core.PlanQualityAssessor import PlanQualityAssessor


def main():
    parser = argparse.ArgumentParser(
        description="评估写作计划质量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s plan.json                           # 规则式评估
  %(prog)s plan.json --deep                    # 深度分析
  %(prog)s plan.json --deep --api-key KEY      # 使用AI评估
        """
    )

    parser.add_argument(
        "plan",
        type=str,
        help="写作计划JSON文件路径"
    )

    parser.add_argument(
        "--deep",
        action="store_true",
        help="启用深度分析（仅AI模式有效）"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API密钥（也可通过ANTHROPIC_API_KEY环境变量设置）"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细输出"
    )

    args = parser.parse_args()

    # 解析API密钥
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"[ERROR] File not found: {plan_path}")
        return 1

    print(f"[START] Assessing writing plan...")
    print(f"   File: {plan_path}")
    print(f"   Mode: {'AI Assessment' if api_key else 'Rule-based Assessment'}")
    if args.deep:
        print(f"   Deep Analysis: Enabled")
    print()

    try:
        assessor = PlanQualityAssessor(api_key=api_key)
        result = assessor.assess(plan_path, use_deep_analysis=args.deep)

        # 打印摘要
        print("=" * 50)
        print("Assessment Result Summary")
        print("=" * 50)
        print(f"  Score: {result.overall_score}/100")
        print(f"  Status: {_get_status_symbol(result.readiness)} {result.readiness}")
        if result.token_saved > 0:
            print(f"  Tokens Saved: ~{result.token_saved:,}")
        print()

        # 优点
        if result.strengths:
            print("[+] Strengths:")
            for strength in result.strengths:
                print(f"     * {strength}")
            print()

        # 问题
        if result.issues:
            # 按严重程度统计
            severity_count = {}
            for issue in result.issues:
                sev = issue.severity.value
                severity_count[sev] = severity_count.get(sev, 0) + 1

            print("[!] Issues Distribution:")
            for sev, count in severity_count.items():
                print(f"     {sev.upper()}: {count}")
            print()

            # 显示关键问题
            critical_issues = [i for i in result.issues if i.severity.value in ["critical", "high"]]
            if critical_issues:
                print("[!] Critical Issues:")
                for issue in critical_issues[:5]:  # 最多显示5个
                    print(f"     [{issue.category}] {issue.location}")
                    print(f"       {issue.description}")
                if len(critical_issues) > 5:
                    print(f"     ... and {len(critical_issues) - 5} more, see report file")
                print()

        # 准备度建议
        print("=" * 50)
        if result.readiness == "ready":
            print("[PASS] Ready for next stage generation")
        elif result.readiness == "needs_review":
            print("[WARNING] Some issues need attention")
            print("        Please check detailed report and decide")
        else:
            print("[FAIL] Critical issues found")
            print("        Strongly recommend fixing before next stage")
        print("=" * 50)

        # 报告文件位置
        report_json = plan_path.parent / f"{plan_path.stem}_quality_report.json"
        report_txt = plan_path.parent / f"{plan_path.stem}_quality_report.txt"
        print(f"\n[REPORT] Detailed report saved:")
        print(f"   JSON: {report_json}")
        print(f"   TXT:  {report_txt}")

        return 0

    except Exception as e:
        print(f"[ERROR] Assessment failed: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        return 1


def _get_status_symbol(status: str) -> str:
    return {
        "ready": "[OK]",
        "needs_review": "[WARN]",
        "needs_revision": "[FAIL]"
    }.get(status, "[?]")


if __name__ == "__main__":
    sys.exit(main() or 0)
