content_type = "stage_major_event_skeleton"
content_type_lower = content_type.lower()

# Check the "plan" condition
plan_condition = ("plan" in content_type_lower and "quality" not in content_type_lower and "stage" not in content_type_lower)
print(f"'plan' in '{content_type}': {'plan' in content_type_lower}")
print(f"'quality' not in '{content_type}': {'quality' not in content_type_lower}")
print(f"'stage' not in '{content_type}': {'stage' not in content_type_lower}")
print(f"plan_condition result: {plan_condition}")

# Check the major_event_skeleton condition
skeleton_condition = ("主龙骨" in content_type_lower or "stage_major_event_skeleton" in content_type_lower)
print(f"\n'stage_major_event_skeleton' in '{content_type}': {'stage_major_event_skeleton' in content_type_lower}")
print(f"skeleton_condition result: {skeleton_condition}")
