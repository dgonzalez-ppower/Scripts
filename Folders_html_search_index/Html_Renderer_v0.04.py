import os
import json
from pathlib import Path

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <script src="https://unpkg.com/lunr/lunr.js"></script>
  <title>Document Index</title>
  <style>
      body {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #fcfcfc;
        margin: 0;
        padding: 2rem;
        color: #2c2c2c;
      }

      .main-container {
        max-width: 900px;
        margin: 2rem auto;
        padding: 2rem 2rem 4rem 2rem;
        background: #fff;
        border-radius: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        min-height: 80vh;
      }

      .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 700px;
        margin: 0 auto 2rem auto;
        position: sticky;
        top: 0;
        background: #fcfcfc;
        z-index: 10;
        padding-top: 1.5rem;
        /* Opcional: sombra sutil para distinguir del fondo al hacer scroll */
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
      }

        
      }

      .header-container h1 {
        margin: 0;
        font-size: 2.5rem;
        flex: 1;
        text-align: center;
        letter-spacing: 0.05em;
        color: #1a1a1a;
      }

      .logo {
        height: 60px;
        width: auto;
        margin-left: 1rem;
        flex-shrink: 0;
      }

      input[type='text'] {
        display: block;
        margin: 0 auto 2.5rem auto;
        width: 100%;
        max-width: 600px;
        padding: 1rem 1.5rem;
        font-size: 1.2rem;
        border: 1px solid #ccc;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        position: sticky;
        top: 6.5rem;  /* Ajusta este valor si la cabecera ocupa más/menos altura */
        z-index: 15;
        background: #fff;
                
      }

      .result {
        background: #ffffff;
        margin: 1.5rem auto;
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        max-width: 700px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
      }

      .filepath {
        margin-top: 0.5rem;
        color: #555;
        font-size: 0.9rem;
        word-break: break-all;
      }

      ul {
        list-style-type: none;
        padding-left: 1.2rem;
        margin: 0;
      }

      li {
        margin: 0.4rem 0;
      }

      .folder-tree {
        margin-top: 3rem;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
      }

      .collapsible > span {
        cursor: pointer;
        font-weight: bold;
        user-select: none;
        display: inline-block;
      }

      .collapsible > span::before {
        content: "▶";
        display: inline-block;
        margin-right: 0.5em;
        transform: rotate(0deg);
        transition: transform 0.2s;
        color: #444;
      }

      .collapsible:not(.collapsed) > span::before {
        transform: rotate(90deg);
      }

      .collapsed > ul {
        display: none;
      }

      a {
        color: #005f73;
        text-decoration: none;
      }

      a:hover {
        text-decoration: underline;
      }
  </style>


</head>
<body>
  <div class="main-container">
    <div class="header-container">
      <h1>Document Index</h1>
      <img class="logo" src="logo_proinelca.png" alt="Logo Proinelca México">
    </div>
    <input type="text" id="searchBox" placeholder="Search documents...">
    <div id="results"></div>
    <div id="folderTree" class="folder-tree">__FOLDER_TREE__</div>
  </div>
    
  <script>
    document.addEventListener('DOMContentLoaded', () => {
      // Árbol de carpetas colapsable
      document.querySelectorAll('.collapsible').forEach(li => li.classList.add('collapsed'));
      document.querySelectorAll('.collapser').forEach(span => {
        span.addEventListener('click', () => {
          const li = span.parentElement;
          li.classList.toggle('collapsed');
        });
      });
      // Expande la raíz
      const rootLi = document.querySelector('.folder-tree > ul > li');
      if (rootLi) rootLi.classList.remove('collapsed');
    });

    // Búsqueda en Lunr
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
      const query = this.value.trim();
      resultsDiv.innerHTML = '';

      if (query !== '') {
        folderTree.style.display = 'none';

        let normalizedQuery = query
          .replace(/[\.\+\?\$\{\}\(\)\[\]\\\|]/g, '\\$&') // Escapa todo menos *
          .replace(/\*/g, '*');

        let results;
        if (query.includes('*') || query.includes('?')) {
          results = idx.search(`filename:${normalizedQuery} text_content:${normalizedQuery}`);
        } else {
          results = idx.search(`${normalizedQuery}`);
        }

        if (results.length === 0) {
          resultsDiv.innerHTML = '<div class="result"><strong>No matches found</strong></div>';
          return;
        }

        results.forEach(r => {
          const doc = documents[r.ref];
          const lowerQuery = query.toLowerCase();

          // 1. Coincidencias en texto/páginas (solo si existe page_texts)
          let hits = 0;
          let pagesWithHits = [];

          if (doc.page_texts) {
            doc.page_texts.forEach(p => {
              const matchCount = (p.text.toLowerCase().match(new RegExp(lowerQuery, 'g')) || []).length;
              if (matchCount > 0) {
                hits += matchCount;
                pagesWithHits.push(p.page);
              }
            });
          }

          // 2. Coincidencia por nombre de archivo
          let filenameMatch = false;
          // Aplica lógica de wildcard si hay * o ?, si no, literal
          if (query.includes('*') || query.includes('?')) {
            // Convierte el wildcard a regex JS
            let pattern = query.replace(/[-\/\\^$+?.()|[\]{}]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.');
            filenameMatch = new RegExp('^' + pattern + '$', 'i').test(doc.filename);
          } else {
            filenameMatch = doc.filename.toLowerCase().includes(lowerQuery);
          }

          // Mostrar solo si: hay hits en texto, hay match en nombre de archivo, o (si quieres) match en filepath
          if (hits > 0 || filenameMatch) {
            const div = document.createElement('div');
            div.className = 'result';
            div.innerHTML = `
              <strong>${doc.filename}</strong>
              <div class='filepath'>
                <a href="${doc.filepath}" target="_blank">${doc.filepath}</a><br>
                <small>🔎 ${hits} match(es) on page(s): ${pagesWithHits.join(', ')}</small>
              </div>
            `;
            resultsDiv.appendChild(div);
          }
        });

        // Si no hay ningún resultado visible tras el filtro, muestra mensaje "No matches found"
        if (resultsDiv.innerHTML.trim() === '') {
          resultsDiv.innerHTML = '<div class="result"><strong>No matches found</strong></div>';
        }

      } else {
        folderTree.style.display = 'block';
      }
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
                "text_content": content.get("text_content", ""),
                "page_texts": content.get("page_texts", []),
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

    def extract_text_by_page(filepath):
        import fitz
        doc = fitz.open(filepath)
        page_texts = [{"page": i+1, "text": doc[i].get_text("text")} for i in range(len(doc))]
        doc.close()
        return page_texts

    def extract_text_from_pdf(filepath):
        try:
            doc = fitz.open(filepath)
            reported_pages = doc.page_count
            text = ""
            page_texts = []
            page_count = 0
            for i, page in enumerate(doc, start=1):
                page_text = page.get_text("text")
                text += page_text + "\n"
                page_texts.append({"page": i, "text": page_text})
                page_count += 1
            return text.strip(), page_count, reported_pages, page_texts

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
        text_content, page_count, reported_pages, page_texts = extract_text(filepath)
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
            "page_texts": extract_text_by_page(filepath),
            "metadata": metadata,      
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
