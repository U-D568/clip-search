import os
from typing import List

from ai.models.clip import load_clip_processor, get_device, load_clip_text_model
from infra.qdrant.repositories import AsyncQdrantRepository
from backend.ai.models.encoder import text_encoding, text_projection
from workers.worker import celery_app


@celery_app.task(queue="text_queue")
def text_embedding(text_query: str, video_id: int, topk=5) -> List[int]:
    # initaliation
    device = get_device()
    model = load_clip_text_model()
    model.to(device)
    processor = load_clip_processor()

    # text embedding and projection
    text_embeds = text_encoding(model, processor, text_query, device)
    text_embeds = text_projection(model, text_embeds)
    text_embeds = text_embeds.detach().cpu().tolist()

    qdrant_client = AsyncQdrantRepository.get_client()
    collection_name = os.environ["FRAME_COLLECTION"]
    qdrant_repo = AsyncQdrantRepository(qdrant_client, collection_name)
    timestamps = qdrant_repo.query_image_in_video(
        collection_name, text_embeds, video_id, topk
    )

    return timestamps
