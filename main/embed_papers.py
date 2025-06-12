import os
import numpy as np
from sentence_transformers import SentenceTransformer

def load_model(model_name):
    return SentenceTransformer(model_name)

def embed_abstracts(processed_folder, model_name):
    model = load_model(model_name)
    texts = []
    filenames = []

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue
        with open(os.path.join(processed_folder, file), "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) < 2:
                print(f"⚠️ Skipping malformed file: {file}")
                continue
            title = lines[0].replace("Title: ", "").strip()
            abstract = lines[1].replace("Abstract: ", "").strip()
            text = title + ". " + abstract
            texts.append(text)
            filenames.append(file)

    if not texts:
        raise ValueError(f"No abstracts found in {processed_folder}. Did GROBID fail to extract content?")

    embeddings = model.encode(texts, convert_to_tensor=False, normalize_embeddings=True)
    return texts, np.array(embeddings).astype("float32"), model, filenames


def embed_sections(processed_folder, model):
    paper_sections = {}

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue
        with open(os.path.join(processed_folder, file), "r", encoding="utf-8") as f:
            lines = f.readlines()

        sections = []
        current_header = None
        current_text = ""
        for line in lines:
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                if current_header and current_text:
                    sections.append((current_header, current_text.strip()))
                parts = line.split(":", 1)
                current_header = parts[0][2:].strip()
                current_text = parts[1].strip()
            elif line:
                current_text += " " + line

        if current_header and current_text:
            sections.append((current_header, current_text.strip()))

        chunk_embeddings = []
        for header, text in sections:
            if len(text) > 20:
                emb = model.encode(text, convert_to_tensor=False, normalize_embeddings=True)
                chunk_embeddings.append(emb)

        if chunk_embeddings:
            paper_sections[file] = np.array(chunk_embeddings).astype("float32")

    return paper_sections
