import torch


def l2_normalization(tensor: torch.Tensor) -> torch.Tensor:
    return tensor / tensor.norm(dim=-1, keepdim=True)


def cosine_similarity(tensor1, tensor2):
    return l2_normalization(tensor1) @ l2_normalization(tensor2).T
