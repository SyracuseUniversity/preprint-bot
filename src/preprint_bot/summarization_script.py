import os
import re
from pathlib import Path
from nltk.tokenize import sent_tokenize
from nltk import download
from transformers import pipeline
import argparse
import torch
from llama_cpp import Llama

# NLTK setup
try:
    sent_tokenize("This is a test. This is only a test.")
except Exception:
    def sent_tokenize(text):
        return text.split('. ')

download('punkt')


# Text cleaning
def clean_text(text):
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\([A-Za-z, ]+\d{4}\)', '', text)
    return text.strip()


# Section extraction
def extract_sections_from_txt_markdown(txt, exclude_sections=None):
    if exclude_sections is None:
        exclude_sections = ['acknowledgement', 'acknowledgements', 'reference', 'references']
    sections = []
    current_header = None
    current_text = []

    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("### "):
            if current_header and current_text:
                if not any(excl in current_header.lower() for excl in exclude_sections):
                    sections.append({'header': current_header.lower(), 'text': ' '.join(current_text)})
            current_header = line[4:].strip()
            current_text = []
        else:
            if current_header:
                current_text.append(line)

    if current_header and current_text:
        if not any(excl in current_header.lower() for excl in exclude_sections):
            sections.append({'header': current_header.lower(), 'text': ' '.join(current_text)})

    return [{'header': s['header'], 'text': clean_text(s['text'])} for s in sections]


# Chunking for transformer
def chunk_text(text, max_tokens=900):
    sentences = sent_tokenize(text)
    chunks = []
    current = ''
    for sent in sentences:
        if len(current.split()) + len(sent.split()) < max_tokens:
            current += ' ' + sent
        else:
            chunks.append(current.strip())
            current = sent
    if current:
        chunks.append(current.strip())
    return chunks


# Transformer summarizer
class TransformerSummarizer:
    def __init__(self, model_name="google/pegasus-xsum"):
        device = 0 if torch.cuda.is_available() else -1
        print(f"Transformer summarizer using {'cuda:0' if device == 0 else 'cpu'}")
        self.summarizer = pipeline("summarization", model=model_name, tokenizer=model_name, use_fast=False, device=device)

    def summarize(self, text, max_length=180):
        chunks = chunk_text(text)
        summaries = []
        for chunk in chunks:
            if len(chunk.split()) < 20:
                continue
            try:
                result = self.summarizer(chunk, max_length=max_length, min_length=60, do_sample=False)
                summaries.append(result[0]['summary_text'])
            except Exception as e:
                print(f"Chunk summarization error: {e}")
        if len(summaries) > 1:
            try:
                combined = ' '.join(summaries)
                final_summary = self.summarizer(combined, max_length=max_length, min_length=60, do_sample=False)[0]['summary_text']
                return final_summary
            except Exception:
                return ' '.join(summaries)
        if summaries:
            return summaries[0]
        return "No valid chunks to summarize."


# LLaMA summarizer
class LlamaSummarizer:
    def __init__(self, model_path: str):
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=4,
            n_gpu_layers=20
        )

    def summarize(self, text: str, max_length: int = 200) -> str:
        tokens = self.llm.tokenize(text.encode("utf-8"))
        if len(tokens) > 1800:
            tokens = tokens[:1800]
            text = self.llm.detokenize(tokens).decode("utf-8", errors="ignore")
        prompt = (
            "You are an expert academic summarizer. "
            "Read the following research paper text and summarize what it is about clearly, "
            "Make it the length of a tweet (no ps no hashtags and use concise language):\n\n" # Try teling it its a tweet
            f"{text}\n\nSummary:"
        )
        result = self.llm(prompt, max_tokens=max_length, temperature=0.3, top_p=0.9, echo=False)
        if isinstance(result, dict):
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0].get("text", "").strip()
            if "text" in result:
                return result["text"].strip()
        return str(result).strip()


# Section-based summarization
def summarize_sections_single_paragraph(sections, summarizer, max_length=180):
    section_keywords = [
        ('introduction', 'Introduction'),
        ('method', 'Methods'),
        ('result', 'Results'),
        ('discussion', 'Discussion'),
        ('conclusion', 'Conclusions')
    ]
    section_texts = {label: "" for _, label in section_keywords}
    for sec in sections:
        header = sec['header'].lower()
        for key, label in section_keywords:
            if key in header and not section_texts[label]:
                section_texts[label] = sec['text']
    section_summaries = []
    for _, label in section_keywords:
        text = section_texts[label]
        if text and len(text.split()) > 25:
            section_summaries.append(summarizer.summarize(text, max_length=max_length))
    return ' '.join(section_summaries)


# File / Folder processing
def process_file(input_file, output_file, summarizer, max_length=180):
    with open(input_file, "r", encoding="utf-8") as f:
        txt = f.read()
    sections = extract_sections_from_txt_markdown(txt)
    summary = summarize_sections_single_paragraph(sections, summarizer, max_length=max_length)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"Summary saved to {output_file}")


def process_folder(input_folder, output_folder, summarizer, max_length=180):
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    input_path = Path(input_folder)

    for input_file in input_path.glob("*.txt"):
        output_file = output_path / f"{input_file.stem}_summary.txt"
        process_file(input_file, output_file, summarizer, max_length=max_length)

