import os
import json
from pathlib import Path

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <title>Document Index</title>
  <script src=\"https://unpkg.com/lunr/lunr.js\"></script>
  <style>
    body { font-family: Arial, sans-serif; padding: 2rem; background: #f9f9f9; }
    input[type='text'] { width: 100%; padding: 1rem; font-size: 1.2rem; margin-bottom: 2rem; }
    .result { background: white; margin-bottom: 1rem; padding: 1rem; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .filepath { color: #888; font-size: 0.9rem; }
    ul { list-style-type: none; padding-left: 1rem; }
    li { margin: 0.2rem 0; }
    .folder-tree { margin-top: 3rem; }
  
    .collapsible > span::before {
      content: "▶";
      display: inline-block;
      margin-right: 0.5em;
      transform: rotate(0deg);
      transition: transform 0.2s;
    }

    .collapsible:not(.collapsed) > span::before {
      transform: rotate(90deg);
    }
  
    .collapsed > ul {
      display: none;
    }
  
  </style>
</head>
<body>
  <h1>Document Index</h1>
  <input type=\"text\" id=\"searchBox\" placeholder=\"Search documents...\">
  <div id=\"results\"></div>
  <div id=\"folderTree\" class=\"folder-tree\">__FOLDER_TREE__</div>

  <script>
    const documents = __DATA__;

    const idx = lunr(function () {
      this.ref('id');
      this.field('filename');
      this.field('text_content');

      documents.forEach(function (doc, idx) {
        doc.id = idx;
        this.add(doc);
      }, this);
    });

    const searchBox = document.getElementById('searchBox');
    const resultsDiv = document.getElementById('results');
    const folderTree = document.getElementById('folderTree');

    searchBox.addEventListener('input', function () {
      const query = this.value;
      const results = idx.search(query);

      resultsDiv.innerHTML = '';

      if (query.trim() !== '') {
        folderTree.style.display = 'none';
        results.forEach(r => {
          const doc = documents[r.ref];
          const div = document.createElement('div');
          div.className = 'result';
          div.innerHTML = `<strong>${doc.filename}</strong><div class='filepath'><a href=\"${doc.filepath}\" target=\"_blank\">${doc.filepath}</a></div>`;
          resultsDiv.appendChild(div);
        });
      } else {
        folderTree.style.display = 'block';
      }
    });
    
    document.addEventListener('DOMContentLoaded', () => {
      // Colapsar todas las carpetas por defecto
      document.querySelectorAll('.collapsible').forEach(li => li.classList.add('collapsed'));

      // Agregar comportamiento de plegado/expansión
      document.querySelectorAll('.collapser').forEach(span => {
        span.addEventListener('click', () => {
          const li = span.parentElement;
          li.classList.toggle('collapsed');
        });
      });
    });

        
  </script>
</body>
</html>
"""

def build_file_tree_html(data):
    from collections import defaultdict

    tree = lambda: defaultdict(tree)
    file_tree = tree()

    for doc in data:
        parts = Path(doc['filepath']).parts
        ref = file_tree
        for part in parts[:-1]:
            ref = ref[part]
        ref[parts[-1]] = doc['filepath']

    def render_node(node):
        html = '<ul>'
        for name, value in sorted(node.items()):
            if isinstance(value, str):
                html += f'<li><a href="{value}" target="_blank">{name}</a></li>'
            else:
                # Aquí insertamos el onclick directamente en el <span>
                html += f'<li class="collapsible collapsed"><span class="collapser">{name}</span>{render_node(value)}</li>'
        html += '</ul>'
        return html

    return render_node(file_tree)


def generate_index_html(json_folder, output_html, source_folder):
    json_folder = Path(json_folder)
    base_folder = Path(source_folder).resolve()
    root_relative_prefix = os.path.relpath(source_folder, Path(output_html).parent).replace("\\", "/")
    data = []

    for file in json_folder.glob("*.json"):
        with open(file, encoding='utf-8') as f:
            content = json.load(f)
            relative_path = Path(content["filepath"])
            data.append({
                "filename": content["filename"],
                "filepath": f"{root_relative_prefix}/{str(relative_path).replace('\\', '/')}",
                "text_content": content.get("text_content", "")
            })

    folder_tree_html = build_file_tree_html(data)
    html_content = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    html_content = html_content.replace("__FOLDER_TREE__", folder_tree_html)

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ HTML index generated at: {output_html}")

def index_documents(source_folder, output_folder):
    import fitz
    import docx
    import datetime
    from tqdm import tqdm

    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt']

    def extract_text_from_pdf(filepath):
        try:
            doc = fitz.open(filepath)
            reported_pages = doc.page_count
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

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Index and render searchable HTML index from folder")
    parser.add_argument("--source_folder", required=True, help="Path to the folder to index")
    args = parser.parse_args()

    source_path = Path(args.source_folder).resolve()
    index_folder = source_path.parent / f"index_{source_path.name}"
    index_folder.mkdir(exist_ok=True)
    json_folder = index_folder / "index_data"
    output_html = index_folder / "index.html"

    index_documents(source_path, index_folder)
    generate_index_html(json_folder, output_html, source_path)
