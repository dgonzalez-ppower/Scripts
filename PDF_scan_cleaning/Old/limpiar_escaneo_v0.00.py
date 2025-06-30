import os
import fitz  # PyMuPDF
import subprocess
import shutil
from tkinter import Tk, filedialog
from PIL import Image, ImageEnhance

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
os.makedirs(temp_folder, exist_ok=True)
img_paths = []

# === Paso 1: Extraer y mejorar páginas ===
doc = fitz.open(input_pdf)
print(f"✅ Extrayendo y mejorando {len(doc)} páginas...")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    contrast = ImageEnhance.Contrast(img).enhance(1.8)
    brightness = ImageEnhance.Brightness(contrast).enhance(1.05)
    img_path = os.path.join(temp_folder, f"page_{i:04}.png")
    brightness.save(img_path)
    img_paths.append(img_path)

# === Paso 2: Ensamblar a PDF ===
intermediate_pdf = f"{base_name}_mejorado.pdf"
images = [Image.open(p).convert("RGB") for p in img_paths]
images[0].save(intermediate_pdf, save_all=True, append_images=images[1:])
print(f"✅ PDF mejorado generado: {intermediate_pdf}")

# === Paso 3: Aplicar OCR ===
ocr_pdf = f"{base_name}_OCR.pdf"
print("⌛ Aplicando OCR...")
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
print(f"✅ OCR terminado: {ocr_pdf}")

# === Paso 4: Restaurar marcadores ===
print("✏ Restaurando marcadores...")
doc_original = fitz.open(input_pdf)
toc = doc_original.get_toc()
doc_final = fitz.open(ocr_pdf)
doc_final.set_toc(toc)
final_pdf = f"{base_name}_FINAL.pdf"
doc_final.save(final_pdf)
print(f"🎉 PDF final generado: {final_pdf}")

# === Paso 5: Limpieza de archivos temporales ===
print("🧹 Limpiando archivos temporales...")
try:
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    if os.path.exists(intermediate_pdf):
        os.remove(intermediate_pdf)
    if os.path.exists(ocr_pdf):
        os.remove(ocr_pdf)
    print("✅ Limpieza completada.")
except Exception as e:
    print(f"⚠️ Error durante la limpieza: {e}")
