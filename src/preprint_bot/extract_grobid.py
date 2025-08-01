import os
import requests
from lxml import etree
from pathlib import Path
from urllib.parse import urlparse   # kept in case you add URL support later

# Optional spaCy sentence tokenizer
try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except ImportError:
    NLP = None

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def spacy_tokenize(text: str):
    """
    Tokenize *text* into sentences with spaCy if available, else split on blank lines.
    """
    if NLP:
        return [sent.text.strip() for sent in NLP(text).sents]
    return [s.strip() for s in text.split("\n\n") if s.strip()]


# Unified extractor
def extract_grobid_sections(src):
    """
    Extract structured metadata, sections and references from a PDF.
    """
    # 1. Load bytes 
    if isinstance(src, (bytes, bytearray)):
        pdf_bytes = src
    else:  # assume path-like
        with open(src, "rb") as fp:
            pdf_bytes = fp.read()

    # 2. Call GROBID 
    resp = requests.post(
        GROBID_URL,
        files={"input": ("file.pdf", pdf_bytes)},
        data={"consolidateHeader": "1"},
        timeout=30,
    )
    resp.raise_for_status()
    root = etree.fromstring(resp.content)

    # 3. Convenience 
    def _txt(el, path):
        found = el.find(path, NS)
        if found is not None:
            return " ".join(found.itertext()).strip()
        return ""

    # --- 4. Metadata --
    title = _txt(root, ".//tei:titleStmt/tei:title")
    abstract = _txt(root, ".//tei:profileDesc/tei:abstract")
    authors = [
        " ".join(
            filter(
                None,
                [
                    auth.findtext("tei:forename", namespaces=NS),
                    auth.findtext("tei:surname", namespaces=NS),
                ],
            )
        ).strip()
        for auth in root.findall(".//tei:sourceDesc//tei:author", NS)
    ]
    affiliations = [
        aff.text.strip()
        for aff in root.findall(".//tei:sourceDesc//tei:affiliation", NS)
        if aff is not None and aff.text
    ]
    publication_date = _txt(root, ".//tei:sourceDesc//tei:date")

    # 5. Sections 
    sections = []
    for div in root.findall(".//tei:body//tei:div", NS):
        head = _txt(div, "tei:head") or "Untitled Section"
        paras = [p.text.strip() for p in div.findall("tei:p", NS) if p.text]
        if paras:
            sections.append((head, "\n".join(paras)))

    # 6. References 
    references = []
    for ref in root.findall(".//tei:listBibl//tei:biblStruct", NS):
        ref_title = _txt(ref, ".//tei:title")
        ref_authors = [
            p.text
            for p in ref.findall(".//tei:author//tei:surname", NS)
            if p is not None and p.text
        ]
        if ref_title or ref_authors:
            references.append({"title": ref_title, "authors": ref_authors})

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "affiliations": affiliations,
        "publication_date": publication_date,
        "sections": sections,
        "references": references,
    }


# Back-compat alias: any existing imports keep working
extract_grobid_sections_from_bytes = extract_grobid_sections


#Batch processor
def process_folder(folder_path: str | Path, output_folder: str | Path):
    """
    Run GROBID extraction on every PDF inside *folder_path* and write “*_output.txt”
    files to *output_folder*.

    Skips files that error but continues processing the rest.
    """
    folder_path = Path(folder_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    pdf_paths = list(folder_path.rglob("*.pdf"))
    print(f"Found {len(pdf_paths)} PDFs in {folder_path}")

    for pdf in pdf_paths:
        try:
            info = extract_grobid_sections(pdf)        # ← unified call
            out_file = output_folder / f"{pdf.stem}_output.txt"

            with out_file.open("w", encoding="utf-8") as fh:
                fh.write(f"# {info['title']}\n\n")
                fh.write(f"## Abstract\n{info['abstract']}\n\n")
                fh.write(f"## Authors\n{', '.join(info['authors'])}\n\n")
                fh.write(f"## Affiliations\n{', '.join(info['affiliations'])}\n\n")

                for sec_title, sec_text in info["sections"]:
                    fh.write(f"### {sec_title}\n{sec_text}\n\n")

                if info["references"]:
                    fh.write("## References\n")
                    for ref in info["references"]:
                        fh.write(f"- {ref['title']} ({', '.join(ref['authors'])})\n")

        except Exception as exc:
            print(f"[WARN] Failed to process {pdf.name}: {exc}")
