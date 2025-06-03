import os
import requests
from lxml import etree
from pathlib import Path

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def extract_grobid_sections(pdf_path):
    with open(pdf_path, 'rb') as pdf_file:
        response = requests.post(GROBID_URL, files={'input': pdf_file})

    if response.status_code != 200:
        raise Exception(f"GROBID error: {response.status_code} for {pdf_path}")

    xml = etree.fromstring(response.content)

    title = xml.findtext('.//tei:titleStmt/tei:title', namespaces=NS) or "N/A"
    abstract_node = xml.find('.//tei:profileDesc/tei:abstract', namespaces=NS)
    abstract = " ".join(p.text for p in abstract_node.findall('.//tei:p', namespaces=NS)) if abstract_node is not None else "N/A"

    authors = []
    for pers in xml.findall('.//tei:sourceDesc//tei:analytic//tei:author', namespaces=NS):
        name = pers.find('.//tei:persName', namespaces=NS)
        if name is not None:
            full_name = " ".join(filter(None, [
                name.findtext('tei:forename', namespaces=NS),
                name.findtext('tei:surname', namespaces=NS)
            ]))
            authors.append(full_name)

    affiliations = [aff.text for aff in xml.findall('.//tei:affiliation/tei:orgName[@type="institution"]', namespaces=NS) if aff.text]

    pub_date = xml.findtext('.//tei:publicationStmt/tei:date', namespaces=NS) or "N/A"

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
        'sections': sections,
    }

def process_folder(input_folder, output_folder):
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    for pdf_file in input_path.glob("*.pdf"):
        print(f"Processing: {pdf_file.name}")
        try:
            result = extract_grobid_sections(str(pdf_file))
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
            print(f"✅ Saved: {output_file}")
        except Exception as e:
            print(f"Failed to process {pdf_file.name}: {e}")
