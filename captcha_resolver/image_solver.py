"""
Image Solver - Giải captcha ảnh bằng ONNX local
"""

import os
import io
import numpy as np
from PIL import Image
import onnxruntime
from typing import Optional, Dict, Any, Union


class ImageSolver:
    """Giải captcha ảnh bằng ONNX AI model"""
    
    def __init__(self, model_path: str = 'best.onnx', bot=None):
        self.model_path = model_path
        self.bot = bot
        self.canvas_size = 384
        self.alphabet = "abcdefghijklmnopqrstuvwxyz"
        self.min_score = 0.3
        self.pad = (114, 114, 114)
        
        self._engine = None
        self._feed = None
        self._loaded = False
        self._load_model()
    
    def _log(self, level: str, msg: str):
        if self.bot:
            self.bot.log(level, f"[ImageSolver] {msg}")
    
    def _load_model(self):
        """Load ONNX model"""
        try:
            if not os.path.exists(self.model_path):
                self._log("WARN", f"Model not found: {self.model_path}")
                return
            
            self._engine = onnxruntime.InferenceSession(
                self.model_path,
                providers=["CPUExecutionProvider"]
            )
            self._feed = self._engine.get_inputs()[0].name
            self._loaded = True
            self._log("INFO", f"✅ Model loaded: {self.model_path}")
        except Exception as e:
            self._log("ERROR", f"Failed to load model: {e}")
            self._loaded = False
    
    def _fit_square(self, frame: np.ndarray) -> np.ndarray:
        """Resize ảnh về square với padding"""
        pic = Image.fromarray(frame)
        width, height = pic.size
        ratio = min(self.canvas_size / width, self.canvas_size / height)
        target = (max(1, int(width * ratio)), max(1, int(height * ratio)))
        shrunk = pic.resize(target, Image.BILINEAR)
        
        canvas = Image.new("RGB", (self.canvas_size, self.canvas_size), self.pad)
        offset = ((self.canvas_size - target[0]) // 2, 
                  (self.canvas_size - target[1]) // 2)
        canvas.paste(shrunk, offset)
        return np.asarray(canvas)
    
    def _to_tensor(self, frame: np.ndarray) -> np.ndarray:
        """Chuyển frame thành tensor cho ONNX"""
        tensor = self._fit_square(frame).astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))
        return tensor[np.newaxis, ...]
    
    def solve(self, image_data: Union[bytes, str, Image.Image], expected_length: int = 6) -> Optional[str]:
        """
        Giải captcha ảnh
        
        Args:
            image_data: bytes, file path, hoặc PIL Image
            expected_length: Số ký tự mong đợi
        
        Returns:
            str: Captcha text hoặc None nếu thất bại
        """
        try:
            if not self._loaded:
                self._log("ERROR", "Model not loaded")
                return None
            
            # Load image
            if isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, str) and os.path.exists(image_data):
                img = Image.open(image_data)
            elif isinstance(image_data, Image.Image):
                img = image_data
            else:
                self._log("ERROR", "Invalid image data")
                return None
            
            img = img.convert("RGB")
            frame = np.asarray(img)
            
            # Inference
            tensor = self._to_tensor(frame)
            raw = self._engine.run(None, {self._feed: tensor})[0][0]
            
            # Parse results
            found = []
            for row in raw:
                ax, ay, bx, by, score, label = row
                if score < self.min_score:
                    continue
                found.append((float((ax + bx) / 2), float(score), self.alphabet[int(label)]))
            
            if not found:
                return None
            
            # Filter by expected length
            if expected_length and len(found) > expected_length:
                found.sort(key=lambda item: item[1], reverse=True)
                found = found[:expected_length]
            
            # Sort by position và ghép text
            found.sort(key=lambda item: item[0])
            result = "".join(item[2] for item in found)
            
            return result if len(result) >= 3 else None
            
        except Exception as e:
            self._log("ERROR", f"Solve failed: {e}")
            return None
    
    def is_available(self) -> bool:
        """Kiểm tra solver có sẵn sàng không"""
        return self._loaded