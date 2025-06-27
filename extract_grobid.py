# no download, works in memory

import requests
from urllib.parse import urlparse
from lxml import etree
import spacy
from pathlib import Path

nlp = spacy.load("en_core_web_sm")  # spaCy tokenizer

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

# tokenize text using spaCy
def spacy_tokenize(text):
    doc = nlp(text)
    return [token.text for token in doc if not token.is_space]

# extract PDF bytes from arXiv link
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

# send to GROBID and extract sections
def extract_grobid_sections_from_bytes(pdf_bytes):
    response = requests.post(GROBID_URL, files={'input': ('paper.pdf', pdf_bytes)})
    if response.status_code != 200:
        raise Exception(f"GROBID error: {response.status_code}")
    
    xml = etree.fromstring(response.content)

    title = xml.findtext('.//tei:titleStmt/tei:title', namespaces=NS) or "N/A"
    abstract_node = xml.find('.//tei:profileDesc/tei:abstract', namespaces=NS)
    abstract = " ".join(p.text for p in abstract_node.findall('.//tei:p', namespaces=NS)) if abstract_node is not None else "N/A"

    # Authors
    authors = []
    for pers in xml.findall('.//tei:sourceDesc//tei:analytic//tei:author', namespaces=NS):
        name = pers.find('.//tei:persName', namespaces=NS)
        if name is not None:
            full_name = " ".join(filter(None, [
                name.findtext('tei:forename', namespaces=NS),
                name.findtext('tei:surname', namespaces=NS)
            ]))
            full_name = full_name.replace(", -", "-")
            authors.append(full_name)

    # Affiliations
    affiliations = []
    for aff in xml.findall('.//tei:affiliation/tei:orgName[@type="institution"]', namespaces=NS):
        if aff.text:
            affiliations.append(aff.text)

    # Publication Date
    pub_date = xml.findtext('.//tei:publicationStmt/tei:date', namespaces=NS) or "N/A"

    # Section headers and paragraphs
    sections = []
    for div in xml.findall('.//tei:text//tei:body//tei:div', namespaces=NS):
        header = div.findtext('tei:head', namespaces=NS) or "[no section title]"
        paragraphs = " ".join(p.text.strip() for p in div.findall('tei:p', namespaces=NS) if p.text)
        sections.append({'header': header, 'text': paragraphs})

    return {
        'title': title.strip(),
        'abstract': abstract.strip(),
        'authors': authors,
        'affiliations': affiliations,
        'pub_date': pub_date.strip(),
        'sections': sections
    }
    
def process_folder(input_folder, output_folder):
    """
    Processes all PDFs in a folder, extracts structured data via GROBID, and saves tokenized output.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    for pdf_file in input_path.glob("*.pdf"):
        print(f"Processing: {pdf_file.name}")
        try:
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
            result = extract_grobid_sections_from_bytes(pdf_bytes)

            tokenized = {
                'title': spacy_tokenize(result['title']),
                'abstract': spacy_tokenize(result['abstract']),
                'sections': [
                    {
                        'header': sec['header'],
                        'tokens': spacy_tokenize(sec['text'])
                    } for sec in result['sections']
                ]
            }

            output_file = output_path / (pdf_file.stem + "_output.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Title: {result['title']}\n")
                f.write(f"Abstract: {result['abstract']}\n\n")
                f.write(f"Authors: {', '.join(result['authors'])}\n")
                f.write(f"Affiliations: {', '.join(result['affiliations'])}\n")
                f.write(f"Publication Date: {result['pub_date']}\n\n")
                f.write("Sections:\n")
                for sec in result['sections']:
                    f.write(f"\n- {sec['header']}:\n{sec['text']}\n")

                f.write("\nTokenized Title:\n")
                f.write(" ".join(tokenized['title']) + "\n")

                f.write("\nTokenized Abstract:\n")
                f.write(" ".join(tokenized['abstract']) + "\n")

                f.write("\nTokenized Sections:\n")
                for sec in tokenized['sections']:
                    f.write(f"\n- {sec['header']}:\n{' '.join(sec['tokens'])}\n")

            print(f"Saved: {output_file}")
        except Exception as e:
            print(f"Failed to process {pdf_file.name}: {e}")

if __name__ == "__main__":
    arxiv_url = "https://arxiv.org/abs/2304.12345"
    pdf_bytes, arxiv_id = get_arxiv_pdf_bytes(arxiv_url)
    result = extract_grobid_sections_from_bytes(pdf_bytes)
    
    # tokenize main fields with spaCy
    tokenized = {
        'title': spacy_tokenize(result['title']),
        'abstract': spacy_tokenize(result['abstract']),
        'sections': [
            {
                'header': sec['header'],
                'tokens': spacy_tokenize(sec['text'])
            } for sec in result['sections']
        ]
    }

    # write everything to output file
    with open(f"{arxiv_id}_output.txt", "w", encoding="utf-8") as f:
        f.write(f"Title: {result['title']}\n")
        f.write(f"Abstract: {result['abstract']}\n\n")
        f.write(f"Authors: {', '.join(result['authors'])}\n")
        f.write(f"Affiliations: {', '.join(result['affiliations'])}\n")
        f.write(f"Publication Date: {result['pub_date']}\n\n")

        f.write("Sections:\n")
        for sec in result['sections']:
            f.write(f"\n- {sec['header']}:\n{sec['text']}\n")
        
        # tokenized output
        f.write("\nTokenized Title:\n")
        f.write(" ".join(tokenized['title']) + "\n")

        f.write("\nTokenized Abstract:\n")
        f.write(" ".join(tokenized['abstract']) + "\n")

        f.write("\nTokenized Sections:\n")
        for sec in tokenized['sections']:
            f.write(f"\n- {sec['header']}:\n{' '.join(sec['tokens'])}\n")
