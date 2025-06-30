from tkinter import Tk, filedialog
from pdf2image import convert_from_path
import os

def seleccionar_pdf():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")])

print("📌 Selecciona un archivo PDF...")
pdf_path = seleccionar_pdf()
if not pdf_path:
    print("🚫 No se seleccionó archivo. Fin del programa.")
    exit()

print("📄 Intentando convertir la primera página a imagen...")
try:
    imagenes = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
    print(f"✅ Conversión exitosa. Total de imágenes: {len(imagenes)}")
except Exception as e:
    print(f"❌ Error durante la conversión: {e}")
