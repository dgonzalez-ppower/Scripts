import os
import fitz  # PyMuPDF
import docx
import json
import datetime
from pathlib import Path
from tqdm import tqdm

SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt']

def extract_text_from_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        reported_pages = doc.page_count  # más robusto que len(doc)
        text = ""
        page_count = 0
        for page in doc:
            text += page.get_text("text") + "\n"
            page_count += 1
        return text.strip(), page_count, reported_pages
    except Exception as e:
        raise RuntimeError(f"Error reading PDF: {filepath} - {e}")

def extract_text_from_docx(filepath):
    try:
        doc = docx.Document(filepath)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text.strip(), None
    except Exception as e:
        raise RuntimeError(f"Error reading DOCX: {filepath} - {e}")


def extract_text_from_txt(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip(), None
    except Exception as e:
        raise RuntimeError(f"Error reading TXT: {filepath} - {e}")


def extract_text(filepath):
    ext = filepath.suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(filepath)
    elif ext == '.docx':
        text, _ = extract_text_from_docx(filepath)
        return text, None, None
    elif ext == '.txt':
        text, _ = extract_text_from_txt(filepath)
        return text, None, None
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def generate_json_entry(filepath, base_folder):
    text_content, page_count, reported_pages = extract_text(filepath)
    stat = filepath.stat()
    metadata = {
        "modification_date": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "size_kb": round(stat.st_size / 1024, 2),
        "pages_iterated": page_count,
        "pages_reported": reported_pages,
        "page_mismatch": page_count != reported_pages
    }

    return {
        "filename": filepath.name,
        "filepath": str(filepath.relative_to(base_folder)).replace("\\", "/"),
        "text_content": text_content,
        "metadata": metadata
    }


def index_documents(source_folder, output_folder):
    source = Path(source_folder)
    output_data = Path(output_folder) / "index_data"
    output_data.mkdir(parents=True, exist_ok=True)

    error_log = open(output_data / "errores.log", "w", encoding="utf-8")
    ignored_log = open(output_data / "ignorados.log", "w", encoding="utf-8")

    all_files = [Path(root) / file for root, _, files in os.walk(source) for file in files]
    doc_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    ignored_files = [f for f in all_files if f.suffix.lower() not in SUPPORTED_EXTENSIONS]

    base_folder = source.resolve()

    for ignored in ignored_files:
        ignored_log.write(str(ignored.resolve()) + "\n")

    print(f"\n🔍 Documentos encontrados para indexar: {len(doc_files)}")
    print(f"🚫 Archivos ignorados por extensión: {len(ignored_files)}\n")

    for filepath in tqdm(doc_files, desc="Indexando documentos"):
        try:
            json_data = generate_json_entry(filepath, base_folder)
            json_name = filepath.stem + ".json"
            json_path = output_data / json_name
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error_log.write(f"{filepath.resolve()} - {e}\n")

    error_log.close()
    ignored_log.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Index documents and extract content to JSON")
    parser.add_argument("--source", required=True, help="Path to the folder with documents")
    parser.add_argument("--output", required=True, help="Path to output folder for JSON data")
    args = parser.parse_args()

    index_documents(args.source, args.output)
    print("\n✅ Indexación completa. Revisa errores.log e ignorados.log si es necesario.")