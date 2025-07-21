
FROM python:3.11 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages

COPY smartcli/ ./smartcli/
COPY scli.py .

ENTRYPOINT ["python", "./scli.py"]


CMD ["help"]
