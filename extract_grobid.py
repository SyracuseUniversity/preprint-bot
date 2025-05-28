import requests
from lxml import etree

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def extract_grobid_sections(pdf_path):
    with open(pdf_path, 'rb') as pdf_file:
        response = requests.post(GROBID_URL, files={'input': pdf_file})

    # checks if the GROBID server responded successfully 
    if response.status_code != 200:
        raise Exception(f"GROBID error: {response.status_code}")

    xml = etree.fromstring(response.content)

    # Title
    title = xml.findtext('.//tei:titleStmt/tei:title', namespaces=NS) or "N/A"


    # Abstract
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


    # References
    references = []
    for bibl in xml.findall('.//tei:listBibl//tei:biblStruct', namespaces=NS):
        ref_title = bibl.findtext('.//tei:title', namespaces=NS)
        
        # Get reference title and list of authors (full names) from each bibliographic entry
        ref_authors = []
        for pers in bibl.findall('.//tei:author', namespaces=NS):
            pers_name = pers.find('tei:persName', namespaces=NS)
            if pers_name is not None:
                forename = pers_name.findtext('tei:forename', namespaces=NS) or ''
                surname = pers_name.findtext('tei:surname', namespaces=NS) or ''
                full_name = " ".join(filter(None, [forename.strip(), surname.strip()]))
                if full_name:
                    ref_authors.append(full_name)

        references.append({
            'title': ref_title or "N/A",
            'authors': ref_authors if ref_authors else []
        })

    return {
        'title': title.strip(),
        'abstract': abstract.strip(),
        'authors': authors,
        'affiliations': affiliations,
        'pub_date': pub_date.strip(),
        'sections': sections,
        'references': references
    }



if __name__ == "__main__":
    # pdf file with path
    pdf_file = "testGrobid.pdf"
    result = extract_grobid_sections(pdf_file)

    # Write results to file
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(f"Title: {result['title']}\n")
        f.write(f"Abstract: {result['abstract']}\n\n")
        f.write(f"Authors: {', '.join(result['authors'])}\n")
        f.write(f"Affiliations: {', '.join(result['affiliations'])}\n")
        f.write(f"Publication Date: {result['pub_date']}\n\n")

        f.write("Sections:\n")
        for sec in result['sections']:
            f.write(f"\n- {sec['header']}:\n{sec['text']}\n")
            # f.write(f"\n- {sec['header']}\n{sec['text'][:1000]}:\n") to cap each section at 1000 characters

        f.write("\nReferences:\n")
        for ref in result['references']:
            # fixes hyphen issue
            fixed_author_line = ", ".join(ref['authors']).replace(", -", "-")
            f.write(f"- {ref['title']}\n  by {fixed_author_line}\n")
