import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import datetime
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import Destination

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
    def _recurse(bookmark_list, level=0):
        bookmarks = []
        for b in bookmark_list:
            if isinstance(b, list):
                bookmarks.extend(_recurse(b, level + 1))
            else:
                try:
                    title = b.title if hasattr(b, 'title') else str(b)
                    page = reader.get_destination_page_number(b)
                    bookmarks.append({'title': title, 'page': page, 'level': level})
                except Exception as e:
                    print(f"[WARN] No se pudo leer bookmark: {b} -> {e}")
        return bookmarks
    try:
        return _recurse(reader.outline)
    except Exception as e:
        print(f"[WARN] No se pudo extraer outline: {e}")
        return []
      
def is_undivided(bookmarks):
    if not bookmarks:
        return True

    # Contamos cuántos hay sin incluir "Cover"
    others = [b for b in bookmarks if b["title"].strip().lower() != "cover"]

    # Si hay solo uno adicional a "Cover", NO se divide
    return len(others) <= 1

def split_pdf_by_bookmarks(original_name, pdf_path, bookmarks, df_index, excel_dir):
    reader = PdfReader(pdf_path)
    split_files = []

    top_bms = [b for b in bookmarks if b["level"] == 0 and str(b["title"]).strip().lower() != "cover"]
    include_cover = len(top_bms) > 1
    cover_page = reader.pages[0] if include_cover else None

    for i, bm in enumerate(top_bms):
        title = bm["title"]
        start_page = bm["page"]
        end_page = top_bms[i + 1]["page"] if i + 1 < len(top_bms) else len(reader.pages)

        # Determinar sufijo desde el título del bookmark
        match = re.search(r"/\s*(\d+\.\d+(?:\.\d+)?)(?:\s*/\s*([A-Z0-9\-]+))?", title)
        if not match:
            print(f"[WARN] Título de bookmark no coincide con patrón esperado: {title}")
            continue

        sub_b = match.group(1)
        sub_c = match.group(2) if match.lastindex == 2 else None

        # Buscar nombre PDF destino en Excel
        matches = df_index[df_index["Nombre RFI"].astype(str).str.strip() == os.path.splitext(original_name)[0]].copy()
        matches["Subindice"] = matches["Subindice"].astype(str).str.strip().str.replace("/", "", regex=False)
        matches["Subindice_2"] = matches["Subindice_2"].astype(str).str.strip()

        if sub_c:
            matched_row = matches[
                (matches["Subindice"] == sub_b) &
                (matches["Subindice_2"].str.contains(sub_c, na=False))
            ]
        else:
            matched_row = matches[matches["Subindice"] == sub_b]

        if matched_row.empty:
            print(f"[WARN] No se encontró destino en Excel para subíndice: {sub_b} {sub_c or ''}")
            continue

        row = matched_row.iloc[0]
        final_name = row["Nombre PDF Destino"]
        dest_dir = row["Enlace Destino"]
        # Si el destino incluye el nombre del archivo PDF, quitarlo
        if isinstance(dest_dir, str) and dest_dir.lower().endswith(".pdf"):
            dest_dir = os.path.dirname(dest_dir)

        # Convertir a ruta absoluta y normalizar
        full_dest_dir = os.path.normpath(os.path.join(excel_dir, dest_dir))
        os.makedirs(full_dest_dir, exist_ok=True)

        final_name = final_name.strip()
        if final_name.lower().endswith(".pdf.pdf"):
            final_name = final_name[:-4]
        elif not final_name.lower().endswith(".pdf"):
            final_name += ".pdf"
        dest_filename = final_name
        output_path = os.path.join(full_dest_dir, dest_filename)

        writer = PdfWriter()
        page_offset = 1 if include_cover else 0

        if include_cover:
            writer.add_page(cover_page)

        for p in range(start_page, end_page):
            writer.add_page(reader.pages[p])

        # Añadir bookmark raíz
        root_bm = writer.add_outline_item(final_name, 0)

        # Insertar sub-bookmarks
        base_level = bm["level"]
        for b in bookmarks:
            if b["page"] >= start_page and b["page"] < end_page and b["level"] > base_level:
                try:
                    rel_page = b["page"] - start_page + page_offset
                    writer.add_outline_item(b["title"], rel_page, parent=root_bm)
                except Exception as e:
                    print(f"[WARN] No se pudo insertar bookmark: {b['title']} -> {e}")

        with open(output_path, "wb") as f:
            writer.write(f)

        split_files.append(output_path)

    return split_files

