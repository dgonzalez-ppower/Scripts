import fitz
import os
import easyocr
from pdf2image import convert_from_path
from tkinter import Tk, filedialog
import difflib
from PIL import Image, ImageDraw

def seleccionar_pdf():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")])

def seleccionar_txt():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Seleccionar archivo de códigos", filetypes=[("Text files", "*.txt")])

def cargar_codigos(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def dividir_codigo(codigo):
    return [p for p in codigo.replace("_", "-").replace("/", "-").replace(".", "-").split("-") if len(p) >= 3]

def es_tamano_a3_o_mayor(pagina):
    return pagina.rect.width >= 842 or pagina.rect.height >= 1190

def obtener_ocr_easyocr(imagen):
    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(imagen)
    return results

def texto_similar(t1, t2, umbral=0.7):
    return difflib.SequenceMatcher(None, t1.lower(), t2.lower()).ratio() >= umbral

def detectar_codigo_en_texto(texto, partes, min_match=2):
    encontrados = [p for p in partes if any(texto_similar(p, palabra) for palabra in texto.split())]
    return len(encontrados) >= min_match, encontrados

def detectar_codigo_en_ocr(ocr_results, partes, min_match=2, tolerancia_y=15):
    matches = []
    for part in partes:
        for (bbox, text, conf) in ocr_results:
            if texto_similar(text, part):
                matches.append((part, bbox))
                break
    if len(matches) >= min_match:
        return True, matches
    return False, []

def dibujar_resultados(imagen_path, matches, output_path):
    im = Image.open(imagen_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    for (_, box) in matches:
        draw.rectangle(box, outline="orange", width=2)
    im.save(output_path)

def procesar_pdf(pdf_path, codigos):
    doc = fitz.open(pdf_path)
    reader = easyocr.Reader(['en'], gpu=False)
    total = len(doc)
    print(f"📘 PDF cargado: {total} páginas")
    for i, page in enumerate(doc):
        print(f"🔍 Página {i+1}/{total}")
        if es_tamano_a3_o_mayor(page):
            print("⏩ Página omitida (A3 o mayor)")
            continue

        texto = page.get_text().strip()
        for codigo in codigos:
            partes = dividir_codigo(codigo)
            if texto:
                ok, encontrados = detectar_codigo_en_texto(texto, partes)
                if ok:
                    print(f"✅ [Texto] Código '{codigo}' encontrado en página {i+1} con partes: {encontrados}")
            else:
                imagen = convert_from_path(pdf_path, dpi=300, first_page=i+1, last_page=i+1)[0]
                temp_img = f"temp_page_{i+1}.png"
                imagen.save(temp_img)
                ocr_results = reader.readtext(temp_img)
                ok, matches = detectar_codigo_en_ocr(ocr_results, partes)
                if ok:
                    print(f"✅ [OCR] Código '{codigo}' encontrado en página {i+1}")
                    dibujar_resultados(temp_img, matches, f"debug_match_page_{i+1}.png")
                os.remove(temp_img)

# === BLOQUE PRINCIPAL ===
print("📌 Selecciona el archivo PDF:")
pdf_path = seleccionar_pdf()
if not pdf_path:
    print("🚫 No se seleccionó PDF.")
    exit()

print("📌 Selecciona el archivo de códigos (uno por línea):")
txt_path = seleccionar_txt()
if not txt_path:
    print("🚫 No se seleccionó archivo de códigos.")
    exit()

codigos = cargar_codigos(txt_path)
print(f"💾 Códigos cargados: {len(codigos)}")

procesar_pdf(pdf_path, codigos)

