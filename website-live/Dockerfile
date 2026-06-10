FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
# Each open WebSocket pins a thread for its whole lifetime, so threads caps the
# number of concurrent users before requests queue/hang (#81).
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "16", "--worker-class", "gthread", "--timeout", "300", "app:app"]
