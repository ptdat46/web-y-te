"""
Ollama provider abstraction with a safe mock fallback.

The chatbot never produces a diagnosis. It helps the user structure
their symptoms and decide which specialist to see. Red-flag symptoms
always return an emergency warning instead of a normal answer.
"""

import json
import logging
import os
import re
import unicodedata
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
REQUEST_TIMEOUT = float(os.getenv('OLLAMA_TIMEOUT', '15'))

SYSTEM_PROMPT = """Bạn là trợ lý định hướng sức khỏe sử dụng tiếng Việt.

QUY TẮC BẮT BUỘC:
1. KHÔNG BAO GIỜ đưa ra chẩn đoán bệnh hoặc kê đơn thuốc.
2. Chỉ giúp người dùng mô tả triệu chứng rõ ràng: vị trí, mức độ, thời gian, yếu tố tăng/giảm.
3. Gợi ý nhóm chuyên khoa phù hợp để đi khám (nội khoa, tim mạch, tiêu hóa...).
4. Đề nghị đi khám ngay nếu triệu chứng kéo dài hoặc nặng thêm.
5. Luôn kết thúc bằng: "Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ."
6. Trả lời ngắn gọn, tối đa 150 từ, bằng tiếng Việt.
"""

RED_FLAG_PATTERNS = [
    r'đau\s+ngực',
    r'khó\s+thở',
    r'không\s+thở\s+được',
    r'yếu\s+(nửa\s+)?người',
    r'liệt',
    r'nói\s+khó',
    r'khó\s+nói',
    r'méo\s+miệng',
    r'ngất',
    r'bất\s+tỉnh',
    r'chảy\s+máu\s+nhiều',
    r'sốc\s+phản\s+vệ',
    r'sưng\s+môi',
    r'co\s+giật',
    r'đau\s+bụng\s+dữ\s+dội',
]

EMERGENCY_RESPONSE = (
    '⚠️ Cảnh báo khẩn cấp: Các triệu chứng bạn mô tả có thể là dấu hiệu cấp cứu '
    '(tim mạch, đột quỵ hoặc phản ứng dị ứng nghiêm trọng). '
    'Hãy gọi 115 hoặc đến cơ sở y tế gần nhất NGAY LẬP TỨC. '
    'Đừng tự lái xe nếu có thể. Đây là thông tin hỗ trợ, không thay thế đánh giá y tế.'
)


def normalize_vi(text: str) -> str:
    """
    Normalize Vietnamese text to lowercase plain ASCII by removing all
    diacritics (standard NFD decomposition). E.g. 'nghẹt thở' -> 'nghet tho'.
    """
    lowered = (text or '').lower()
    decomposed = unicodedata.normalize('NFD', lowered)
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch))


def contains_red_flag(text: str) -> bool:
    """Heuristic red-flag detection for emergency symptoms."""
    normalized = normalize_vi(text)
    for pattern in RED_FLAG_PATTERNS:
        if re.search(normalize_vi(pattern), normalized):
            return True
    return False


class OllamaUnavailable(Exception):
    pass


def call_ollama(messages: list[dict]) -> str:
    """
    Call the Ollama chat API. Returns the assistant text.
    Raises OllamaUnavailable when Ollama cannot be reached.
    """
    payload = json.dumps({
        'model': OLLAMA_MODEL,
        'messages': messages,
        'stream': False,
    }).encode('utf-8')

    url = f'{OLLAMA_BASE_URL.rstrip("/")}/api/chat'
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return str(data.get('message', {}).get('content', '')).strip()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        logger.warning('Ollama call failed: %s', exc)
        raise OllamaUnavailable(str(exc)) from exc


