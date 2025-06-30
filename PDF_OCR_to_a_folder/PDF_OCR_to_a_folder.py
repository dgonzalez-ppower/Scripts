import os
import shutil
import csv
import subprocess
from PyPDF2 import PdfReader
from tkinter import Tk, filedialog, messagebox, simpledialog

# ========== PARÁMETROS ==========
OCR_THRESHOLD = 0.20        # Porcentaje mínimo de páginas con texto para considerar "PDF digital"
OCR_LANG = "spa"            # Idioma OCR por defecto ('spa' = español)
LOG_NAME = "log_OCR.csv"    # Nombre del log en la raíz de la carpeta objetivo

def count_text_pages(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        pages_with_text = 0
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                pages_with_text += 1
        return num_pages, pages_with_text
    except Exception as e:
        return None, None

def is_pdf_protected(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            return True
        return False
    except Exception:
        return True

def get_unique_filename(folder, base_filename):
    name, ext = os.path.splitext(base_filename)
    candidate = base_filename
    counter = 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{name}_{counter}{ext}"
        counter += 1
    return candidate

def ensure_folder_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def run_ocr(input_pdf, output_pdf, lang=OCR_LANG):
    try:
        result = subprocess.run(
            ['ocrmypdf', '--language', lang, '--output-type', 'pdf', '--optimize', '3', '--fast-web-view', '1', '--deskew', input_pdf, output_pdf],
            capture_output=True, text=True)
        return result.returncode == 0, result.stderr + result.stdout
    except Exception as e:
        return False, str(e)

def process_pdf(pdf_path, root_folder, log_writer, ocr_lang=OCR_LANG):
    folder = os.path.dirname(pdf_path)
    filename = os.path.basename(pdf_path)

    # 1. Comprobamos si está protegido/corrupto
    if is_pdf_protected(pdf_path):
        prot_folder = os.path.join(folder, "protected_PDFs")
        ensure_folder_exists(prot_folder)
        dest_name = get_unique_filename(prot_folder, filename)
        shutil.move(pdf_path, os.path.join(prot_folder, dest_name))
        log_writer.writerow([pdf_path, "PROTEGIDO/CORRUPTO", os.path.join(prot_folder, dest_name), "PDF protegido o corrupto"])
        print(f"Protegido/corrupto: {pdf_path}")
        return

    # 2. Cuenta páginas con texto
    num_pages, text_pages = count_text_pages(pdf_path)
    if num_pages is None or num_pages == 0:
        prot_folder = os.path.join(folder, "protected_PDFs")
        ensure_folder_exists(prot_folder)
        dest_name = get_unique_filename(prot_folder, filename)
        shutil.move(pdf_path, os.path.join(prot_folder, dest_name))
        log_writer.writerow([pdf_path, "CORRUPTO", os.path.join(prot_folder, dest_name), "PDF ilegible"])
        print(f"Corrupto/ilegible: {pdf_path}")
        return

    pct_text = text_pages / num_pages

    if pct_text >= OCR_THRESHOLD:
        # Suficiente texto: No se hace nada
        log_writer.writerow([pdf_path, "YA_TIENE_TEXTO", "", f"{text_pages}/{num_pages} páginas con texto ({pct_text:.2%})"])
        return

    # 3. Si no tiene suficiente texto → Hacer OCR
    ocr_name = os.path.splitext(filename)[0] + "_OCR.pdf"
    ocr_path = os.path.join(folder, ocr_name)
    ok, ocr_log = run_ocr(pdf_path, ocr_path, lang=ocr_lang)
    if ok and os.path.exists(ocr_path):
        # Mueve el original a NO_OCR (con sufijo si hace falta)
        no_ocr_folder = os.path.join(folder, "NO_OCR")
        ensure_folder_exists(no_ocr_folder)
        safe_name = get_unique_filename(no_ocr_folder, filename)
        shutil.move(pdf_path, os.path.join(no_ocr_folder, safe_name))
        log_writer.writerow([pdf_path, "OCR_HECHO", ocr_path, f"OCR OK: {text_pages}/{num_pages} páginas con texto ({pct_text:.2%})"])
        print(f"OCR hecho: {pdf_path} → {ocr_path}")
    else:
        # Si falla, deja original donde está y loguea el error
        log_writer.writerow([pdf_path, "FALLO_OCR", "", f"{ocr_log}"])
        print(f"Fallo OCR: {pdf_path} ({ocr_log})")

def process_folder_recursively(root_folder, ocr_lang=OCR_LANG):
    log_path = os.path.join(root_folder, LOG_NAME)
    with open(log_path, 'a', newline='', encoding='utf-8') as logfile:
        writer = csv.writer(logfile)
        writer.writerow(["PDF_original", "Estado", "Ruta_destino", "Notas"])
        for dirpath, _, filenames in os.walk(root_folder):
            # Evitar procesar los PDFs ya movidos
            if os.path.basename(dirpath) in ["NO_OCR", "protected_PDFs"]:
                continue
            for filename in filenames:
                if not filename.lower().endswith(".pdf"):
                    continue
                pdf_path = os.path.join(dirpath, filename)
                # Saltar los generados por OCR para evitar bucle
                if filename.endswith("_OCR.pdf"):
                    continue
                process_pdf(pdf_path, root_folder, writer, ocr_lang=ocr_lang)

def select_folder_and_run():
    root = Tk()
    root.withdraw()
    messagebox.showinfo("OCR Selectivo", "Selecciona la carpeta RAÍZ que quieres procesar con OCR")
    folder_selected = filedialog.askdirectory(title="Selecciona carpeta raíz de PDFs")
    if not folder_selected:
        messagebox.showerror("OCR Selectivo", "No has seleccionado ninguna carpeta.")
        return

    # Preguntar si desea cambiar el idioma OCR
    if messagebox.askyesno("Idioma OCR", f"¿Quieres usar OCR en otro idioma diferente de '{OCR_LANG}'?"):
        lang = simpledialog.askstring("Idioma OCR", "Introduce el código del idioma (ej: spa, eng, fra):")
        if not lang:
            lang = OCR_LANG
    else:
        lang = OCR_LANG

    process_folder_recursively(folder_selected, ocr_lang=lang)
    messagebox.showinfo("OCR Selectivo", "¡Proceso terminado! Consulta el log_OCR.csv para ver los resultados.")

if __name__ == "__main__":
    select_folder_and_run()
