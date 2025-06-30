import os
import fitz  # PyMuPDF
import subprocess
import shutil
from tkinter import Tk, filedialog
from PIL import Image, ImageEnhance
from datetime import datetime

# === GUI para seleccionar PDF ===
Tk().withdraw()
input_pdf = filedialog.askopenfilename(
    title="Selecciona el PDF a procesar",
    filetypes=[("PDF files", "*.pdf")]
)
if not input_pdf:
    print("❌ No se seleccionó ningún archivo.")
    exit()

# === Config ===
base_name = os.path.splitext(os.path.basename(input_pdf))[0]
temp_folder = f"temp_imgs_{base_name}"
intermediate_pdf = f"{base_name}_mejorado.pdf"
ocr_pdf = f"{base_name}_OCR.pdf"
final_pdf = f"{base_name}_FINAL.pdf"
log_file = f"log_{base_name}.txt"

os.makedirs(temp_folder, exist_ok=True)
img_paths = []
log = []

# === Paso 1: Extraer y mejorar páginas ===
doc = fitz.open(input_pdf)
log.append(f"[{datetime.now()}] ✅ Extrayendo y mejorando {len(doc)} páginas...")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    contrast = ImageEnhance.Contrast(img).enhance(1.8)
    brightness = ImageEnhance.Brightness(contrast).enhance(1.05)
    img_path = os.path.join(temp_folder, f"page_{i:04}.png")
    brightness.save(img_path)
    img_paths.append(img_path)

# === Paso 2: Ensamblar a PDF ===
images = [Image.open(p).convert("RGB") for p in img_paths]
images[0].save(intermediate_pdf, save_all=True, append_images=images[1:])
log.append(f"[{datetime.now()}] ✅ PDF mejorado generado: {intermediate_pdf}")

# === Paso 3: Aplicar OCR ===
log.append(f"[{datetime.now()}] ⌛ Aplicando OCR...")
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
log.append(f"[{datetime.now()}] ✅ OCR terminado: {ocr_pdf}")

# === Paso 4: Restaurar marcadores ===
log.append(f"[{datetime.now()}] ✏ Restaurando marcadores...")
doc_original = fitz.open(input_pdf)
toc = doc_original.get_toc()
doc_final = fitz.open(ocr_pdf)
doc_final.set_toc(toc)
doc_final.save(final_pdf)
log.append(f"[{datetime.now()}] 🎉 PDF final generado: {final_pdf}")

# === Paso 5: Limpieza de archivos temporales ===
log.append(f"[{datetime.now()}] 🧹 Limpiando archivos temporales...")
try:
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    if os.path.exists(intermediate_pdf):
        os.remove(intermediate_pdf)
    if os.path.exists(ocr_pdf):
        os.remove(ocr_pdf)
    log.append(f"[{datetime.now()}] ✅ Limpieza completada.")
except Exception as e:
    log.append(f"[{datetime.now()}] ⚠️ Error durante la limpieza: {e}")

# === Guardar log ===
with open(log_file, "w", encoding="utf-8") as f:
    f.write("\n".join(log))
print(f"📝 Log guardado en: {log_file}")
