"""Deterministic safety rules independent of model output."""
import re

from .schemas import AnalysisResult


EMERGENCY_PATTERNS = (
    r"khó thở|sốc phản vệ|phù mạch|bất tỉnh",
    r"hoại tử|bóng nước lan rộng|trợt loét diện rộng",
    r"stevens.?johnson|sjs|ten",
    r"viêm mô tế bào.*lan nhanh",
)
SOON_PATTERNS = (
    r"zona.*mắt|quanh mắt",
    r"sốt cao.*mủ|mụn mủ.*sốt",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(re.search(pattern, lowered) for pattern in patterns)


def apply_guardrails(result: AnalysisResult, user_text: str) -> AnalysisResult:
    if _matches(user_text, EMERGENCY_PATTERNS):
        result.triage_level = "Cap_cuu"
        result.urgency_label = "Cần đến khoa Cấp cứu hoặc gọi cấp cứu ngay."
        result.recommended_specialty = "Khoa Cấp cứu"
        result.red_flags_check = {
            "has_red_flag": True,
            "warning_notes": "Phát hiện dấu hiệu có thể nguy hiểm trong mô tả; cần đánh giá y tế khẩn cấp.",
        }
    elif not result.red_flags_check.has_red_flag and _matches(user_text, SOON_PATTERNS):
        result.triage_level = "Kham_som"
        result.urgency_label = "Nên được khám trong vòng 24–48 giờ."
        result.red_flags_check = {
            "has_red_flag": True,
            "warning_notes": "Có dấu hiệu cần được đánh giá sớm bởi nhân viên y tế.",
        }
    if result.red_flags_check.has_red_flag and not result.urgency_label:
        result.urgency_label = "Nên liên hệ cơ sở y tế sớm."
    return result
