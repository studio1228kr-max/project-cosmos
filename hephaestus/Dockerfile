FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# sh -c 로 셸 확장을 보장하고, Railway 가 PORT 를 안 넣어주는 경우(내부 서비스)
# 8000 으로 폴백한다. exec/shell 어느 쪽으로 호출돼도 $PORT 가 리터럴로 새지 않는다.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
