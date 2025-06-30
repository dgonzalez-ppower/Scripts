import fitz
import pytesseract
from pdf2image import convert_from_path
from tkinter import Tk, filedialog
import os
import difflib

def seleccionar_pdf():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")])

def parece_igual(cadena1, cadena2, umbral=0.7):  # umbral más permisivo
    ratio = difflib.SequenceMatcher(None, cadena1.strip(), cadena2.strip()).ratio()
    return ratio >= umbral

def pixel_rect_to_pdf(palabra, dpi):
    scale = 72 / dpi
    x0 = palabra['x'] * scale
    y0 = palabra['y'] * scale
    x1 = (palabra['x'] + palabra['w']) * scale
    y1 = (palabra['y'] + palabra['h']) * scale
    return fitz.Rect(x0, y0, x1, y1)

def es_tamano_a3_o_mayor(pagina):
    width, height = pagina.rect.width, pagina.rect.height
    return width >= 842 or height >= 1190

COLORES_RGB = [(1, 0, 0), (0, 1, 0), (0.3, 0.7, 1)]

def marcar_textos_stream(pdf_path, textos_objetivo, output_pdf_path, dpi=300):
    doc = fitz.open(pdf_path)
    total_paginas = len(doc)

    for i, page in enumerate(doc):
        print(f"➡️ Procesando página {i+1} de {total_paginas}...")

        if es_tamano_a3_o_mayor(page):
            print(f"⏩ Página {i+1} omitida (tamaño grande)")
            continue

        imagen = convert_from_path(pdf_path, dpi=dpi, first_page=i+1, last_page=i+1)[0]

        ocr_data = pytesseract.image_to_data(imagen, output_type=pytesseract.Output.DICT)
        palabras = [
            {
                "text": ocr_data['text'][j].strip(),
                "x": ocr_data['left'][j],
                "y": ocr_data['top'][j],
                "w": ocr_data['width'][j],
                "h": ocr_data['height'][j]
            }
            for j in range(len(ocr_data['text'])) if ocr_data['text'][j].strip() != ""
        ]

        print("🧾 OCR detectado en la página:")
        for p in palabras:
            print(f"→ '{p['text']}' @ ({p['x']},{p['y']})")

        for idx, objetivo in enumerate(textos_objetivo):
            if not objetivo:
                continue
            for palabra in palabras:
                if parece_igual(palabra["text"], objetivo):
                    rect = pixel_rect_to_pdf(palabra, dpi)
                    page.draw_rect(rect, color=COLORES_RGB[idx], width=1.5)
                    print(f"✅ Texto {idx+1} encontrado: '{palabra['text']}' en página {i+1}")

    doc.save(output_pdf_path)
    print(f"✅ PDF guardado: {output_pdf_path}")

# === BLOQUE PRINCIPAL ===

print("📌 Selecciona un archivo PDF...")
pdf_path = seleccionar_pdf()
if not pdf_path:
    print("🚫 No se seleccionó archivo. Fin del programa.")
    exit()

textos_usuario = [
    "1.1.3",  # rojo
    "70215-25500-EL-RFI-200013",  # verde
    "GEN-10"  # azul claro
]

print("📌 Textos definidos manualmente:", textos_usuario)

while len(textos_usuario) < 3:
    textos_usuario.append("")

pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
output_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_marked_debug.pdf")

print("🚀 Iniciando escaneo del PDF página por página...")
marcar_textos_stream(pdf_path, textos_usuario, output_pdf_path)
