from transformers.feature_extraction_utils import BatchFeature


def get_eos_pos(inputs: BatchFeature):
    attn_mask = inputs["attention_mask"]
    eos_pos = attn_mask.sum(dim=-1) - 1
    return eos_pos
