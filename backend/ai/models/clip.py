import os

import torch
from transformers import CLIPModel, CLIPProcessor
from transformers import CLIPTextModelWithProjection, CLIPVisionModelWithProjection

_model = None
_vision_model = None
_text_model = None
_processor = None


def load_clip_model():
    global _model
    if _model is None:
        _model = CLIPModel.from_pretrained(
            os.environ["PRETRAINED_MODEL"], cache_dir=os.environ["MODEL_CACHE_DIR"]
        )
    return _model


def load_clip_text_model() -> CLIPTextModelWithProjection:
    global _text_model
    if _text_model is None:
        _text_model = CLIPTextModelWithProjection.from_pretrained(
            os.environ["PRETRAINED_MODEL"], cache_dir=os.environ["MODEL_CACHE_DIR"]
        )
    return _text_model


def load_clip_vision_model() -> CLIPVisionModelWithProjection:
    global _vision_model
    if _vision_model is None:
        _vision_model = CLIPVisionModelWithProjection.from_pretrained(
            os.environ["PRETRAINED_MODEL"], cache_dir=os.environ["MODEL_CACHE_DIR"]
        )
    return _vision_model


def load_clip_processor():
    global _processor
    if _processor is None:
        _processor = CLIPProcessor.from_pretrained(
            os.environ["PRETRAINED_MODEL"], cache_dir=os.environ["MODEL_CACHE_DIR"]
        )
    return _processor


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"
