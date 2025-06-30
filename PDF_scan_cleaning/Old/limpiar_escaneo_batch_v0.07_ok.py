import os
import fitz  # PyMuPDF
import subprocess
import shutil
from tkinter import Tk, filedialog, simpledialog
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# === GUI para seleccionar archivo o carpeta ===
Tk().withdraw()
choice = filedialog.askopenfilename(title="Selecciona un PDF o CANCELA para elegir una carpeta", filetypes=[("PDF files", "*.pdf")])
input_files = []
dest_folder = ""

if choice:
    input_files = [choice]
    dest_folder = os.path.dirname(choice)
else:
    source_folder = filedialog.askdirectory(title="Selecciona la carpeta con los PDFs a procesar")
    if not source_folder:
        print("❌ No se seleccionó ningún archivo ni carpeta.")
        exit()
    dest_folder = filedialog.askdirectory(title="Selecciona carpeta de destino para los resultados")
    if not dest_folder:
        print("❌ No se seleccionó carpeta de destino.")
        exit()
    input_files = [os.path.join(source_folder, f) for f in os.listdir(source_folder) if f.lower().endswith(".pdf")]

if not input_files:
    print("❌ No se encontraron archivos PDF para procesar.")
    exit()

modo_mejora = simpledialog.askinteger("Modo de mejora visual", "Selecciona preset de mejora visual:\n1 - Contraste + Brillo + Borde\n2 - Suavizado adicional\n3 - Autocontraste + Suavizado\n4 - Umbral binario suave\n(default = 1)", initialvalue=1)

def aplicar_mejora(img, modo):
    if modo == 2:
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = img.filter(ImageFilter.EDGE_ENHANCE)
        img = img.filter(ImageFilter.SMOOTH_MORE)
    elif modo == 3:
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SMOOTH)
    elif modo == 4:
        img = img.convert("L").point(lambda p: 255 if p > 180 else 0).convert("RGB")
    else:  # default
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = img.filter(ImageFilter.EDGE_ENHANCE)
    return img

def procesar_pdf(input_pdf):
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]
    temp_folder = os.path.join(dest_folder, f"temp_imgs_{base_name}")
    intermediate_pdf = os.path.join(dest_folder, f"{base_name}_mejorado.pdf")
    ocr_pdf = os.path.join(dest_folder, f"{base_name}_OCR.pdf")
    final_pdf = os.path.join(dest_folder, f"{base_name}_FINAL.pdf")
    log_file = os.path.join(dest_folder, f"log_{base_name}.txt")

    os.makedirs(temp_folder, exist_ok=True)
    img_paths = []
    log = []
    log.append(f"[{datetime.now()}] Inicio del proceso")
    log.append(f"Archivo seleccionado: {input_pdf}")

    try:
        doc = fitz.open(input_pdf)
        log.append(f"[{datetime.now()}] Extrayendo y mejorando {len(doc)} páginas")
        print(f"✅ Extrayendo y mejorando {len(doc)} páginas de {base_name}...")
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = aplicar_mejora(img, modo_mejora)
            img_path = os.path.join(temp_folder, f"page_{i:04}.png")
            img.save(img_path)
            img_paths.append(img_path)
    except Exception as e:
        log.append(f"[{datetime.now()}] ❌ Error durante la mejora de páginas: {e}")
        return

    try:
        images = [Image.open(p).convert("RGB") for p in img_paths]
        images[0].save(intermediate_pdf, save_all=True, append_images=images[1:])
        log.append(f"[{datetime.now()}] PDF mejorado generado: {intermediate_pdf}")
        print(f"✅ PDF mejorado generado: {intermediate_pdf}")
    except Exception as e:
        log.append(f"[{datetime.now()}] ❌ Error al ensamblar PDF: {e}")
        return

    print("⏳ Aplicando OCR...")
    log.append(f"[{datetime.now()}] Iniciando OCR...")
    try:
        subprocess.run([
            "ocrmypdf",
            "--force-ocr",
            "--deskew",
            "--rotate-pages",
            "--rotate-pages-threshold", "0.8",
            "--tesseract-timeout", "60",
            "--output-type", "pdfa",
            "--pdf-renderer", "hocr",
            intermediate_pdf,
            ocr_pdf
        ], check=True)
        log.append(f"[{datetime.now()}] OCR terminado: {ocr_pdf}")
        print(f"✅ OCR terminado: {ocr_pdf}")
    except subprocess.CalledProcessError as e:
        log.append(f"[{datetime.now()}] ❌ Error en OCR: {e}")
        return

    print("✏ Restaurando marcadores...")
    log.append(f"[{datetime.now()}] Restaurando marcadores...")
    try:
        doc_original = fitz.open(input_pdf)
        toc = doc_original.get_toc()
        doc_final = fitz.open(ocr_pdf)
        doc_final.set_toc(toc)
        doc_final.save(final_pdf)
        doc_final.close()
        log.append(f"[{datetime.now()}] PDF final generado: {final_pdf}")
        print(f"🎉 PDF final generado: {final_pdf}")
    except Exception as e:
        log.append(f"[{datetime.now()}] ❌ Error al restaurar marcadores: {e}")
        return

    print("🧹 Limpiando archivos temporales...")
    log.append(f"[{datetime.now()}] Iniciando limpieza de temporales")
    try:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
            log.append(f"[{datetime.now()}] Carpeta temporal eliminada: {temp_folder}")
        if os.path.exists(intermediate_pdf):
            os.remove(intermediate_pdf)
            log.append(f"[{datetime.now()}] Intermedio eliminado: {intermediate_pdf}")
        for attempt in range(3):
            try:
                if os.path.exists(ocr_pdf):
                    os.remove(ocr_pdf)
                    log.append(f"[{datetime.now()}] OCR eliminado: {ocr_pdf}")
                    break
            except PermissionError:
                print(f"⚠️ Intento {attempt+1}: No se pudo eliminar {ocr_pdf}, reintentando...")
                time.sleep(1)
        else:
            print(f"⚠️ No se pudo eliminar {ocr_pdf} tras varios intentos.")
            log.append(f"[{datetime.now()}] ⚠️ No se pudo eliminar {ocr_pdf} tras varios intentos")
        print("✅ Limpieza completada.")
        log.append(f"[{datetime.now()}] Limpieza completada")
    except Exception as e:
        print(f"⚠️ Error durante la limpieza: {e}")
        log.append(f"[{datetime.now()}] Error durante la limpieza: {e}")

    log.append(f"[{datetime.now()}] Proceso completado con éxito")
    log.append(f"Archivo final: {final_pdf}")
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(log))
        print(f"📝 Log guardado en: {log_file}")
    except Exception as e:
        print(f"⚠️ Error al guardar log: {e}")

# === Procesamiento en paralelo ===
if len(input_files) > 1:
    print(f"🔁 Procesando {len(input_files)} archivos en paralelo...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(procesar_pdf, pdf) for pdf in input_files]
        for f in as_completed(futures):
            pass
elif len(input_files) == 1:
    procesar_pdf(input_files[0])
