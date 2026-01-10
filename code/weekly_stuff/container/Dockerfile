FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir gradio

# Copy the application
COPY app/app.py /app/

# Expose Gradio's default port
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]