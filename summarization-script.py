import os
import re
from pathlib import Path
from nltk.tokenize import sent_tokenize
from nltk import download
from transformers import pipeline
import argparse

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

def chunk_text(text, max_tokens=900):
    """
    Splits the input text into smaller chunks of up to `max_tokens` words.
    Args:
        text (str): The input text to chunk.
        max_tokens (int): Maximum number of tokens per chunk.
    Returns:
        list: A list of text chunks.
    """
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

def summarize_with_transformer(text, model_name="facebook/bart-large-cnn", max_chunk_length=900, max_length=180, min_length=60):
    """
    Summarizes the input text using a transformer-based summarization model.
    Args:
        text (str): The input text to summarize.
        model_name (str): The name of the transformer model to use.
        max_chunk_length (int): Maximum number of tokens per chunk.
        max_length (int): Maximum length of the summary for each chunk.
        min_length (int): Minimum length of the summary for each chunk.
    Returns:
        str: The summarized text.
    """
    try:
        summarizer = pipeline("summarization", model=model_name, tokenizer=model_name, use_fast=False)
        chunks = chunk_text(text, max_tokens=max_chunk_length)
        summaries = []
        for chunk in chunks:
            result = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
            summaries.append(result[0]['summary_text'])
        if len(summaries) > 1:
            combined = ' '.join(summaries)
            final_summary = summarizer(combined, max_length=max_length, min_length=min_length, do_sample=False)[0]['summary_text']
            return final_summary
        return summaries[0]
    except Exception as e:
        print(f"Error during summarization: {e}")
        return ""

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize text using a transformer model.")
    parser.add_argument("input_text", type=str, help="The input text to summarize.")
    parser.add_argument("--max_length", type=int, default=180, help="Maximum length of the summary.")
    parser.add_argument("--min_length", type=int, default=60, help="Minimum length of the summary.")
    args = parser.parse_args()

    # Example input text
    input_text = args.input_text
    summary = summarize_with_transformer(input_text, max_length=args.max_length, min_length=args.min_length)
    print("Summary:")
    print(summary)
