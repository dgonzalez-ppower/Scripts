import fitz
import pytesseract
from pdf2image import convert_from_path
from tkinter import Tk, filedialog
import os
import re
import difflib
from collections import Counter

CANDIDATOS = [
    "70215-40-YQ_-QNQ-UTE-007",
    "70215-40-YQ_-QNQ-UTE-008",
    "70215-40-YQ_-QNQ-UTE-013",
    "70215-40-YQ_-QNQ-UTE-014",
    "70215-40-YQ_-QNQ-UTE-015",
    "70215-40-YQ_-QNQ-UTE-016",
    "70215-40-YQ_-QNQ-UTE-018",
    "70215-40-YQ_-QNQ-UTE-019",
    "70215-40-YQ_-QNQ-UTE-021",
    "70215-40-YQ_-QNQ-UTE-022",
    "70215-40-YQ_-QNQ-UTE-023",
    "70215-40-YQ_-QNQ-UTE-024",
    "70215-40-YQ_-QNQ-UTE-025",
    "70215-40-YQ_-QNQ-UTE-026",
    "70215-40-YQ_-QNQ-UTE-027",
    "70215-40-YQ_-QNQ-UTE-028",
    "70215-40-YQ_-QNQ-UTE-029",
    "70215-40-YQ_-QNQ-UTE-030",
    "70215-40-YQ_-QNQ-UTE-031",
    "70215-40-YQ_-QNQ-UTE-033",
]

# === Funciones OCR y lógica fuzzy ===

def parece_igual(cadena1, cadena2, umbral=0.85):
    ratio = difflib.SequenceMatcher(None, cadena1.strip(), cadena2.strip()).ratio()
    return ratio >= umbral

def pixel_rect_to_pdf(palabra, dpi):
    scale = 72 / dpi
    x0 = palabra['x'] * scale
    y0 = palabra['y'] * scale
    x1 = (palabra['x'] + palabra['w']) * scale
    y1 = (palabra['y'] + palabra['h']) * scale
    return fitz.Rect(x0, y0, x1, y1)

def reconstruir_cadena(centro, palabras, direccion, valor_objetivo, tolerancia_altura=15, max_palabras=6, distancia_max=300):
    match = ""
    grupo = []
    palabras_iteradas = palabras if direccion == 'derecha' else list(reversed(palabras))

    for palabra in palabras_iteradas:
        if palabra["text"] == "/":
            continue
        misma_linea = abs(palabra["y"] - centro["y"]) < tolerancia_altura
        dentro_distancia = abs(palabra["x"] - centro["x"]) < distancia_max
        lado_correcto = (palabra["x"] > centro["x"]) if direccion == "derecha" else (palabra["x"] < centro["x"])

        if misma_linea and dentro_distancia and lado_correcto:
            if direccion == "derecha":
                match += palabra["text"]
                grupo.append(palabra)
            else:
                match = palabra["text"] + match
                grupo.append(palabra)

            if parece_igual(match, valor_objetivo):
                return grupo
            if len(grupo) >= max_palabras:
                break
    return None

