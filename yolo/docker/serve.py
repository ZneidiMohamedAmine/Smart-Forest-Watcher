"""
Minimal inference server for the packaged YOLO26 ONNX model.
POST an image to /predict and get back raw model output.

YOLO26 is natively NMS-free/end-to-end, so no NMS post-processing step
is needed -- but you'll still want to add letterboxing (to match training
input size) and decode the raw output into (box, class, score) tuples
with the "smoke"/"fire" class names to match how smart_forest_watcher
consumes detections.
"""
import io

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, UploadFile
from PIL import Image

app = FastAPI()
session = ort.InferenceSession("model.onnx", providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((640, 640))
    arr = np.array(image).astype(np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)[None, ...]  # NCHW

    outputs = session.run(None, {input_name: arr})
    return {"raw_output_shape": [list(o.shape) for o in outputs]}
