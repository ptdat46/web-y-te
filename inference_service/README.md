# FastAPI inference service

Service nội bộ điều phối Qwen2.5-VL 3B qua Ollama, RAG local và guardrail phân luồng. Chạy từ thư mục gốc sau khi Ollama đã chạy và `ollama list` có đúng model tag:

```powershell
python -m venv .ai-venv
.\.ai-venv\Scripts\python.exe -m pip install -r inference_service\requirements.txt
$env:OLLAMA_TIMEOUT="300"
$env:OLLAMA_RETRIES="3"
$env:OLLAMA_RETRY_DELAY="2"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
.\.ai-venv\Scripts\python.exe -m uvicorn inference_service.main:app --host 127.0.0.1 --port 8100
```

Endpoints:

- `GET /health`: tiến trình và trạng thái đã nạp RAG.
- `GET /ready`: kiểm tra Ollama reachable và model tồn tại; trả `503` nếu chưa sẵn sàng.
- `POST /v1/chat`: multipart field `question` cho chat chữ.
- `POST /v1/analyze`: multipart fields `question`, tùy chọn `patient_context`, và file `image` (JPEG/PNG/WebP).

RAG mặc định đọc `AI Chatbot/data/rag_knowledge_base`. Qdrant là tùy chọn; khi chưa cấu hình, service dùng lexical retrieval deterministic và vẫn trả citation theo file/chunk. Không đặt PHI hoặc tài liệu không có quyền sử dụng vào knowledge base.