def detectar_actividad_ppi_desde_texto(texto):
    patron = r"actividad\(es\).*?PPI[:：]?\s*([A-Z0-9\-_/.]+)"
    match = re.search(patron, texto, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extraer_texto_pytesseract(image, config=""):
    return pytesseract.image_to_string(image, config=config)

def determinar_actividad_por_mayoria(imagen):
    resultados = []

    print("🔎 OCR modo normal...")
    text1 = extraer_texto_pytesseract(imagen)
    r1 = detectar_actividad_ppi_desde_texto(text1)
    if r1:
        print(f"🟢 OCR 1: {r1}")
        resultados.append(r1)

    print("🔎 OCR modo PSM 6...")
    text2 = extraer_texto_pytesseract(imagen, config="--psm 6")
    r2 = detectar_actividad_ppi_desde_texto(text2)
    if r2:
        print(f"🟢 OCR 2: {r2}")
        resultados.append(r2)

    print("🔎 OCR modo PSM 11...")
    text3 = extraer_texto_pytesseract(imagen, config="--psm 11")
    r3 = detectar_actividad_ppi_desde_texto(text3)
    if r3:
        print(f"🟢 OCR 3: {r3}")
        resultados.append(r3)

    if not resultados:
        print("❌ Ningún OCR detectó actividad.")
        return None

    votos = Counter(resultados)
    ganador, cantidad = votos.most_common(1)[0]
    if cantidad >= 2:
        print(f"✅ Actividad seleccionada por mayoría: {ganador}")
        return ganador
    else:
        print("❌ No hay mayoría suficiente para determinar actividad.")
        return None

def es_tamano_a3_o_mayor(pagina):
    width, height = pagina.rect.width, pagina.rect.height
    return width >= 842 or height >= 1190  # en puntos PDF

def seleccionar_pdf():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Selecciona un PDF", filetypes=[("PDF", "*.pdf")])

# === Procesamiento principal ===

def marcar_textos_y_ppi_actividad(pdf_path, textos_objetivo, output_pdf_path, dpi=300):
    doc = fitz.open(pdf_path)

    print("📄 Escaneando primera página con triple OCR...")
    primera_img = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)[0]
    actividad_ppi_valor = determinar_actividad_por_mayoria(primera_img)
    ppi_valor = textos_objetivo[0]

    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=len(doc), fmt='ppm')

    for i, page in enumerate(doc):
        page_num = i + 1

        if es_tamano_a3_o_mayor(page):
            print(f"⚠️ Página {page_num} descartada por tamaño A3 o superior.")
            continue

        print(f"📄 Procesando página {page_num}...")
        image = images[i]
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        palabras = [
            {
                "text": ocr_data['text'][j].strip(),
                "x": ocr_data['left'][j],
                "y": ocr_data['top'][j],
                "w": ocr_data['width'][j],
                "h": ocr_data['height'][j]
            }
            for j in range(len(ocr_data['text']))
            if ocr_data['text'][j].strip() != ""
        ]

        rojo_detectado = False
        for palabra in palabras:
            if parece_igual(palabra["text"], ppi_valor):
                rect = pixel_rect_to_pdf(palabra, dpi)
                page.draw_rect(rect, color=(1, 0, 0), width=1.5)
                rojo_detectado = True
                print(f"🟥 PPI detectado en página {page_num}: '{palabra['text']}'")

        verde_detectado = False
        if actividad_ppi_valor:
            for palabra in palabras:
                if parece_igual(palabra["text"], actividad_ppi_valor):
                    rect = pixel_rect_to_pdf(palabra, dpi)
                    page.draw_rect(rect, color=(0, 1, 0), width=1.5)
                    verde_detectado = True

        slash_words = [w for w in palabras if w["text"] == "/"]
        for slash in slash_words:
            if not verde_detectado and actividad_ppi_valor:
                grupo_verde = reconstruir_cadena(slash, palabras, "derecha", actividad_ppi_valor)
                if grupo_verde:
                    for palabra in grupo_verde:
                        rect = pixel_rect_to_pdf(palabra, dpi)
                        page.draw_rect(rect, color=(0, 1, 0), width=1.5)
                    print(f"🧩 Reconstrucción VERDE fuzzy en página {page_num}: '{actividad_ppi_valor}'")

            if not rojo_detectado and ppi_valor:
                grupo_rojo = reconstruir_cadena(slash, palabras, "izquierda", ppi_valor)
                if grupo_rojo:
                    for palabra in grupo_rojo:
                        rect = pixel_rect_to_pdf(palabra, dpi)
                        page.draw_rect(rect, color=(1, 0, 0), width=1.5)
                    print(f"🧩 Reconstrucción ROJA fuzzy en página {page_num}: '{ppi_valor}'")

    doc.save(output_pdf_path)
    print(f"\n✅ PDF marcado guardado en:\n{output_pdf_path}")

# === MAIN ===
print("📌 Seleccioná el PDF a escanear...")
pdf_path = seleccionar_pdf()
if not pdf_path:
    print("🚫 No se seleccionó ningún archivo. Abortando.")
    exit()

pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
output_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_marked.pdf")

print("🚀 Iniciando procesamiento completo...")
marcar_textos_y_ppi_actividad(pdf_path, CANDIDATOS, output_pdf_path)
