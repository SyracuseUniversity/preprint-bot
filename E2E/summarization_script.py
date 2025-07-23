import os
import re
from pathlib import Path
from nltk.tokenize import sent_tokenize
from nltk import download
from transformers import pipeline
import argparse
from transformers import AutoTokenizer

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
    text = re.sub(r'-\n', '', text)  # Remove hyphenated line breaks
    text = re.sub(r'\n+', ' ', text)  # Replace multiple line breaks with a single space
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'\[\d+\]', '', text)  # Remove references like [1], [2]
    text = re.sub(r'\([A-Za-z, ]+\d{4}\)', '', text)  # Remove in-text citations like (Author, 2023)
    return text.strip()

def extract_sections_from_txt(txt, exclude_sections=None):
    """
    Extracts sections from the input text, excluding specified sections.

    Args:
        txt (str): The input text containing sections.
        exclude_sections (list): List of section names to exclude (e.g., acknowledgements, references).

    Returns:
        list: A list of cleaned text for all included sections.
    """
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
    return [clean_text(section['text']) for section in sections]

def chunk_text(text, tokenizer, max_tokens=900):
    """
    Splits *text* so that each chunk is ≤ *max_tokens* **token** IDs
    (not words).  Works for any HF tokenizer.
    """
    token_ids = tokenizer.encode(
        text,
        add_special_tokens=False,
        return_tensors=None,
    )
    chunks = []
    for i in range(0, len(token_ids), max_tokens):
        ids = token_ids[i : i + max_tokens]
        chunks.append(tokenizer.decode(ids, skip_special_tokens=True))
    return chunks

def summarize_with_transformer(text, model_name="facebook/bart-large-cnn",
                               max_chunk_length=900, max_length=180):
    
    import torch
    device = 0 if torch.cuda.is_available() else -1


    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    summarizer = pipeline("summarization",
                          model=model_name,
                          tokenizer=tokenizer,
                          device=device,       # keep CPU (-1) or change to 0 for CUDA
                          truncation=True) # <- always truncate safely

    chunks = chunk_text(text, tokenizer, max_tokens=max_chunk_length)
    if not chunks:          # nothing to summarise
        return ""

    summaries = []
    for chunk in chunks:
        try:
            result = summarizer(chunk,
                                max_length=max_length,
                                min_length=60,
                                do_sample=False,
                                truncation=True)
            summaries.append(result[0]["summary_text"])
        except Exception as e:
            print(f"⚠️  Skipping tiny chunk: {e}")

    if not summaries:
        return "Error: Summarization failed."

    if len(summaries) == 1:
        return summaries[0]

    combined = " ".join(summaries)
    return summarizer(combined,
                      max_length=max_length,
                      min_length=60,
                      do_sample=False,
                      truncation=True)[0]["summary_text"]


def hierarchical_summarization(sections, model_name="facebook/bart-large-cnn", max_length=180):
    """
    Performs hierarchical summarization by summarizing each section and then combining the results.

    Args:
        sections (list): List of text sections to summarize.
        model_name (str): The name of the transformer model to use.
        max_length (int): Maximum length of the summary.

    Returns:
        str: The final summarized text.
    """
    try:
        section_summaries = []
        for sec in sections:
            if len(sec.split()) > 25:  # Only summarize sections with more than 25 words
                section_summaries.append(summarize_with_transformer(sec, model_name=model_name, max_length=max_length))
        combined = ' '.join(section_summaries)
        final_summary = summarize_with_transformer(combined, model_name=model_name, max_length=max_length)
        return final_summary
    except Exception as e:
        print(f"Error during hierarchical summarization: {e}")
        return "Error: Hierarchical summarization failed."

def process_folder(input_folder, output_folder, model_name="facebook/bart-large-cnn", max_length=180):
    """
    Summarizes the entire cleaned content of each input file directly, without section parsing.

    Args:
        input_folder (str): Path to folder containing GROBID-parsed `.txt` files.
        output_folder (str): Where to write *_summary.txt files.
        model_name (str): HuggingFace summarization model to use.
        max_length (int): Max summary length.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    for input_file in input_path.glob("*.txt"):
        try:
            print(f"Processing file: {input_file.name}")
            with open(input_file, "r", encoding="utf-8") as f:
                raw_text = f.read()

            cleaned = clean_text(raw_text)
            summary = summarize_with_transformer(cleaned, model_name=model_name, max_length=max_length)

            arxiv_id = input_file.stem.replace("_output", "").split("v")[0]
            output_file = output_path / f"{arxiv_id}_summary.txt"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary)

            print(f"Summary saved to: {output_file}")
        except Exception as e:
            print(f"Failed to process {input_file.name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize text files in a folder.")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the folder containing input text files.")
    parser.add_argument("--max_length", type=int, default=180, help="Maximum length of the summary (default: 180).")
    args = parser.parse_args()

    # Define the output folder as "summaries" in the current working directory
    output_folder = Path("summaries")
    process_folder(args.input_folder, output_folder, max_length=args.max_length)
