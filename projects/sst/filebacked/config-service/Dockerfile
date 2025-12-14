FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask pyyaml

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]