"""
Mock Environment for Fast Testing
快速测试模拟环境 - 无需真实API调用
"""

import os
import json
import time
import random
from typing import Dict, Any

# Mock mode flag
MOCK_MODE = True

class MockAPIClient:
    """Mock API Client - Returns predefined responses"""

    def __init__(self, config=None):
        self.response_delay = 0.1  # Simulate network delay

    def call_api(self, messages: list, role_name: str = None, **kwargs) -> str:
        """Return mock API response"""

        # Simulate delay
        time.sleep(self.response_delay)

        content = messages[-1]["content"] if messages else ""

        # Return different responses based on content
        if "creative" in content.lower() or "refine" in content.lower():
            return self._mock_creative_refinement()
        elif "outline" in content.lower() and "chapter" in content.lower():
            chapter_num = self._extract_chapter_number(content)
            return self._mock_chapter_outline(chapter_num)
        elif "content" in content.lower() and "chapter" in content.lower():
            chapter_num = self._extract_chapter_number(content)
            return self._mock_chapter_content(chapter_num)
        elif "assess" in content.lower() or "evaluate" in content.lower():
            return self._mock_quality_assessment()
        elif "plan" in content.lower():
            return self._mock_novel_plan()
        else:
            return self._mock_default_response()

    def _extract_chapter_number(self, content: str) -> int:
        """Extract chapter number from content"""
        import re
        match = re.search(r'(\d+)', content)
        return int(match.group(1)) if match else 1

    def _mock_creative_refinement(self) -> str:
        """Mock creative refinement response"""
        return json.dumps({
            "type": "creative_refinement",
            "data": {
                "title": "Star River Sword God: From Nobody to Supreme",
                "synopsis": "In the Nine Heavens and Ten Earths, where myriad races coexist, young Li Fan obtains the Hongmeng Sword Canon, rising from a nobody to stand above the heavens.",
                "core_setting": "Multi-universe cultivation system, sword path is supreme, technology and cultivation merge",
                "characters": {
                    "protagonist": "Li Fan (transmigrator with Hongmeng Sword Canon)",
                    "love_interest": "Yaochi Saintess (most beautiful woman in the heavens)",
                    "rival": "Heaven Lord's Son (main antagonist)"
                },
                "selling_points": [
                    "Genius protagonist with hidden identity",
                    "Mysterious inheritance, heaven-defying transformation",
                    "Surrounded by beauties, unlimited possibilities",
                    "Upgrade battles, fast-paced action"
                ]
            }
        }, ensure_ascii=False, indent=2)

    def _mock_chapter_outline(self, chapter_num: int) -> str:
        """Mock chapter outline generation"""
        plot_types = ["Upgrade", "Battle", "Cultivation", "Adventure", "Showdown"]
        plot_type = random.choice(plot_types)

        outlines = {
            "Upgrade": f"Li Fan discovers an ancient ruin in the Star Forest. By breaking through the sword intent inheritance within, his cultivation skyrockets, breaking through to the late Foundation Building stage.",
            "Battle": f"Li Fan encounters provocation from the Heaven Lord's Son in Tianji City. The two engage in a heaven-shaking battle where Li Fan defeats three opponents single-handedly, shocking the entire city.",
            "Cultivation": f"Li Fan enters the Nine Heavens for closed-door cultivation. He comprehends the true meaning of the sword path, his cultivation bottleneck loosening, preparing to break through to the Golden Core stage.",
            "Adventure": f"While exploring the void turbulence, Li Fan accidentally discovers an ancient star with a Sword Immortal's inheritance, gaining supreme sword techniques.",
            "Showdown": f"The Heaven Lord's Son publicly mocks Li Fan as trash at the sect competition. Li Fan defeats the opponent with one strike, shocking everyone who ever looked down on him."
        }

        return json.dumps({
            "type": "chapter_outline",
            "data": {
                "chapter_title": f"Chapter {chapter_num}: Path of {plot_type}",
                "plot_type": plot_type,
                "core_conflict": "Protagonist vs antagonist conflict intensifies",
                "character_development": "Li Fan's cultivation and mental growth",
                "worldbuilding_progress": f"Reveals secrets of universe layer {chapter_num}",
                "foreshadowing": "Sets up important foreshadowing for future plots",
                "emotional_arc": "Relationship progress with Yaochi Saintess",
                "estimated_words": 2000,
                "scene_setting": {
                    "location": self._generate_scene(chapter_num),
                    "time": f"Day {chapter_num*10} of the story",
                    "atmosphere": "Passionate and thrilling"
                },
                "plot_outline": outlines.get(plot_type, "Protagonist continues cultivation adventures"),
                "chapter_goal": f"Advance main plot to stage {chapter_num+1}"
            }
        }, ensure_ascii=False, indent=2)

    def _mock_chapter_content(self, chapter_num: int) -> str:
        """Mock chapter content generation"""
        content_templates = [
            f"Chapter {chapter_num}: Star River Sword Shadows\n\nAbove the Nine Heavens, winds and clouds surge.\n\nLi Fan holds his sword, standing proudly in the Nine Heavens, his gaze like lightning, staring at the distant horizon. Since obtaining the Hongmeng Sword Canon, his cultivation has advanced by leaps and bounds. Now he stands at the peak of Foundation Building stage.\n\n" +
            f"The path of cultivation has always been defying heaven. Li Fan knows this well, so he cultivates even harder. On this day, he finally senses the opportunity to break through.\n\n" +
            f"The Golden Core path is close at hand!\n\nLi Fan takes a deep breath and begins circulating the secret art from the Hongmeng Sword Canon. Instantly, spiritual energy from heaven and earth rushes wildly into his body.",

            f"Chapter {chapter_num}: Sword Pointing to the Heavens\n\nDragons meet, tigers contend.\n\nOn this day, Li Fan arrives at Tianji City. This city is built in the void, the most prosperous cultivation land in the Nine Heavens and Ten Earths. However, what awaits him is an unprecedented challenge.\n\n" +
            f"The Heaven Lord's Son stands high above, coldly looking down at Li Fan: 'A mere Foundation Building cultivator dares to act arrogantly in Tianji City?'\n\n" +
            f"'Xuantian Sword Art First Form!' Li Fan shouts, his sword unsheathing, flashing cold light.",

            f"Chapter {chapter_num}: Heart Moving Nine Heavens\n\nMoonlight like water, star river brilliant.\n\nIn the Yaochi Saintess's chamber, Li Fan receives her guidance. This saintess, known as the most beautiful woman in the heavens, not only has profound cultivation but more importantly, her pure heart.\n\n" +
            f"'Your sword technique is very special,' the Yaochi Saintess says softly, a glint of admiration in her eyes.\n\nLi Fan's heart stirs; he can feel the Yaochi Saintess's goodwill. But he knows his path is long, and now is not the time for romance."
        ]

        return random.choice(content_templates)

    def _mock_quality_assessment(self) -> str:
        """Mock quality assessment"""
        score = random.uniform(8.0, 9.5)

        return json.dumps({
            "type": "quality_assessment",
            "data": {
                "overall_score": round(score, 1),
                "rating": "Excellent" if score >= 9.0 else "Good" if score >= 8.0 else "Pass",
                "strengths": [
                    "Tight plot, fast-paced",
                    "Vivid character creation with life and blood",
                    "Grand and consistent worldbuilding",
                    "Smooth writing, vivid language",
                    "Clever suspense, captivating"
                ],
                "improvement_suggestions": [
                    "Consider adding more detail descriptions",
                    "Character dialogue can be more personalized",
                    "Battle scenes can be more intense and exciting",
                    "Emotional development can be more delicate"
                ],
                "chapter_quality": {
                    "plot_development": round(score, 1),
                    "character_creation": round(score - 0.2, 1),
                    "writing_expression": round(score + 0.1, 1),
                    "worldbuilding": round(score, 1),
                    "emotional_description": round(score - 0.3, 1)
                },
                "overall_evaluation": "This chapter's content quality is excellent, plot development reasonable, character creation vivid, meeting web novel creation standards."
            }
        }, ensure_ascii=False, indent=2)

    def _mock_novel_plan(self) -> str:
        """Mock novel plan generation"""
        return json.dumps({
            "type": "novel_plan",
            "data": {
                "title": "Star River Sword God",
                "genre": "Xuanhuan Cultivation",
                "target_audience": "15-35 year old male readers",
                "word_count": "3 million characters",
                "chapter_count": 100,
                "plot_structure": {
                    "opening": "Protagonist Li Fan transmigrates to another world, obtains mysterious inheritance",
                    "development": "Gradual growth, encounters challenges, makes allies",
                    "climax": "Confront final antagonist, save the universe",
                    "ending": "Becomes universe supreme, opens new era"
                },
                "character_arc": {
                    "start": "Trash student",
                    "growth": "Diligent cultivation, breaks through self",
                    "peak": "Universe Sword God",
                    "transformation": "Transformation from ordinary to great"
                },
                "selling_points": [
                    "Genius protagonist with hidden identity",
                    "Mysterious inheritance, heaven-defying transformation",
                    "Surrounded by beauties, unlimited possibilities",
                    "Upgrade battles, fast-paced action",
                    "Grand world, universe adventure"
                ]
            }
        }, ensure_ascii=False, indent=2)

    def _mock_default_response(self) -> str:
        """Mock default response"""
        return json.dumps({
            "type": "default_response",
            "data": {
                "message": "Mock API response",
                "status": "success",
                "content": "This is a simulated response content"
            }
        }, ensure_ascii=False, indent=2)

    def _generate_scene(self, chapter_num: int) -> str:
        """Generate scene description"""
        scenes = [
            "Sacred cultivation site above the Nine Clouds",
            "Mysterious star in the void turbulence",
            "Ancient ruins deep within",
            "Prosperous cultivation city",
            "Dangerous forbidden zone",
            "Opportunity-filled secret realm",
            "Sect competition venue",
            "Land of heavenly tribulation descent"
        ]
        return scenes[chapter_num % len(scenes)]


# Global mock client instance
mock_api_client = MockAPIClient()

def get_mock_client():
    """Get mock API client instance"""
    return mock_api_client

def is_mock_mode():
    """Check if in mock mode"""
    return MOCK_MODE