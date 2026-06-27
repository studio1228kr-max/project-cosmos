# data-pipeline 서비스 — repo 루트가 빌드 컨텍스트이므로 COPY 경로는 data-pipeline/ 기준.
# Railway: RAILWAY_DOCKERFILE_PATH=data-pipeline/Dockerfile 로 지정.
FROM python:3.11-slim

WORKDIR /app

COPY data-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data-pipeline/ .

# Sprint #9: HERMES API(uvicorn) 구동 + startup에서 워커(scan+consume) 백그라운드.
# PORT는 Railway 주입(없으면 8000). COSMOS는 http://data-pipeline.railway.internal:8000 호출.
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
