import requests

# === CONFIG ===
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
PDF_PATH = "main\my_papers\paper 1.pdf"  # replace with your test PDF path

# === SEND PDF TO GROBID ===
def test_grobid(pdf_path):
    try:
        with open(pdf_path, 'rb') as pdf_file:
            print(f"Sending '{pdf_path}' to GROBID...")
            response = requests.post(GROBID_URL, files={'input': pdf_file})
        
        if response.status_code == 200:
            print("✅ Success! TEI XML received.\n")
            print(response.text[:1000])  # Print first 1000 characters
        else:
            print(f"❌ Error: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Exception: {e}")

# === RUN ===
if __name__ == "__main__":
    test_grobid(PDF_PATH)
