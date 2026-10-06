"""Run converted models through the existing checkpoint evaluators on CPU."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import onnxruntime as ort
import torch
from transformers import AutoConfig


class OnnxModel:
    """Expose the config and tensor outputs that both evaluators consume."""

    def __init__(self, checkpoint, onnx_path):
        self.config = AutoConfig.from_pretrained(checkpoint, local_files_only=True)
        self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        with Path(onnx_path).open("rb") as stream:
            self.artifact = {
                "filename": Path(onnx_path).name,
                "sha256": hashlib.file_digest(stream, "sha256").hexdigest(),
                "onnxruntime_version": ort.__version__,
                "provider": "CPUExecutionProvider",
            }

    def __call__(self, **inputs):
        feeds = {
            item.name: inputs[item.name].detach().cpu().numpy()
            for item in self.session.get_inputs()
        }
        names = ["logits"]
        if self.config.model_type == "rt_detr_v2":
            names.append("pred_boxes")
        values = self.session.run(names, feeds)
        if any(not np.isfinite(value).all() for value in values):
            raise ValueError("ONNX evaluation returned NaN or infinity")
        return SimpleNamespace(**{
            name: torch.from_numpy(value) for name, value in zip(names, values)
        })
