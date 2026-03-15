# Example Dockerfile - should PASS validation
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app /app
COPY . .
CMD ["python", "main.py"]
