import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter

def natural_key(string_):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', string_)]

def build_tree(folder_path):
    node = {
        'folder_path': folder_path,
        'folder_name': os.path.basename(folder_path),
        'pdf_files': [],
        'children': []
    }
    cover_pdfs = []
    other_pdfs = []

    for item in sorted(os.listdir(folder_path), key=natural_key):
        full_path = os.path.join(folder_path, item)
        if os.path.isfile(full_path) and item.lower().endswith('.pdf'):
            if "cover" in item.lower():
                cover_pdfs.append(full_path)
            else:
                other_pdfs.append(full_path)
        elif os.path.isdir(full_path):
            node['children'].append(build_tree(full_path))

    node['pdf_files'] = cover_pdfs + other_pdfs
    return node

def merge_tree_has_pdf(node):
    return bool(node['pdf_files']) or any(merge_tree_has_pdf(child) for child in node['children'])

def merge_tree(node, writer, current_offset, parent_bookmark, pdf_reader_cache):
    has_pdf = bool(node['pdf_files']) or any(merge_tree_has_pdf(child) for child in node['children'])
    bookmark = None
    first_pdf_offset = current_offset
    child_offsets = []

    if has_pdf:
        bookmark = writer.add_outline_item(node['folder_name'], first_pdf_offset, parent=parent_bookmark)

    # Marcar si solo hay un único PDF
    multiple_pdfs = len(node['pdf_files']) > 1

    for i, pdf_path in enumerate(node['pdf_files']):
        if pdf_path in pdf_reader_cache:
            reader = pdf_reader_cache[pdf_path]
        else:
            try:
                reader = PdfReader(pdf_path)
                pdf_reader_cache[pdf_path] = reader
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el PDF '{pdf_path}': {e}")
                continue

        num_pages = len(reader.pages)
        if num_pages == 0:
            continue

        for page in reader.pages:
            writer.add_page(page)

        if multiple_pdfs:
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            writer.add_outline_item(pdf_name, current_offset, parent=bookmark)

        if i == 0:
            first_pdf_offset = current_offset

        current_offset += num_pages

    for child in sorted(node['children'], key=lambda x: natural_key(x['folder_name'])):
        child_offset_before = current_offset
        current_offset = merge_tree(child, writer, current_offset, bookmark, pdf_reader_cache)
        child_offsets.append(child_offset_before)

    # Si esta carpeta no tiene PDFs, pero sí hijos con PDFs, corregir el marcador
    if not node['pdf_files'] and child_offsets and bookmark is not None:
        bookmark.page_number = child_offsets[0]

    return current_offset

def assemble_pdf(source_folder, destination_folder):
    writer = PdfWriter()
    current_offset = 0
    pdf_reader_cache = {}
    tree = build_tree(source_folder)
    merge_tree(tree, writer, current_offset, parent_bookmark=None, pdf_reader_cache=pdf_reader_cache)

    folder_name = os.path.basename(os.path.normpath(source_folder))
    output_filename = f"{folder_name}_ensamblado.pdf"
    output_path = os.path.join(destination_folder, output_filename)

    try:
        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        messagebox.showinfo("Éxito", f"PDF ensamblado guardado en:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar el PDF ensamblado:\n{e}")

def main():
    root = tk.Tk()
    root.title("Ensamblador PDF (Prioridad COVER + Bookmarks Inteligentes)")
    root.geometry("600x220")

    source_var = tk.StringVar()
    dest_var = tk.StringVar()

    def browse_source():
        folder = filedialog.askdirectory(title="Selecciona la carpeta de origen")
        if folder:
            source_var.set(folder)

    def browse_dest():
        folder = filedialog.askdirectory(title="Selecciona la carpeta de destino")
        if folder:
            dest_var.set(folder)

    def run_assemble():
        source = source_var.get()
        dest = dest_var.get()
        if not source or not dest:
            messagebox.showerror("Error", "Debes seleccionar la carpeta de origen y la de destino.")
            return
        assemble_pdf(source, dest)

    tk.Label(root, text="Carpeta de Origen:").pack(pady=5)
    tk.Entry(root, textvariable=source_var, width=80).pack(pady=5)
    tk.Button(root, text="Seleccionar Carpeta de Origen", command=browse_source).pack(pady=5)

    tk.Label(root, text="Carpeta de Destino:").pack(pady=5)
    tk.Entry(root, textvariable=dest_var, width=80).pack(pady=5)
    tk.Button(root, text="Seleccionar Carpeta de Destino", command=browse_dest).pack(pady=5)

    tk.Button(root, text="Ejecutar Ensamblado", command=run_assemble, bg="green", fg="white").pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
