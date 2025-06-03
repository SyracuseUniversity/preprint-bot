import numpy as np
from sentence_transformers import SentenceTransformer
from config import MODEL_NAME

def embed_papers(papers):
    model = SentenceTransformer(MODEL_NAME)
    texts = [paper["title"] + ". " + paper["summary"] for paper in papers]
    embeddings = model.encode(texts, convert_to_tensor=False, normalize_embeddings=True)
    return texts, np.array(embeddings).astype("float32"), model
