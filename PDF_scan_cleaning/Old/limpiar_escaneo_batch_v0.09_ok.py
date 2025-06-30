import os
import fitz  # PyMuPDF
import subprocess
import shutil
from tkinter import Tk, filedialog
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

modo_mejora = 1  # preset fijo por ahora

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
    else:
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = img.filter(ImageFilter.EDGE_ENHANCE)
    return img

def procesar_pdf(input_pdf):
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]
    temp_folder = os.path.join(dest_folder, f"temp_imgs_{base_name}")
    final_pdf = os.path.join(dest_folder, f"{base_name}_FINAL.pdf")
    ocr_pdf = os.path.join(dest_folder, f"{base_name}_FINAL_OCR.pdf")
    log_file = os.path.join(dest_folder, f"log_{base_name}.txt")

    os.makedirs(temp_folder, exist_ok=True)
    log = []
    log.append(f"[{datetime.now()}] Inicio del proceso")
    log.append(f"Archivo seleccionado: {input_pdf}")

    try:
        doc_original = fitz.open(input_pdf)
        paginas_texto = []
        paginas_imagen = []
        for i, page in enumerate(doc_original):
            text = page.get_text().strip()
            if len(text) > 30:
                paginas_texto.append(i)
            else:
                paginas_imagen.append(i)

        log.append(f"[{datetime.now()}] Detectadas {len(paginas_texto)} páginas de texto y {len(paginas_imagen)} páginas tipo imagen")

        paginas_mejoradas = {}

        for i in paginas_imagen:
            page = doc_original.load_page(i)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = aplicar_mejora(img, modo_mejora)
            img_path = os.path.join(temp_folder, f"page_{i:04}.png")
            img.save(img_path)
            paginas_mejoradas[i] = img_path

        nuevo_doc = fitz.open()

        for i in range(len(doc_original)):
            if i in paginas_texto:
                nuevo_doc.insert_pdf(doc_original, from_page=i, to_page=i)
            else:
                img_path = paginas_mejoradas[i]
                #img = Image.open(img_path)
                #w, h = img.size
                with Image.open(img_path) as img:
                    w, h = img.size
                
                rect_original = doc_original[i].rect

                imgpdf = fitz.open()
                page = imgpdf.new_page(width=rect_original.width, height=rect_original.height)

                aspect_ratio_img = w / h
                aspect_ratio_page = rect_original.width / rect_original.height

                if aspect_ratio_img > aspect_ratio_page:
                    new_width = rect_original.width
                    new_height = rect_original.width / aspect_ratio_img
                else:
                    new_height = rect_original.height
                    new_width = rect_original.height * aspect_ratio_img

                x0 = rect_original.x0 + (rect_original.width - new_width) / 2
                y0 = rect_original.y0 + (rect_original.height - new_height) / 2
                x1 = x0 + new_width
                y1 = y0 + new_height

                rect = fitz.Rect(x0, y0, x1, y1)
                page.insert_image(rect, filename=img_path)
                nuevo_doc.insert_pdf(imgpdf)

        toc = doc_original.get_toc()
        nuevo_doc.set_toc(toc)
        nuevo_doc.save(final_pdf)
        nuevo_doc.close()

        log.append(f"[{datetime.now()}] PDF final generado: {final_pdf}")
        print(f"🎉 PDF final generado: {final_pdf}")

        # Aplicar OCR al PDF final
        print(f"🔎 Aplicando OCR al PDF final...")
        try:
            subprocess.run([
                "ocrmypdf",
                "--skip-text",
                "--deskew",
                "--rotate-pages",
                "--rotate-pages-threshold", "0.8",
                "--tesseract-timeout", "60",
                "--output-type", "pdfa",
                "--pdf-renderer", "hocr",
                final_pdf,
                ocr_pdf
            ], check=True)
            log.append(f"[{datetime.now()}] OCR aplicado: {ocr_pdf}")
            print(f"✅ OCR aplicado correctamente: {ocr_pdf}")
        
        # Intentar eliminar el archivo pesado sin OCR si el OCR fue exitoso
            try:
                if os.path.exists(ocr_pdf) and os.path.exists(final_pdf):
                    os.remove(final_pdf)
                    log.append(f"[{datetime.now()}] ✅ Archivo FINAL eliminado tras aplicar OCR.")
            except Exception as e:
                log.append(f"[{datetime.now()}] ⚠️ No se pudo eliminar el archivo FINAL: {e}")

        
        except subprocess.CalledProcessError as e:
            log.append(f"[{datetime.now()}] ❌ Error aplicando OCR: {e}")
            print(f"⚠️ Error aplicando OCR: {e}")

    except Exception as e:
        log.append(f"[{datetime.now()}] ❌ Error procesando PDF: {e}")
        print(f"⚠️ Error: {e}")

    try:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
    except Exception as e:
        print(f"⚠️ Error limpiando temporales: {e}")

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(log))
        print(f"📝 Log guardado en: {log_file}")
    except Exception as e:
        print(f"⚠️ Error al guardar log: {e}")

if len(input_files) > 1:
    print(f"🔁 Procesando {len(input_files)} archivos en paralelo...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(procesar_pdf, pdf) for pdf in input_files]
        for f in as_completed(futures):
            pass
elif len(input_files) == 1:
    procesar_pdf(input_files[0])
