# Minimal ONNX Runtime inference image for the trained YOLO model.
# The workflow copies the exported model.onnx into this directory before build.
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir onnxruntime fastapi uvicorn pillow numpy opencv-python-headless

COPY model.onnx /app/model.onnx
COPY serve.py /app/serve.py

EXPOSE 8080
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8080"]
