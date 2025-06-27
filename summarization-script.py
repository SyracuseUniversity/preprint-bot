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
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\([A-Za-z, ]+\d{4}\)', '', text)
    return text.strip()

def extract_sections_from_txt(txt, exclude_sections=None):
    """
    Extracts sections from the input text, excluding specified sections.

    Args:
        txt (str): The input text containing sections.
        exclude_sections (list, optional): List of section names to exclude (e.g., acknowledgements, references).
            Defaults to ['acknowledgement', 'acknowledgements', 'reference', 'references'].

    Returns:
        list: A list of dictionaries with 'header' and 'text' for all included sections.
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
    return [{'header': section['header'], 'text': clean_text(section['text'])} for section in sections]

def chunk_text(text, max_tokens=900):
    """
    Splits the input text into smaller chunks of up to `max_tokens` words.

    Args:
        text (str): The input text to chunk.
        max_tokens (int): Maximum number of tokens (words) per chunk.

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

def summarize_with_transformer(text, model_name="facebook/bart-large-cnn", max_chunk_length=900, max_length=180):
    """
    Summarizes the input text using a transformer-based summarization model.

    Args:
        text (str): The input text to summarize.
        model_name (str): The name of the transformer model to use.
        max_chunk_length (int): Maximum number of tokens per chunk.
        max_length (int): Maximum length of the summary.

    Returns:
        str: The summarized text.
    """
    try:
        summarizer = pipeline("summarization", model=model_name, tokenizer=model_name, use_fast=False)
        chunks = chunk_text(text, max_tokens=max_chunk_length)
        summaries = []
        for chunk in chunks:
            result = summarizer(chunk, max_length=max_length, min_length=60, do_sample=False)
            summaries.append(result[0]['summary_text'])
        if len(summaries) > 1:
            combined = ' '.join(summaries)
            final_summary = summarizer(combined, max_length=max_length, min_length=60, do_sample=False)[0]['summary_text']
            return final_summary
        return summaries[0]
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Error: Summarization failed."

def summarize_sections_single_paragraph(sections, model_name="facebook/bart-large-cnn", max_length=180):
    """
    Summarizes each canonical section (Introduction, Methods, Results, Discussion, Conclusions) individually,
    then concatenates all section summaries into a single paragraph.

    Args:
        sections (list): List of dictionaries with 'header' and 'text' for each section.
        model_name (str): The name of the transformer model to use.
        max_length (int): Maximum length of the summary for each section.

    Returns:
        str: A single-paragraph summary of all sections.
    """
    # Section keywords and canonical order
    section_keywords = [
        ('introduction', 'Introduction'),
        ('method', 'Methods'),
        ('result', 'Results'),
        ('discussion', 'Discussion'),
        ('conclusion', 'Conclusions')
    ]
    # Map to hold the best-matching text for each section
    section_texts = {label: "" for _, label in section_keywords}
    for sec in sections:
        header = sec['header'].lower()
        for key, label in section_keywords:
            if key in header and not section_texts[label]:
                section_texts[label] = sec['text']
    # Summarize each section individually
    section_summaries = []
    for _, label in section_keywords:
        text = section_texts[label]
        if text and len(text.split()) > 25:
            summary = summarize_with_transformer(text, model_name=model_name, max_length=max_length)
            section_summaries.append(summary)
    # Concatenate all section summaries into a single paragraph
    return ' '.join(section_summaries)

def process_folder(input_folder, output_folder, model_name="facebook/bart-large-cnn", max_length=180):
    """
    Processes all text files in the input folder, summarizes their content, and saves the summaries.

    Args:
        input_folder (str): Path to the folder containing input text files.
        output_folder (str): Path to the folder where summaries will be saved.
        model_name (str): The name of the transformer model to use.
        max_length (int): Maximum length of the summary for each section.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    for input_file in input_path.glob("*.txt"):
        try:
            print(f"Processing file: {input_file.name}")
            with open(input_file, "r", encoding="utf-8") as f:
                txt = f.read()
            sections = extract_sections_from_txt(txt)
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
