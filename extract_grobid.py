import os
import re
import requests
from lxml import etree
from pathlib import Path
from urllib.parse import urlparse

# Optional spaCy tokenizer
try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except ImportError:
    NLP = None

# Constants
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def spacy_tokenize(text):
    """
    Tokenizes input text into sentences using spaCy if available,
    otherwise falls back to splitting on double newlines.
    """
    if NLP:
        return [sent.text.strip() for sent in NLP(text).sents]
    else:
        return [s.strip() for s in text.split("\n\n") if s.strip()]

def extract_grobid_sections_from_bytes(pdf_bytes):
    """
    Send PDF bytes to GROBID and extract metadata, abstract, sections, and references.

    Returns:
        dict with: title, abstract, authors, affiliations, publication_date, sections, references
    """
    response = requests.post(
        GROBID_URL,
        files={'input': ('file.pdf', pdf_bytes)},
        data={'consolidateHeader': '1'},
        timeout=30
    )
    response.raise_for_status()
    root = etree.fromstring(response.content)

    def xpath_text(el, path):
        found = el.find(path, NS)
        return found.text.strip() if found is not None and found.text else ""

    title = xpath_text(root, ".//tei:titleStmt/tei:title")
    abstract = xpath_text(root, ".//tei:profileDesc/tei:abstract")
    authors = [
        " ".join(filter(None, [
            author.findtext("tei:forename", namespaces=NS),
            author.findtext("tei:surname", namespaces=NS)
        ])).strip()
        for author in root.findall(".//tei:sourceDesc//tei:author", NS)
    ]
    affiliations = [
        aff.text.strip() for aff in root.findall(".//tei:sourceDesc//tei:affiliation", NS)
        if aff is not None and aff.text
    ]
    publication_date = xpath_text(root, ".//tei:sourceDesc//tei:date")

    sections = []
    for div in root.findall(".//tei:body//tei:div", NS):
        head = xpath_text(div, "tei:head")
        paragraphs = [p.text.strip() for p in div.findall("tei:p", NS) if p.text]
        full_text = "\n".join(paragraphs)
        if full_text:
            sections.append((head or "Untitled Section", full_text))

    references = []
    for ref in root.findall(".//tei:listBibl//tei:biblStruct", NS):
        title = xpath_text(ref, ".//tei:title")
        authors = [p.text for p in ref.findall(".//tei:author//tei:surname", NS) if p.text]
        if title or authors:
            references.append({
                "title": title,
                "authors": authors
            })

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "affiliations": affiliations,
        "publication_date": publication_date,
        "sections": sections,
        "references": references
    }


def process_folder(folder_path, output_folder):
    """
    Batch process all PDFs in a folder via GROBID and save output text files.

    Args:
        folder_path (str): Path to input PDFs
        output_folder (str): Folder to store _output.txt files
    """
    os.makedirs(output_folder, exist_ok=True)
    pdf_paths = list(Path(folder_path).rglob("*.pdf"))
    print(f"Found {len(pdf_paths)} PDFs in {folder_path}")

    for pdf in pdf_paths:
        try:
            info = extract_grobid_sections(pdf)
            out_file = Path(output_folder) / f"{pdf.stem}_output.txt"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(f"# {info['title']}\n\n")
                f.write(f"## Abstract\n{info['abstract']}\n\n")
                f.write(f"## Authors\n{', '.join(info['authors'])}\n\n")
                f.write(f"## Affiliations\n{', '.join(info['affiliations'])}\n\n")
                for section_title, section_text in info["sections"]:
                    f.write(f"### {section_title}\n{section_text}\n\n")
                if info.get("references"):
                    f.write("## References\n")
                    for ref in info["references"]:
                        f.write(f"- {ref['title']} ({', '.join(ref['authors'])})\n")
        except Exception as e:
            print(f"Failed to process {pdf.name}: {e}")
