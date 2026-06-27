# data-pipeline 서비스 — repo 루트가 빌드 컨텍스트이므로 COPY 경로는 data-pipeline/ 기준.
# Railway: RAILWAY_DOCKERFILE_PATH=data-pipeline/Dockerfile 로 지정.
FROM python:3.11-slim

WORKDIR /app

COPY data-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data-pipeline/ .

# Sprint #9: HERMES API(uvicorn) 구동 + startup에서 워커(scan+consume) 백그라운드.
# PORT는 Railway 주입(없으면 8000). COSMOS는 http://data-pipeline.railway.internal:8000 호출.
# Railway 사설망은 IPv6 전용 → ::로 바인딩. -u(unbuffered)로 기동/에러 로그 노출.
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "echo BOOT PORT=$PORT; python -u -m uvicorn api:app --host :: --port ${PORT:-8000}"]
