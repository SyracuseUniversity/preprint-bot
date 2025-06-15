import re
import requests
from urllib.parse import urlparse
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk import download
from transformers import pipeline
from extract_grobid import extract_grobid_sections_from_bytes

# Download necessary NLTK data
download('punkt')
download('stopwords')

def clean_text(text):
    text = re.sub(r'-\n', '', text)  # Remove hyphenation at line breaks
    text = re.sub(r'\n+', ' ', text) # Replace newlines with space
    text = re.sub(r'\s+', ' ', text) # Collapse multiple spaces
    text = re.sub(r'\[\d+\]', '', text) # Remove [1], [2], etc.
    text = re.sub(r'\([A-Za-z, ]+\d{4}\)', '', text) # Remove (Smith et al., 2020)
    return text.strip()

def get_arxiv_pdf_bytes(arxiv_url):
    parsed = urlparse(arxiv_url)
    if "arxiv.org" not in parsed.netloc:
        raise ValueError("Not a valid arXiv link")
    arxiv_id = parsed.path.strip("/").split("/")[-1]
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    print(f"Fetching {pdf_url}")
    response = requests.get(pdf_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download PDF: {response.status_code}")
    return response.content, arxiv_id

def extract_sections(result, section_names=None):
    # section_names: list of lower-case section names to prioritize
    sections = result.get('sections', [])
    selected = []
    for section in sections:
        header = section['header'].lower()
        if section_names:
            if any(name in header for name in section_names):
                selected.append(clean_text(section['text']))
        else:
            selected.append(clean_text(section['text']))
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

def summarize_with_transformer(text, model_name="google/pegasus-cnn_dailymail", max_chunk_length=900):
    summarizer = pipeline("summarization", model=model_name)
    chunks = chunk_text(text, max_tokens=max_chunk_length)
    summaries = [summarizer(chunk, max_length=180, min_length=60, do_sample=False)[0]['summary_text'] for chunk in chunks]
    if len(summaries) > 1:
        combined = ' '.join(summaries)
        final_summary = summarizer(combined, max_length=180, min_length=60, do_sample=False)[0]['summary_text']
        return final_summary
    return summaries[0]

def hierarchical_summarization(sections, model_name="google/pegasus-cnn_dailymail"):
    # Summarize each section, then summarize the summaries
    section_summaries = []
    for sec in sections:
        if len(sec.split()) > 50:
            section_summaries.append(summarize_with_transformer(sec, model_name=model_name))
    combined = ' '.join(section_summaries)
    final_summary = summarize_with_transformer(combined, model_name=model_name)
    return final_summary

def highlight_technical_terms(text):
    words = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word.isalnum() and word.lower() not in stop_words]
    freq_dist = FreqDist(filtered_words)
    technical_terms = [word for word, freq in freq_dist.items() if freq > 1 and len(word) > 5]
    highlighted_content = text
    for term in technical_terms:
        highlighted_content = re.sub(rf'\b{term}\b', f"**{term}**", highlighted_content)
    return highlighted_content, technical_terms

if __name__ == "__main__":
    arxiv_url = "https://arxiv.org/abs/2304.12345"
    pdf_bytes, arxiv_id = get_arxiv_pdf_bytes(arxiv_url)
    result = extract_grobid_sections_from_bytes(pdf_bytes)
    # Prioritize abstract, introduction, methods, results, conclusion
    section_names = ['abstract', 'introduction', 'method', 'result', 'discussion', 'conclusion', 'summary']
    selected_sections = extract_sections(result, section_names=section_names)
    # Hierarchical summarization
    summary = hierarchical_summarization(selected_sections, model_name="google/pegasus-cnn_dailymail")
    highlighted_content, technical_terms = highlight_technical_terms(summary)
    with open(f"{arxiv_id}_output.txt", "w", encoding="utf-8") as f:
        f.write(highlighted_content)
        f.write("\n\n### Technical Terms ###\n")
        f.write(", ".join(technical_terms))