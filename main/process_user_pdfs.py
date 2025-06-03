import os, re, fitz
import numpy as np

def extract_text_from_pdf(file_path):
    try:
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def extract_title_and_abstract(text):
    text = re.sub(r'\s+', ' ', text)
    title_match = re.match(r'^(.{10,150}?)\.\s', text)
    title = title_match.group(1).strip() if title_match else "Unknown Title"

    abstract_match = re.search(r'(?i)(?:abstract)\s*[:.-]*\s*(.{100,2000}?)\s*(?=(?:introduction|1\s*\.|keywords|I\s*\.)|$)', text)
    abstract = abstract_match.group(1).strip() if abstract_match else text[:1000]
    return title, abstract

def process_user_papers(folder_path, model):
    user_texts = []
    user_metadata = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            text = extract_text_from_pdf(file_path)
            if text:
                title, abstract = extract_title_and_abstract(text)
                user_texts.append(title + ". " + abstract)
                user_metadata.append({"filename": filename, "title": title})

    embeddings = model.encode(user_texts, convert_to_tensor=False, normalize_embeddings=True)
    return user_texts, np.array(embeddings).astype("float32"), user_metadata
