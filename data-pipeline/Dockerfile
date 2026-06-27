# data-pipeline 서비스 — repo 루트가 빌드 컨텍스트이므로 COPY 경로는 data-pipeline/ 기준.
# Railway: RAILWAY_DOCKERFILE_PATH=data-pipeline/Dockerfile 로 지정.
FROM python:3.11-slim

WORKDIR /app

COPY data-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data-pipeline/ .

# Sprint #9: HERMES API(uvicorn) 구동 + startup에서 워커(scan+consume) 백그라운드.
# PORT는 Railway 주입(없으면 8000). COSMOS는 http://data-pipeline.railway.internal:8000 호출.
ENV PYTHONUNBUFFERED=1
# 복구: 작동하던 워커로 환원(백그라운드 scan/consume). HERMES 웹서버(api.py)는
# 별도 Railway 웹 서비스로 띄워야 함 — 동일 워커 서비스에서 uvicorn 기동이 Railway에서 불발.
CMD ["python", "main.py", "worker_only"]
