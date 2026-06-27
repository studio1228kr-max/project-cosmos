FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 컨테이너 stdout 즉시 flush — Railway 로그에 앱 출력이 보이게.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# --host :: : Railway 사설 네트워크/헬스체크는 IPv6 라 0.0.0.0(IPv4 전용)으로는
#   "service unavailable" 로 도달 실패한다. :: 듀얼스택이면 IPv6+IPv4 모두 수신.
# sh -c : $PORT 셸 확장 보장. 내부 서비스라 PORT 미주입 시 8000 폴백.
CMD ["sh", "-c", "uvicorn main:app --host :: --port ${PORT:-8000} --workers 2"]
