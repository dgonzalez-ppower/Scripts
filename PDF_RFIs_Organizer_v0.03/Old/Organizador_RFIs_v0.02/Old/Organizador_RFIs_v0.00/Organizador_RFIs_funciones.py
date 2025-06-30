import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import datetime
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter

# --- Funciones de procesamiento ---
def process_rfis(pdf_folder, index_excel):
    print(f"[INFO] Procesando carpeta: {pdf_folder}")
    print(f"[INFO] Índice: {index_excel}")

    df_index = pd.read_excel(index_excel)

    not_in_excel = []
    not_in_folder = []

    for filename in os.listdir(pdf_folder):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_folder, filename)
        print(f"\n[PDF] Procesando: {filename}")
        try:
            reader = PdfReader(pdf_path)
            bookmarks = extract_bookmarks(reader)

            if is_undivided(bookmarks):
                move_whole_file(filename, pdf_path, df_index)
            else:
                split_files = split_pdf_by_bookmarks(filename, pdf_path, bookmarks)
                move_split_files(filename, split_files, df_index)

        except Exception as e:
            print(f"[ERROR] Falló el procesamiento de {filename}: {e}")

    generate_log(pdf_folder, df_index, not_in_excel, not_in_folder)


def extract_bookmarks(reader):
    bookmarks = []

    def parse_outlines(outlines, level=0):
        for item in outlines:
            if isinstance(item, list):
                parse_outlines(item, level + 1)
            else:
                try:
                    # Detectamos si tiene título (como los bookmarks reales)
                    if hasattr(item, "title"):
                        page_number = reader.get_destination_page_number(item)
                        bookmarks.append({
                            "title": item.title.strip(),
                            "page": page_number,
                            "level": level
                        })
                except Exception as e:
                    print(f"[WARN] No se pudo obtener página para bookmark {item}: {e}")

    parse_outlines(reader.outline)  # Correcto para PyPDF2 >= 3.0

    # Solo de primer nivel
    bookmarks = [b for b in bookmarks if b["level"] == 0]
    return bookmarks

      

def is_undivided(bookmarks):
    if not bookmarks:
        return True

    # Contamos cuántos hay sin incluir "Cover"
    others = [b for b in bookmarks if b["title"].strip().lower() != "cover"]

    # Si hay solo uno adicional a "Cover", NO se divide
    return len(others) <= 1


def split_pdf_by_bookmarks(original_name, pdf_path, bookmarks):
    reader = PdfReader(pdf_path)
    split_files = []

    # Página del cover
    cover_page = reader.pages[0]

    # Filtramos bookmarks útiles (ignoramos Cover)
    main_bms = [b for b in bookmarks if b["title"].strip().lower() != "cover"]

    for i, bm in enumerate(main_bms):
        start_page = bm["page"]
        end_page = main_bms[i + 1]["page"] if i + 1 < len(main_bms) else len(reader.pages)

        writer = PdfWriter()
        writer.add_page(cover_page)  # Agrega la portada

        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])

        # Sacar x.y.z desde el título del bookmark
        match = re.search(r"/\s*(\d+\.\d+(?:\.\d+)?)", bm["title"])
        suffix = match.group(1) if match else f"parte_{i+1}"

        output_filename = f"{os.path.splitext(original_name)[0]}_{suffix}.pdf"
        output_path = os.path.join(os.path.dirname(pdf_path), output_filename)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        split_files.append(output_path)
        print(f"[OK] Archivo generado: {output_filename}")

    return split_files


def move_whole_file(filename, filepath, df_index, excel_dir):

    base_name = os.path.splitext(os.path.basename(filename))[0]
    match = df_index[df_index['Nombre RFI'].astype(str).str.strip() == base_name]

    if match.empty:
        print(f"[WARN] No se encontró {base_name} en columna 'Nombre RFI' del índice.")
        return

    dest_path = match.iloc[0]['Enlace Destino']
    
    # Si la ruta termina en .pdf, quítalo — queremos solo la carpeta
    if dest_path.lower().endswith(".pdf"):
        dest_path = os.path.dirname(dest_path)
    
    if not os.path.isabs(dest_path):
        dest_path = os.path.normpath(os.path.join(excel_dir, dest_path))
    
    new_filename = match.iloc[0]['Nombre PDF Destino']
    new_filename = os.path.splitext(new_filename)[0]  # le quitamos .pdf si lo trae
    dest_file_path = os.path.join(dest_path, f"{new_filename}.pdf")

    os.makedirs(dest_path, exist_ok=True)
    shutil.copy2(filepath, dest_file_path)
    print(f"[OK] Archivo copiado a: {dest_file_path}")




def move_split_files(original_name, split_files, df_index, excel_dir):
    base_original = os.path.splitext(original_name)[0]

    for split_path in split_files:
        split_name = os.path.basename(split_path)
        suffix_match = re.search(r'_(\d+\.\d+(?:\.\d+)?)\.pdf$', split_name)
        if not suffix_match:
            print(f"[WARN] No se encontró sufijo en: {split_name}")
            continue

        suffix = suffix_match.group(1)

        # Buscar filas que coincidan con el nombre original
        matches = df_index[df_index['Nombre RFI'].astype(str).str.strip() == base_original]

        # Limpiar sufijos (quitar la barra final del Excel)
        matches = matches.copy()
        matches['Subindice'] = matches['Subindice'].astype(str).str.strip().str.replace("/", "", regex=False)


        # Buscar coincidencia con el sufijo
        final_match = matches[matches['Subindice'] == suffix]

        if final_match.empty:
            print(f"[WARN] No se encontró match para {split_name} con subíndice {suffix}")
            continue

        row = final_match.iloc[0]
        dest_folder = row['Enlace Destino']
        
        if dest_folder.lower().endswith(".pdf"):
            dest_folder = os.path.dirname(dest_folder)
        
        if not os.path.isabs(dest_folder):
            dest_folder = os.path.normpath(os.path.join(excel_dir, dest_folder))

        
        new_name = os.path.splitext(row['Nombre PDF Destino'])[0]
        dest_path = os.path.join(dest_folder, f"{new_name}.pdf")

        print(f"[DEBUG] Moviendo a: {dest_path}")
        os.makedirs(dest_folder, exist_ok=True)

        # Limpiar bookmarks y renombrar el archivo
        reader = PdfReader(split_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.add_outline_item(new_name, 0)  # Añadir nuevo bookmark con el nombre limpio

        with open(dest_path, "wb") as out_file:
            writer.write(out_file)

        print(f"[OK] Archivo movido: {dest_path}")



def generate_log(pdf_folder, df_index, not_in_excel, not_in_folder):
    log_path = os.path.join(pdf_folder, "log_resultado.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=== Archivos PDF sin entrada en Excel ===\n")
        for item in not_in_excel:
            f.write(f"{item}\n")
        f.write("\n=== Entradas del Excel sin archivo PDF correspondiente ===\n")
        for item in not_in_folder:
            f.write(f"{item}\n")
    print(f"[INFO] Log generado en: {log_path}")




