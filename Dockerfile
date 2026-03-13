FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY config.example.json .

# 如果没有 config.json，使用模板
RUN cp -n config.example.json config.json 2>/dev/null || true

EXPOSE 8200 8201

CMD ["python", "run_api.py", "--host", "0.0.0.0", "--port", "8200"]
