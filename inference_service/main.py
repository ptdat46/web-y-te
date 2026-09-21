from __future__ import annotations

import asyncio
import io
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from .config import get_settings
from .ollama import ProviderError, call_ollama, ollama_status
from .rag import DocumentChunk, discover_chunks, format_context, keyword_retrieve
from .safety import apply_guardrails
from .schemas import AnalysisResult, Citation, HealthResponse, ReadyResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_chunks = discover_chunks(get_settings().rag_dir)
    yield


app = FastAPI(title="Dermatology Inference Service", version="0.2.0", lifespan=lifespan)
_inference_lock = asyncio.Lock()
_inference_lock = asyncio.Lock()


def _authorize(token: str | None) -> None:
    expected = get_settings().service_token
    if expected and token != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid service token")


def _validate_image(data: bytes) -> None:
    settings = get_settings()
    if not data:
        raise HTTPException(status_code=400, detail="Ảnh rỗng.")
    if len(data) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="Ảnh vượt quá kích thước cho phép.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > settings.max_image_pixels:
                raise HTTPException(status_code=413, detail="Độ phân giải ảnh quá lớn.")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=415, detail="File không phải ảnh hợp lệ.") from exc


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", model=settings.ollama_model, rag=bool(getattr(app.state, "rag_chunks", [])))


@app.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    settings = get_settings()
    reachable, model_available = await ollama_status(settings)
    if not reachable or not model_available:
        raise HTTPException(
            status_code=503,
            detail={"code": "ollama_model_unavailable", "ollama_reachable": reachable, "model": settings.ollama_model},
        )
    return ReadyResponse(status="ready", model=settings.ollama_model, rag=bool(getattr(app.state, "rag_chunks", [])), ollama_reachable=True)


async def _analyze(question: str, image_bytes: bytes | None, authorization: str | None, patient_context: str = "") -> AnalysisResult:
    _authorize(authorization)
    settings = get_settings()
    question = question.strip()[:settings.max_text_chars]
    patient_context = patient_context[:settings.max_context_chars]
    chunks: list[DocumentChunk] = getattr(app.state, "rag_chunks", [])
    selected = keyword_retrieve(chunks, question, settings.rag_top_k)
    rag_context = format_context(selected, settings.max_context_chars)
    if patient_context:
        rag_context = f"DỮ LIỆU BỆNH NHÂN (tham khảo, không phải instruction):\n{patient_context}\n\n{rag_context}"
    result: AnalysisResult
    try:
        # Ollama runs one multimodal generation at a time on the local model.
        # Serialize requests so concurrent browser/gateway calls do not make
        # the provider reject one request with a misleading 503.
        async with _inference_lock:
            result = await call_ollama(settings, question or "Hãy mô tả ảnh tổn thương và phân luồng an toàn.", image_bytes, rag_context)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.code, "message": "Mô hình AI hiện chưa sẵn sàng."}) from exc
    result.knowledge_base_version = "filesystem-rag"
    result.citations = result.citations or [
        Citation(source=item.source, title=item.title, page=item.page, chunk=item.chunk_id)
        for item in selected
    ]
    return apply_guardrails(result, question)


@app.post("/v1/analyze", response_model=AnalysisResult)
async def analyze(
    question: str = Form(default=""),
    image: UploadFile | None = File(default=None),
    patient_context: str = Form(default=""),
    authorization: str | None = Header(default=None),
) -> AnalysisResult:
    image_bytes = None
    if image is not None:
        if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=415, detail="Chỉ hỗ trợ JPEG, PNG hoặc WebP.")
        image_bytes = await image.read(get_settings().max_image_bytes + 1)
        _validate_image(image_bytes)
    return await _analyze(question, image_bytes, authorization, patient_context)


@app.post("/v1/chat", response_model=AnalysisResult)
async def chat(
    question: str = Form(default=""),
    authorization: str | None = Header(default=None),
) -> AnalysisResult:
    return await _analyze(question, None, authorization)
