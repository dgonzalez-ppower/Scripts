import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PyPDF2 import PdfReader

def sanitize(name):
    """Elimina caracteres no válidos en nombres de carpetas (Windows)."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def print_outline(outline, indent=0):
    """Función de depuración para imprimir la estructura de bookmarks."""
    if isinstance(outline, list):
        for item in outline:
            print_outline(item, indent)
    else:
        try:
            print(" " * indent + f"Title: {outline.title}, Page: {outline.page}")
        except AttributeError:
            print(" " * indent + f"Non-standard bookmark object: {outline}")

def flatten_bookmarks(bookmarks, pdf_reader, depth=0, parent_titles=None):
    """
    Recorre recursivamente la estructura de bookmarks (que puede incluir contenedores
    sin atributo 'title') y devuelve un listado de nodos con la información:
      - title: título del bookmark (o "Untitled" si está vacío)
      - page: número de página donde inicia el bookmark
      - depth: nivel de profundidad (0 = raíz)
      - parent_titles: lista de nombres de los ancestros (para construir la ruta de carpetas)
    """
    if parent_titles is None:
        parent_titles = []
    nodes = []
    i = 0
    while i < len(bookmarks):
        item = bookmarks[i]
        if not hasattr(item, "title"):
            # Es un contenedor (ej. una lista); se recorre sin cambiar el depth ni los parent_titles
            nodes.extend(flatten_bookmarks(item, pdf_reader, depth, parent_titles))
            i += 1
        else:
            try:
                title = item.title.strip() if item.title.strip() else "Untitled"
            except Exception as e:
                title = "Untitled"
            try:
                page = pdf_reader.get_destination_page_number(item)
            except Exception as e:
                print(f"Error obteniendo la página para el bookmark '{title}': {e}")
                i += 1
                continue
            current_node = {
                'title': title,
                'page': page,
                'depth': depth,
                'parent_titles': list(parent_titles)
            }
            nodes.append(current_node)
            # Si el siguiente elemento es una lista, son los hijos de este bookmark
            if i + 1 < len(bookmarks) and isinstance(bookmarks[i+1], list):
                children = flatten_bookmarks(bookmarks[i+1], pdf_reader, depth + 1, parent_titles + [title])
                nodes.extend(children)
                i += 2  # Se salta el contenedor de hijos ya procesado
            else:
                i += 1
    return nodes

def extract_pages_pymupdf(pdf_path, start_page, end_page, output_folder, bookmark_name):
    """
    Usa PyMuPDF para extraer las páginas desde start_page hasta end_page-1 (inclusive)
    del PDF original y guarda el resultado en output_folder con el nombre bookmark_name.pdf.
    """
    src_doc = fitz.open(pdf_path)
    new_doc = fitz.open()
    new_doc.insert_pdf(src_doc, from_page=start_page, to_page=end_page - 1)
    output_file = os.path.join(output_folder, f"{sanitize(bookmark_name)}.pdf")
    new_doc.save(output_file)
    new_doc.close()
    src_doc.close()
    print(f"Extracted pages {start_page} to {end_page - 1} for '{bookmark_name}' into {output_file}")

def process_pdf(pdf_path):
    print("Processing PDF file:", pdf_path)
    base_dir = os.path.dirname(pdf_path)
    try:
        reader = PdfReader(pdf_path)
        outlines = reader.outline  # Propiedad de PyPDF2 v3.x
        print("Successfully read the bookmark outline.")
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer los bookmarks del PDF: {e}")
        print(f"Error reading PDF bookmarks: {e}")
        return

    if not outlines:
        messagebox.showinfo("Info", "No se encontraron bookmarks en el PDF.")
        print("No bookmarks found.")
        return

    print("---- Debug: Outline Structure ----")
    print_outline(outlines)
    print("---- End Debug ----")

    total_pages = len(reader.pages)
    flattened = flatten_bookmarks(outlines, reader)
    print("Flattened bookmarks:")
    for node in flattened:
        print(node)

    # Recorrer el listado aplanado y extraer cada fragmento
    for i, node in enumerate(flattened):
        start_page = node['page']
        # El end_page es la página del siguiente nodo en el listado o total_pages si es el último
        if i + 1 < len(flattened):
            end_page = flattened[i+1]['page']
        else:
            end_page = total_pages
        if end_page <= start_page:
            end_page = total_pages
        # Crear la ruta de carpetas a partir de la jerarquía
        folder_path = os.path.join(base_dir, *[sanitize(x) for x in node['parent_titles']], sanitize(node['title']))
        os.makedirs(folder_path, exist_ok=True)
        print(f"For bookmark '{node['title']}', extracting pages {start_page} to {end_page - 1} into folder {folder_path}")
        extract_pages_pymupdf(pdf_path, start_page, end_page, folder_path, node['title'])

    messagebox.showinfo("Success", "¡Estructura de carpetas y PDFs extraídos creados correctamente!")
    print("Processing completed.")

def select_pdf():
    file_path = filedialog.askopenfilename(
        title="Select a PDF file", 
        filetypes=[("PDF Files", "*.pdf")]
    )
    if file_path:
        process_pdf(file_path)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("PDF Bookmark Splitter (Flattened DFS)")
    root.geometry("300x100")
    btn = tk.Button(root, text="Select PDF File", command=select_pdf)
    btn.pack(expand=True)
    root.mainloop()
