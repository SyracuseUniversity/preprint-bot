import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk import download
from transformers import pipeline
 
# Import your GROBID extraction functions
from extract_grobid import get_arxiv_pdf_bytes, extract_grobid_sections_from_bytes
 
# Fallback for NLTK punkt_tab bug on Python 3.13
try:
    from nltk.tokenize import sent_tokenize, word_tokenize
    sent_tokenize("This is a test. This is only a test.")
    word_tokenize("This is a test.")
except Exception:
    def sent_tokenize(text):
        return text.split('. ')
    def word_tokenize(text):
        return text.split()
 
# Download necessary NLTK data
download('punkt')
download('stopwords')
 
def clean_text(text):
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\([A-Za-z, ]+\d{4}\)', '', text)
    return text.strip()
 
def extract_sections_from_txt(txt, section_names=None):
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
                sections.append({'header': current_header, 'text': ' '.join(current_text)})
            current_header = line[2:line.index(':')].strip().lower()
            current_text = [line[line.index(':')+1:].strip()]
        elif current_header:
            current_text.append(line)
    if current_header and current_text:
        sections.append({'header': current_header, 'text': ' '.join(current_text)})
    selected = []
    if section_names:
        for section in sections:
            if any(name in section['header'] for name in section_names):
                selected.append(clean_text(section['text']))
    else:
        selected = [clean_text(section['text']) for section in sections]
    return selected
 
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
 
def summarize_with_transformer(text, model_name="facebook/bart-large-cnn", max_chunk_length=900):
    summarizer = pipeline("summarization", model=model_name, tokenizer=model_name, use_fast=False)
    chunks = chunk_text(text, max_tokens=max_chunk_length)
    summaries = [summarizer(chunk, max_length=180, min_length=60, do_sample=False)[0]['summary_text'] for chunk in chunks]
    if len(summaries) > 1:
        combined = ' '.join(summaries)
        final_summary = summarizer(combined, max_length=180, min_length=60, do_sample=False)[0]['summary_text']
        return final_summary
    return summaries[0]
 
def hierarchical_summarization(sections, model_name="facebook/bart-large-cnn"):
    section_summaries = []
    for sec in sections:
        if len(sec.split()) > 50:
            section_summaries.append(summarize_with_transformer(sec, model_name=model_name))
    combined = ' '.join(section_summaries)
    final_summary = summarize_with_transformer(combined, model_name=model_name)
    return final_summary
 
if __name__ == "__main__":
    arxiv_id = "2304.12345"  # Change as needed
    with open(f"{arxiv_id}_output.txt", "r", encoding="utf-8") as f:
        txt = f.read()
    section_names = ['abstract', 'introduction', 'method', 'result', 'discussion', 'conclusion', 'summary']
    selected_sections = extract_sections_from_txt(txt, section_names=section_names)
    summary = hierarchical_summarization(selected_sections, model_name="facebook/bart-large-cnn")
    with open(f"{arxiv_id}_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
 