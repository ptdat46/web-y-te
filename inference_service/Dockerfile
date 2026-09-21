FROM python:3.12-slim
WORKDIR /app
COPY inference_service/requirements.txt /app/inference_service/requirements.txt
RUN pip install --no-cache-dir -r /app/inference_service/requirements.txt
COPY inference_service /app/inference_service
COPY "AI Chatbot/data/rag_knowledge_base" "/app/AI Chatbot/data/rag_knowledge_base"
CMD ["uvicorn", "inference_service.main:app", "--host", "0.0.0.0", "--port", "8100"]
