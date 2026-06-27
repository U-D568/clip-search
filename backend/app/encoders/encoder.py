from typing import Union

import numpy as np
from transformers import CLIPModel, CLIPVisionModelWithProjection, CLIPProcessor, CLIPTextModelWithProjection
import torch

from app.utils.preprocess import get_eos_pos


def text_encoding(model, processor, text: str, device: str) -> torch.Tensor:
    text_inputs = processor(text=text, padding=True, return_tensors="pt")
    text_inputs = {k: v.to(device) for k, v in text_inputs.items()}
    eos_pos = get_eos_pos(text_inputs)
    with torch.no_grad():
        text_outputs = model(**text_inputs)
    last_hidden_state = text_outputs.last_hidden_state
    text_embeds = last_hidden_state[torch.arange(last_hidden_state.size(0)), eos_pos, :]

    return text_embeds


def text_projection(model, text_embeds: torch.Tensor) -> torch.Tensor:
    with torch.no_grad():
        return model.text_projection(text_embeds)


def image_embedding(
    model: CLIPVisionModelWithProjection,
    processor: CLIPProcessor,
    images: np.ndarray,
    device: str,
) -> torch.Tensor:
    image_inputs = processor(images=images, return_tensors="pt")
    image_inputs = {k: v.to(device) for k, v in image_inputs.items()}
    with torch.no_grad():
        image_outputs = model.vision_model(**image_inputs)
    return image_outputs.pooler_output


def image_projection(model, image_embeds: torch.Tensor) -> torch.Tensor:
    with torch.no_grad():
        return model.visual_projection(image_embeds)
