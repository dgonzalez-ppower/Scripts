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

def parece_igual(cadena1, cadena2, umbral=0.65):
    cadena1, cadena2 = cadena1.strip(), cadena2.strip()
    if cadena1 == cadena2:
        return True
    if cadena2 in cadena1 and cadena1 != cadena2:
        return False
    ratio = difflib.SequenceMatcher(None, cadena1, cadena2).ratio()
    return ratio >= umbral

def es_parecido(cadena1, cadena2, umbral=0.5):
    """Comparación mucho más permisiva para detectar OCR dudoso"""
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

def agrupar_por_lineas(palabras, tolerancia_y=10):
    lineas = []
    for palabra in palabras:
        y = palabra['y']
        agregado = False
        for linea in lineas:
            if abs(linea[0]['y'] - y) < tolerancia_y:
                linea.append(palabra)
                agregado = True
                break
        if not agregado:
            lineas.append([palabra])
    return lineas

def reconstruir_en_linea(texto_objetivo, linea, max_combinacion=5):
    reconstrucciones = []
    for i in range(len(linea)):
        combinada = linea[i]['text']
        for j in range(1, max_combinacion):
            if i + j >= len(linea):
                break
            combinada += linea[i + j]['text']
            if parece_igual(combinada, texto_objetivo):
                reconstrucciones.append((combinada, linea[i:i + j + 1]))
                break
    return reconstrucciones

COLORES_RGB = [(1, 0, 0), (0, 1, 0), (0.3, 0.7, 1)]
COLOR_DIFUSO = (1, 0.5, 0)  # naranja para posibles coincidencias dudosas

def marcar_textos_fuzzy(pdf_path, textos_objetivo, output_pdf_path, dpi=300):
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

        lineas = agrupar_por_lineas(palabras)

        for idx, objetivo in enumerate(textos_objetivo):
            if not objetivo:
                continue

            match_directo = False

            for palabra in palabras:
                if parece_igual(palabra['text'], objetivo):
                    rect = pixel_rect_to_pdf(palabra, dpi)
                    page.draw_rect(rect, color=COLORES_RGB[idx], width=1.5)
                    print(f"✅ Coincidencia directa con '{palabra['text']}' ≈ '{objetivo}'")
                    match_directo = True

            for linea in lineas:
                reconstrucciones = reconstruir_en_linea(objetivo, linea)
                for combinada, grupo in reconstrucciones:
                    if combinada != objetivo:
                        continue
                    print(f"🧩 Reconstrucción exacta: '{combinada}' ≈ '{objetivo}'")
                    for palabra in grupo:
                        rect = pixel_rect_to_pdf(palabra, dpi)
                        page.draw_rect(rect, color=COLORES_RGB[idx], width=1.5)
                    match_directo = True

            if not match_directo:
                for palabra in palabras:
                    if es_parecido(palabra['text'], objetivo):
                        rect = pixel_rect_to_pdf(palabra, dpi)
                        page.draw_rect(rect, color=COLOR_DIFUSO, width=1.2)
                        print(f"⚠️ Coincidencia aproximada dudosa: '{palabra['text']}' ≈ '{objetivo}'")

    doc.save(output_pdf_path)
    print(f"✅ PDF guardado: {output_pdf_path}")

# === BLOQUE PRINCIPAL ===

print("📌 Selecciona un archivo PDF...")
pdf_path = seleccionar_pdf()
if not pdf_path:
    print("🚫 No se seleccionó archivo. Fin del programa.")
    exit()

textos_usuario = [
    "ELE-48",  # rojo
    "200018",  # verde
    "70215-40-YQ_-QNQ-UTE-027"  # azul claro
]

print("📌 Textos definidos manualmente:", textos_usuario)

while len(textos_usuario) < 3:
    textos_usuario.append("")

pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
output_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_marked_fuzzyassist.pdf")

print("🚀 Iniciando escaneo del PDF página por página...")
marcar_textos_fuzzy(pdf_path, textos_usuario, output_pdf_path)