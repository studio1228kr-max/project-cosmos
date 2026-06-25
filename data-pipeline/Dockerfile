# data-pipeline 서비스 — repo 루트가 빌드 컨텍스트이므로 COPY 경로는 data-pipeline/ 기준.
# Railway: RAILWAY_DOCKERFILE_PATH=data-pipeline/Dockerfile 로 지정.
FROM python:3.11-slim

WORKDIR /app

COPY data-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data-pipeline/ .

# Procfile worker 와 동일: scan 1회 → Redis consume 루프
CMD ["python", "main.py", "worker"]
