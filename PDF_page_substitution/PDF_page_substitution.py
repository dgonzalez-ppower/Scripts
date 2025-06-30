import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter

# --- GUI para seleccionar archivo y carpeta ---
root = tk.Tk()
root.withdraw()

# Selección del archivo PDF original
pdf_original_path = filedialog.askopenfilename(title="Selecciona el PDF original", filetypes=[("PDF files", "*.pdf")])
if not pdf_original_path:
    raise SystemExit("No se seleccionó ningún archivo PDF original.")

# Selección de la carpeta con los fragmentos
folder_path = filedialog.askdirectory(title="Selecciona la carpeta con los fragmentos S_*.pdf")
if not folder_path:
    raise SystemExit("No se seleccionó ninguna carpeta.")

# Leer PDF original
original_reader = PdfReader(pdf_original_path)
original_num_pages = len(original_reader.pages)

# Leer fragmentos y ordenarlos por página inicial
fragments = []
pattern = re.compile(r"S_(\d+)_(\d+)\.pdf")

for filename in os.listdir(folder_path):
    match = pattern.fullmatch(filename)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            messagebox.showerror("Error", f"Fragmento {filename} tiene página inicial mayor que final.")
            raise SystemExit(1)
        fragments.append((start, end, os.path.join(folder_path, filename)))

fragments.sort()  # ordenados por página inicial

# Validar solapamientos y rangos
used_pages = set()
for start, end, _ in fragments:
    if start < 1 or end > original_num_pages:
        messagebox.showerror("Error", f"Fragmento {start}-{end} fuera del rango del PDF original.")
        raise SystemExit(1)
    for p in range(start, end + 1):
        if p in used_pages:
            messagebox.showerror("Error", f"Solapamiento detectado en la página {p}.")
            raise SystemExit(1)
        used_pages.add(p)

# Crear ventana de progreso
progress_root = tk.Toplevel()
progress_root.title("Procesando PDF")
progress_label = tk.Label(progress_root, text="Procesando páginas...")
progress_label.pack(padx=20, pady=20)
progress_root.update()

# Crear nuevo PDF sustituyendo las páginas
writer = PdfWriter()

page_index = 1
while page_index <= original_num_pages:
    fragment = next(((s, e, f) for (s, e, f) in fragments if s == page_index), None)
    if fragment:
        frag_reader = PdfReader(fragment[2])
        frag_len = fragment[1] - fragment[0] + 1
        if len(frag_reader.pages) != frag_len:
            messagebox.showerror("Error", f"El fragmento {os.path.basename(fragment[2])} no tiene el número esperado de páginas.")
            raise SystemExit(1)
        for p in frag_reader.pages:
            writer.add_page(p)
        page_index = fragment[1] + 1
    else:
        writer.add_page(original_reader.pages[page_index - 1])
        page_index += 1
    progress_label.config(text=f"Procesando página {page_index - 1} de {original_num_pages}...")
    progress_root.update()

# Guardar archivo final
base, ext = os.path.splitext(pdf_original_path)
output_path = base + "_enhanced.pdf"
with open(output_path, "wb") as f:
    writer.write(f)

progress_root.destroy()
messagebox.showinfo("Éxito", f"PDF generado correctamente:\n{output_path}")