def _mock_reply(user_text: str, history: list[dict]) -> str:
    """Deterministic offline reply when Ollama is unavailable."""
    text = user_text.lower()
    if any(kw in text for kw in ('sốt', 'ho', 'đau họng', 'cảm', 'cúm')):
        reply = (
            'Nghe có vẻ bạn đang gặp các triệu chứng đường hô hấp. '
            'Một vài câu hỏi giúp định hướng: Bạn sốt bao nhiêu độ? '
            'Có ho khan hay ho có đờm không? Triệu chứng bắt đầu từ khi nào và đã kéo dài mấy ngày? '
            'Nếu sốt cao trên 5 ngày hoặc khó thở tăng dần, bạn nên đi khám nội khoa hô hấp sớm. '
            'Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ.'
        )
    elif any(kw in text for kw in ('bụng', 'đau bụng', 'tiêu chảy', 'buồn nôn', 'nôn')):
        reply = (
            'Triệu chứng tiêu hóa cần xác định thêm: Vị trí đau ở vùng nào (thượng vị, hạ sườn, quanh rốn)? '
            'Đau âm ỉ hay dữ dội? Có kèm sốt, tiêu chảy hoặc phân bất thường không? '
            'Đau bụng dữ dội đột ngột, đau lan sau lưng hoặc kèm nôn ra máu cần đi cấp cứu ngay. '
            'Nếu nhẹ, bạn có thể khám chuyên khoa tiêu hóa trong 1-2 ngày tới. '
            'Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ.'
        )
    elif any(kw in text for kw in ('đau đầu', 'chóng mặt', 'hoa mắt', 'mất ngủ', 'ngủ')):
        reply = (
            'Đau đầu và chóng mặt có thể do nhiều nguyên nhân. Để định hướng rõ hơn: '
            'Đau đầu kiểu gì (căng, giật theo nhịp mạch, hai bên hay một bên)? '
            'Có kèm rối loạn thị giác, tê yếu tay chân, hoặc đau tăng khi gắng sức không? '
            'Đau đầu đột ngột dữ dội nhất từ trước đến nay, kèm yếu liệt hoặc nói khó phải đi cấp cứu ngay. '
            'Nếu không có dấu hiệu bất thường, chuyên khoa thần kinh hoặc nội khoa sẽ giúp bạn. '
            'Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ.'
        )
    elif any(kw in text for kw in ('da', 'mẩn', 'ngứa', 'dị ứng', 'phát ban')):
        reply = (
            'Các vấn đề về da cần biết thêm: Mẩn ngứa lan rộng hay khu trú? Xuất hiện sau ăn gì, uống thuốc gì không? '
            'Nếu kèm sưng môi, khó thở, tụt huyết áp thì đây là dấu hiệu dị ứng nặng - phải cấp cứu ngay. '
            'Nếu chỉ ngứa nhẹ, bạn có thể khám chuyên khoa da liễu. '
            'Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ.'
        )
    else:
        reply = (
            'Tôi sẽ cố gắng giúp bạn định hướng vấn đề. Hãy mô tả thêm: triệu chứng chính của bạn là gì, '
            'bắt đầu từ khi nào, mức độ ảnh hưởng tới sinh hoạt ra sao, và có yếu tố nào làm nặng/giảm triệu chứng không? '
            'Dựa trên câu trả lời, tôi có thể gợi ý nhóm chuyên khoa phù hợp. '
            'Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ.'
        )
    return reply


def generate_reply(user_text: str, history: list[dict]) -> tuple[str, bool]:
    """
    Generate a reply for the user's message.

    Returns (reply_text, red_flag_detected).
    """
    flag = contains_red_flag(user_text)
    if flag:
        return EMERGENCY_RESPONSE, True

    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}] + history
    try:
        reply = call_ollama(messages)
        if reply:
            return reply, False
        return _mock_reply(user_text, history), False
    except OllamaUnavailable:
        return _mock_reply(user_text, history), False
    except Exception as exc:  # Safety net: never fail the chatbot on provider errors
        logger.warning('Unexpected chatbot provider error: %s', exc)
        return _mock_reply(user_text, history), False