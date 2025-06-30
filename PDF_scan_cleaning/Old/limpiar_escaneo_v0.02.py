import os
import fitz  # PyMuPDF
import subprocess
import shutil
from tkinter import Tk, filedialog
from PIL import Image, ImageEnhance
from datetime import datetime
import time

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
working_dir = os.path.dirname(input_pdf)
os.chdir(working_dir)  # Trabajar dentro del directorio del archivo original

temp_folder = os.path.join(working_dir, f"temp_imgs_{base_name}")
intermediate_pdf = os.path.join(working_dir, f"{base_name}_mejorado.pdf")
ocr_pdf = os.path.join(working_dir, f"{base_name}_OCR.pdf")
final_pdf = os.path.join(working_dir, f"{base_name}_FINAL.pdf")
log_file = os.path.join(working_dir, f"log_{base_name}.txt")

os.makedirs(temp_folder, exist_ok=True)
img_paths = []
log = []

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
images = [Image.open(p).convert("RGB") for p in img_paths]
images[0].save(intermediate_pdf, save_all=True, append_images=images[1:])
print(f"✅ PDF mejorado generado: {intermediate_pdf}")

# === Paso 3: Aplicar OCR ===
print("⏳ Aplicando OCR...")
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
doc_final.save(final_pdf)
doc_final.close()
print(f"🎉 PDF final generado: {final_pdf}")

# === Paso 5: Limpieza de archivos temporales ===
print("🧹 Limpiando archivos temporales...")
try:
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    if os.path.exists(intermediate_pdf):
        os.remove(intermediate_pdf)
    for attempt in range(3):
        try:
            if os.path.exists(ocr_pdf):
                os.remove(ocr_pdf)
                break
        except PermissionError:
            print(f"⚠️ Intento {attempt+1}: No se pudo eliminar {ocr_pdf}, reintentando...")
            time.sleep(1)
    else:
        print(f"⚠️ No se pudo eliminar {ocr_pdf} tras varios intentos.")
    print("✅ Limpieza completada.")
except Exception as e:
    print(f"⚠️ Error durante la limpieza: {e}")

# === Guardar log (comentado por ahora) ===
# with open(log_file, "w", encoding="utf-8") as f:
#     f.write("\n".join(log))
# print(f"📝 Log guardado en: {log_file}")