def move_whole_file(filename, filepath, df_index, excel_dir):

    base_name = os.path.splitext(os.path.basename(filename))[0]
    match = df_index[df_index['Nombre RFI'].astype(str).str.strip() == base_name]

    if match.empty:
        print(f"[WARN] No se encontró {base_name} en columna 'Nombre RFI' del índice.")
        return

    dest_path = match.iloc[0]['Enlace Destino']
    
    if isinstance(dest_path, str) and dest_path.lower().endswith(".pdf"):
        dest_path = os.path.dirname(dest_path)

    
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
        #suffix_match = re.search(r'_(\d+\.\d+(?:\.\d+)?)\.pdf$', split_name)
        
        suffix_match = re.search(r'_(\d+\.\d+(?:\.\d+)?)(?:_([A-Z0-9\-]+))?\.pdf$', split_name)
        if not suffix_match:
            print(f"[WARN] No se encontró sufijo en: {split_name}")
            continue

        sub_b = suffix_match.group(1)
        sub_c = suffix_match.group(2) if suffix_match.lastindex == 2 else None

        
        if not suffix_match:
            print(f"[WARN] No se encontró sufijo en: {split_name}")
            continue

        suffix = suffix_match.group(1)

        # Buscar filas que coincidan con el nombre original
        #matches = df_index[df_index['Nombre RFI'].astype(str).str.strip() == base_original]

        # Limpiar sufijos (quitar la barra final del Excel)
        #matches = matches.copy()
        #matches['Subindice'] = matches['Subindice'].astype(str).str.strip().str.replace("/", "", regex=False)


        # Buscar coincidencia con el sufijo
        #final_match = matches[matches['Subindice'] == suffix]

        matches = df_index[df_index['Nombre RFI'].astype(str).str.strip() == base_original].copy()

        # Limpiar columnas
        matches['Subindice'] = matches['Subindice'].astype(str).str.strip().str.replace("/", "", regex=False)
        if 'Subindice_2' in matches.columns:
            matches['Subindice_2'] = matches['Subindice_2'].astype(str).str.strip()

        # Extraer partes del sufijo
        parts = suffix.split(".")
        if len(parts) == 2:
            # Casos del tipo "1.2" o "1.2.2"
            final_match = matches[matches['Subindice'] == suffix]
        elif len(parts) == 3:
            # Casos con A/B/C – extraer "B" y "C"
            sub1, sub2 = parts[1], parts[2]
            final_match = matches[
                (matches['Subindice'] == sub1) &
                (matches['Subindice_2'].str.contains(sub2, na=False))
            ]
        else:
            print(f"[WARN] No se pudo interpretar sufijo compuesto para: {split_name}")
            continue

        if final_match.empty:
            print(f"[WARN] No se encontró match para {split_name} con subíndice {suffix}")
            continue

        row = final_match.iloc[0]
        dest_folder = row['Enlace Destino']

        # Si la ruta termina en .pdf, quítalo — queremos solo la carpeta
        if isinstance(dest_folder, str) and dest_folder.lower().endswith(".pdf"):
            dest_folder = os.path.dirname(dest_folder)

        # Convertir en ruta absoluta desde el Excel si es relativa
        if not os.path.isabs(dest_folder):
            dest_folder = os.path.normpath(os.path.join(excel_dir, dest_folder))
        
        new_name = row['Nombre PDF Destino'].strip()

        # Normaliza extensión
        if new_name.lower().endswith(".pdf.pdf"):
            new_name = new_name[:-4]
        elif not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        # ✅ Construir la ruta destino del archivo
        dest_path = os.path.join(dest_folder, new_name)

        # 🧹 Eliminar carpeta redundante si el archivo termina en una subcarpeta con su mismo nombre
        pdf_stem = Path(new_name).stem
        parent_dir = Path(dest_path).parent

        # Si el nombre del directorio final coincide con el del archivo (sin extensión), lo quitamos
        if parent_dir.name == pdf_stem:
            dest_path = str(parent_dir.parent / new_name)

        # ✅ Crear solo las carpetas necesarias (sin incluir el nombre del archivo)
        
        # Verifica si dest_path es una carpeta por error, y corrige
        if os.path.isdir(dest_path):
            dest_path = os.path.join(dest_path, new_name)
        
        # Crea la carpeta (solo la parte del directorio, sin incluir el archivo)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        print(f"[DEBUG] Moviendo a: {dest_path}")
        
        # Limpiar bookmarks y renombrar el archivo
        reader = PdfReader(split_path)
        writer = PdfWriter()

       # Añadir páginas
        for page in reader.pages:
            writer.add_page(page)

        # --- Copiar y anidar marcadores desde reader ---
        def copy_and_nest_bookmarks(reader, src_bms, dst_writer, parent=None):
            for bm in src_bms:
                if isinstance(bm, list):  # subniveles
                    copy_and_nest_bookmarks(reader, bm, dst_writer, parent)
                elif isinstance(bm, Destination):
                    try:
                        page_index = reader.get_destination_page_number(bm)
                        new_bm = dst_writer.add_outline_item(bm.title, page_index, parent=parent)
                    except Exception as e:
                        print(f"[WARN] No se pudo copiar bookmark '{bm.title}': {e}")
                elif isinstance(bm, dict):
                    try:
                        title = bm.get("title", "")
                        dest = bm.get("page")
                        children = bm.get("children", [])
                        if isinstance(dest, Destination):
                            page_index = reader.get_destination_page_number(dest)
                        elif isinstance(dest, int):
                            page_index = dest
                        else:
                            page_index = 0  # fallback si no hay nada válido
                        new_bm = dst_writer.add_outline_item(title, page_index, parent=parent)
                        copy_and_nest_bookmarks(reader, children, dst_writer, new_bm)
                    except Exception as e:
                        print(f"[WARN] No se pudo copiar bookmark '{bm}': {e}")

        # Crear bookmark raíz y anidar los originales
        root_bm = writer.add_outline_item(new_name, 0)
        try:
            copy_and_nest_bookmarks(reader, reader.outline, writer, parent=root_bm)
       
            
        except Exception as e:
            print(f"[WARN] No se pudieron copiar los bookmarks: {e}")

        print(f"[INFO] Dividiendo '{pdf_name}': {title} -> {output_name}")

        # Guardar el archivo final
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




