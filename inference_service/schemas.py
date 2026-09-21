from typing import Literal

from pydantic import BaseModel, Field


class SuspectedCondition(BaseModel):
    name: str = Field(max_length=200)
    likelihood: Literal["Thấp", "Trung bình", "Cao", "Không xác định"] = "Không xác định"
    rationale: str = Field(default="", max_length=1000)


class RedFlags(BaseModel):
    has_red_flag: bool = False
    warning_notes: str = Field(default="", max_length=1000)


class Citation(BaseModel):
    source: str = Field(max_length=255)
    title: str = Field(default="", max_length=255)
    page: str = Field(default="", max_length=50)
    chunk: str = Field(default="", max_length=100)


class AnalysisResult(BaseModel):
    schema_version: str = "dermatology-v1"
    visual_findings: str = Field(default="", max_length=3000)
    suspected_conditions: list[SuspectedCondition] = Field(default_factory=list, max_length=5)
    triage_level: Literal["Tu_theo_doi", "Kham_thuong_quy", "Kham_som", "Cap_cuu", "Chưa xác định"] = "Chưa xác định"
    urgency_label: str = Field(default="", max_length=255)
    recommended_specialty: str = Field(default="Chuyên khoa Da liễu", max_length=255)
    red_flags_check: RedFlags = Field(default_factory=RedFlags)
    initial_care_advice: list[str] = Field(default_factory=list, max_length=8)
    disclaimer: str = "Kết quả AI chỉ mang tính tham khảo, không thay thế khám trực tiếp."
    citations: list[Citation] = Field(default_factory=list, max_length=10)
    model_version: str = ""
    knowledge_base_version: str = "none"
    abstained: bool = False
    degraded: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str = "dermatology-inference"
    model: str = ""
    rag: bool = False


class ReadyResponse(HealthResponse):
    ollama_reachable: bool = False
    qdrant_reachable: bool = False
