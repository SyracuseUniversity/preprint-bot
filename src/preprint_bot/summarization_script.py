import os
import re
from pathlib import Path
from nltk.tokenize import sent_tokenize
from nltk import download
from transformers import pipeline
import argparse
import torch

# Fallback for NLTK punkt_tab bug on Python 3.13
try:
    from nltk.tokenize import sent_tokenize
    sent_tokenize("This is a test. This is only a test.")
except Exception:
    def sent_tokenize(text):
        return text.split('. ')

# Download necessary NLTK data
download('punkt')

def clean_text(text):
    """
    Cleans the input text by removing unnecessary characters, line breaks, and references.

    Args:
        text (str): The input text to clean.

    Returns:
        str: The cleaned text.
    """
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\([A-Za-z, ]+\d{4}\)', '', text)
    return text.strip()

def extract_sections_from_txt(txt, exclude_sections=None):
    if exclude_sections is None:
        exclude_sections = ['acknowledgement', 'acknowledgements', 'reference', 'references']
    sections = []
    current_header = None
    current_text = []
    in_sections = False

    for line in txt.splitlines():
        line = line.strip()
        if line == "Sections:":
            in_sections = True
            continue
        if not in_sections:
            continue
        if line.startswith('- ') and ':' in line:
            if current_header and current_text:
                if not any(excl in current_header for excl in exclude_sections):
                    sections.append({'header': current_header, 'text': ' '.join(current_text)})
            current_header = line[2:line.index(':')].strip().lower()
            current_text = [line[line.index(':')+1:].strip()]
        elif current_header:
            current_text.append(line)
    if current_header and current_text:
        if not any(excl in current_header for excl in exclude_sections):
            sections.append({'header': current_header, 'text': ' '.join(current_text)})

    # Clean text and return all included sections
    return [{'header': section['header'], 'text': clean_text(section['text'])} for section in sections]

def extract_sections_from_txt_markdown(txt, exclude_sections=None):
    if exclude_sections is None:
        exclude_sections = ['acknowledgement', 'acknowledgements', 'reference', 'references']
    sections = []
    current_header = None
    current_text = []

    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("### "):  # Markdown level 3 header
            # Save previous section
            if current_header and current_text:
                if not any(excl in current_header for excl in exclude_sections):
                    sections.append({'header': current_header.lower(), 'text': ' '.join(current_text)})
            current_header = line[4:].strip()
            current_text = []
        else:
            if current_header:
                current_text.append(line)

    # Save last section
    if current_header and current_text:
        if not any(excl in current_header for excl in exclude_sections):
            sections.append({'header': current_header.lower(), 'text': ' '.join(current_text)})

    # Clean texts
    return [{'header': s['header'], 'text': clean_text(s['text'])} for s in sections]

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

def summarize_with_transformer(text, model_name = "google/pegasus-xsum", max_chunk_length=900, max_length=280):
    """
    Summarizes the input text using a transformer-based summarization model.

    Uses GPU if available.

    Args:
        text (str): The input text to summarize.
        model_name (str): The name of the transformer model to use.
        max_chunk_length (int): Maximum number of tokens per chunk.
        max_length (int): Maximum length of the summary.

    Returns:
        str: The summarized text.
    """
    try:
        device = device = 0 if torch.cuda.is_available() else -1
        print(f"Device set to use {'cuda:0' if device == 0 else 'cpu'}")

        summarizer = pipeline("summarization", model=model_name, tokenizer=model_name, use_fast=False, device=device)
        chunks = chunk_text(text, max_tokens=max_chunk_length)
        summaries = []
        for i, chunk in enumerate(chunks):
            chunk_len = len(chunk.split())
            print(f"Chunk {i} length: {chunk_len}")
            if chunk_len < 20:
                print(f"Skipping chunk {i} due to short length.")
                continue
            print(f"Chunk {i} preview: {chunk[:100]}")

            try:
                result = summarizer(chunk, max_length=max_length, min_length=60, do_sample=False)
                summaries.append(result[0]['summary_text'])
            except Exception as e:
                print(f"Error summarizing chunk {i}: {e}")
                print(f"Chunk {i} content preview: {chunk[:200]}")
                # Optionally skip the chunk or break here
                continue

        if len(summaries) > 1:
            combined = ' '.join(summaries)
            try:
                final_summary = summarizer(combined, max_length=max_length, min_length=60, do_sample=False)[0]['summary_text']
                return final_summary
            except Exception as e:
                print(f"Error summarizing combined chunks: {e}")
                return ' '.join(summaries)  # fallback

        if summaries:
            return summaries[0]

        return "No valid chunks to summarize."

    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Error: Summarization failed."

def summarize_sections_single_paragraph(sections, model_name="google/pegasus-xsum", max_length=180):
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
            summary = summarize_with_transformer(text, model_name=model_name, max_length=max_length)
            section_summaries.append(summary)
    return ' '.join(section_summaries)

def summarize_abstract_only(sections, model_name="google/pegasus-xsum", max_length=180):
    abstract_text = ""
    for sec in sections:
        if 'abstract' in sec['header'].lower():
            abstract_text = sec['text']
            break
    if abstract_text and len(abstract_text.split()) > 10:  # some minimal length to summarize
        return summarize_with_transformer(abstract_text, model_name=model_name, max_length=max_length)
    return "No abstract found or abstract too short to summarize."

def process_folder(input_folder, output_folder, model_name="google/pegasus-xsum", max_length=180):
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    for input_file in input_path.glob("*.txt"):
        try:
            print(f"Processing file: {input_file.name}")
            with open(input_file, "r", encoding="utf-8") as f:
                txt = f.read()
            sections = extract_sections_from_txt_markdown(txt)
            summary = summarize_sections_single_paragraph(sections, model_name=model_name, max_length=max_length)
            output_file = output_path / f"{input_file.stem}_summary.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"Summary saved to: {output_file}")
        except Exception as e:
            print(f"Failed to process {input_file.name}: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize text files in a folder.")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the folder containing input text files.")
    parser.add_argument("--max_length", type=int, default=180, help="Maximum length of the summary for each section (default: 180).")
    args = parser.parse_args()

    output_folder = Path("summaries")
    process_folder(args.input_folder, output_folder, max_length=args.max_length)
