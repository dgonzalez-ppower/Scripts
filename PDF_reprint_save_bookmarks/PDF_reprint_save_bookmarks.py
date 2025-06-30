import os
import time
import shutil
import csv
from tkinter import Tk, filedialog, messagebox
from PyPDF2 import PdfReader
import subprocess

# === Configuración FIJA ===
PDF_CREATOR_PATH = r"C:\Program Files\PDFCreator\PDFCreator.exe"
PDF_TEMP_FOLDER = r"\\Neotrantor\pp\PUBLICO\20-CARPETAS PERSONALES\dgonzalez\PDFCreatorOutput"
TIMEOUT_S = 90
RETRY_LIMIT = 2

def get_all_pdfs(root_folder):
    pdfs = []
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith('.pdf'):
                pdfs.append(os.path.join(dirpath, filename))
    return pdfs

def clean_temp_folder(folder):
    for f in os.listdir(folder):
        fp = os.path.join(folder, f)
        try:
            if os.path.isfile(fp):
                try_remove_file(fp)
        except Exception as e:
            print(f"No se pudo eliminar {fp}: {e}")

def extract_bookmarks(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        def parse_outline(outline, parent=None):
            bookmarks = []
            for item in outline:
                if isinstance(item, list):
                    bookmarks.append(parse_outline(item, parent))
                else:
                    title = item.title
                    page_num = reader.get_destination_page_number(item)
                    bookmarks.append({'title': title, 'page': page_num, 'children': []})
            return bookmarks
        outline = []
        if hasattr(reader, "outlines"):
            outline = reader.outlines
        elif hasattr(reader, "outline"):
            outline = reader.outline
        else:
            return []
        return parse_outline(outline)
    except Exception as e:
        print(f"Error al extraer bookmarks de {pdf_path}: {e}")
        return []

def print_pdf_to_pdfcreator(pdf_path):
    cmd = [
        PDF_CREATOR_PATH,
        '/PrintFile=' + pdf_path,
        '/NoStart'
    ]
    # No hay que poner comillas, subprocess las gestiona.
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Error lanzando PDFCreator: {e}")

def wait_for_new_pdf_in_folder(folder, timeout=TIMEOUT_S):
    t0 = time.time()
    before = set(os.listdir(folder))
    while time.time() - t0 < timeout:
        after = set(os.listdir(folder))
        new_files = after - before
        for f in new_files:
            if f.lower().endswith('.pdf'):
                return os.path.join(folder, f)
        time.sleep(1)
    return None

def add_bookmarks_to_pdf(src_path, dest_path, bookmarks):
    reader = PdfReader(src_path)
    from PyPDF2 import PdfWriter
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    def add_bms(bms, parent=None):
        for bm in bms:
            child = writer.add_bookmark(bm['title'], bm['page'], parent)
            if bm.get('children'):
                add_bms(bm['children'], child)
    add_bms(bookmarks)
    with open(dest_path, 'wb') as f:
        writer.write(f)

def check_pdf_has_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                return True
        return False
    except Exception as e:
        print(f"Error analizando {pdf_path}: {e}")
        return False

def try_remove_file(filepath, retries=10, delay=1.0):
    for attempt in range(retries):
        try:
            os.remove(filepath)
            return True
        except PermissionError as e:
            if attempt < retries - 1:
                print(f"No se pudo eliminar {filepath}, reintentando ({attempt+1}/{retries})...")
                time.sleep(delay)
            else:
                print(f"ERROR: No se pudo eliminar {filepath} después de {retries} intentos.")
                return False
        except Exception as e:
            print(f"ERROR inesperado eliminando {filepath}: {e}")
            return False
    return False

def try_move_file(src, dst, retries=10, delay=1.0):
    for attempt in range(retries):
        try:
            shutil.move(src, dst)
            return True
        except PermissionError as e:
            if attempt < retries - 1:
                print(f"No se pudo mover {src}, reintentando ({attempt+1}/{retries})...")
                time.sleep(delay)
            else:
                print(f"ERROR: No se pudo mover {src} después de {retries} intentos.")
                return False
        except Exception as e:
            print(f"ERROR inesperado moviendo {src}: {e}")
            return False
    return False

def process_batch(input_folder, output_folder, log_csv):
    pdfs = get_all_pdfs(input_folder)
    clean_temp_folder(PDF_TEMP_FOLDER)
    done = set()
    if os.path.exists(log_csv):
        with open(log_csv, newline='', encoding='utf-8') as f:
            for row in csv.reader(f):
                if row and row[1] == "OK":
                    done.add(row[0])
    with open(log_csv, 'a', newline='', encoding='utf-8') as logfile:
        writer = csv.writer(logfile)
        for pdf in pdfs:
            rel_path = os.path.relpath(pdf, input_folder)
            out_pdf = os.path.join(output_folder, rel_path)
            os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
            if out_pdf in done:
                print(f"Ya procesado: {out_pdf}")
                continue
            bookmarks = extract_bookmarks(pdf)
            for attempt in range(RETRY_LIMIT):
                try:
                    print(f"Reimprimiendo: {pdf}")
                    clean_temp_folder(PDF_TEMP_FOLDER)
                    print_pdf_to_pdfcreator(pdf)
                    temp_pdf = wait_for_new_pdf_in_folder(PDF_TEMP_FOLDER)
                    if not temp_pdf:
                        raise Exception("Timeout esperando PDFCreator")
                    add_bookmarks_to_pdf(temp_pdf, out_pdf, bookmarks)
                    tiene_texto = "SI" if check_pdf_has_text(out_pdf) else "NO"
                    writer.writerow([out_pdf, "OK", tiene_texto])
                    print(f"OK: {out_pdf} (Texto: {tiene_texto})")
                    try_remove_file(temp_pdf)
                    break
                except Exception as e:
                    print(f"Fallo procesando {pdf}: {e}")
                    if attempt == RETRY_LIMIT - 1:
                        writer.writerow([out_pdf, f"FALLO: {e}", ""])
                        try:
                            if temp_pdf and os.path.exists(temp_pdf):
                                try_remove_file(temp_pdf)
                        except: pass
                    else:
                        print("Reintentando...")

def main_gui():
    root = Tk()
    root.withdraw()
    messagebox.showinfo("PDF Batch Reimpression", "Selecciona la carpeta ORIGEN con los PDFs a procesar")
    input_folder = filedialog.askdirectory(title="Carpeta ORIGEN (PDFs)")
    if not input_folder:
        print("No seleccionaste carpeta origen.")
        return

    messagebox.showinfo("PDF Batch Reimpression", "Selecciona la carpeta DESTINO donde se guardarán los PDFs procesados")
    output_folder = filedialog.askdirectory(title="Carpeta DESTINO (PDFs procesados)")
    if not output_folder:
        print("No seleccionaste carpeta destino.")
        return

    log_csv = os.path.join(output_folder, "log_proceso_pdfs.csv")
    process_batch(input_folder, output_folder, log_csv)
    messagebox.showinfo("¡Finalizado!", "Proceso completado. Consulta el log para detalles.")

if __name__ == "__main__":
    main_gui()
