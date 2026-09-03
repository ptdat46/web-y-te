"""LLM provider used by the health assistant."""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
REQUEST_TIMEOUT = float(os.getenv('OLLAMA_TIMEOUT', '15'))

SYSTEM_PROMPT = """Bạn là trợ lý sức khỏe sử dụng tiếng Việt.
Hãy sử dụng dữ liệu bệnh nhân được cung cấp cùng lịch sử hội thoại để trả lời.
Bạn được fine-tune để tự đánh giá triệu chứng, phát hiện tình trạng khẩn cấp,
định hướng chuyên khoa và đưa ra cảnh báo phù hợp. Không bịa dữ liệu còn thiếu.
Không thay thế đánh giá trực tiếp của nhân viên y tế.
Trả lời ngắn gọn, tối đa 150 từ, bằng tiếng Việt.
"""

class OllamaUnavailable(Exception):
    pass

def call_ollama(messages: list[dict]) -> str:
    payload = json.dumps({'model': OLLAMA_MODEL, 'messages': messages, 'stream': False}).encode('utf-8')
    request = urllib.request.Request(
        f'{OLLAMA_BASE_URL.rstrip("/")}/api/chat',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode('utf-8'))
        return str(data.get('message', {}).get('content', '')).strip()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        logger.warning('Ollama call failed: %s', exc)
        raise OllamaUnavailable(str(exc)) from exc

def _mock_reply(user_text: str, history: list[dict]) -> str:
    return 'Hiện chưa kết nối được với trợ lý AI. Vui lòng thử lại sau. Đây chỉ là thông tin định hướng, không thay thế ý kiến bác sĩ.'

def generate_reply(user_text: str, history: list[dict], patient_context: str = '') -> tuple[str, bool]:
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    if patient_context:
        messages.append({'role': 'system', 'content': f'Dữ liệu bệnh nhân hiện tại:\n{patient_context}'})
    messages += history + [{'role': 'user', 'content': user_text}]
    try:
        reply = call_ollama(messages)
        return (reply or _mock_reply(user_text, history)), False
    except OllamaUnavailable:
        return _mock_reply(user_text, history), False
    except Exception as exc:
        logger.warning('Unexpected chatbot provider error: %s', exc)
        return _mock_reply(user_text, history), False
