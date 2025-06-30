import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from traducir_pdf_gui import is_scanned, process_pdf_precise_translation
import fitz
from langdetect import detect
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import defaultdict
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

LOG = defaultdict(list)

def detect_language(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        sample_text = " ".join(page.get_text() for page in doc[:2])
        lang = detect(sample_text) if sample_text.strip() else "und"
        return lang
    except Exception as e:
        print(f"⚠️ Error analizando idioma de {os.path.basename(pdf_path)}: {e}")
        return "und"

def filtrar_pdfs_a_traducir(carpeta):
    pdfs = glob.glob(os.path.join(carpeta, "*.pdf"))
    lista_traducibles = []
    LOG["detalles"] = []

    for pdf in pdfs:
        filename = os.path.basename(pdf)
        calidad = ""
        idioma = "und"

        try:
            if is_scanned(pdf):
                doc = fitz.open(pdf)
                ocr_texto = extraer_texto_con_ocr(pdf, paginas=2)
                if ocr_texto.strip():
                    calidad = "escaneado sin texto"
                    idioma = detect(ocr_texto)
                else:
                    calidad = "escaneado sin texto"
                    idioma = "und"
            else:
                calidad = "tipo texto"

            doc = fitz.open(pdf)
            text_sample = "".join(page.get_text() for page in doc[:2])
            idioma = detect(text_sample) if text_sample.strip() else "und"

        except Exception as e:
            print(f"⚠️ Error analizando {filename}: {e}")
            calidad = "error"
            idioma = "und"

        aplicar = False
        if calidad == "escaneado sin texto":
            aplicar = True
        elif idioma not in ['es', 'en']:
            aplicar = True

        if aplicar:
            lista_traducibles.append(pdf)
            resultado = "aplicable - pendiente"
        else:
            resultado = "no aplicable"

        LOG["detalles"].append({
            "nombre del archivo": filename,
            "calidad original": calidad,
            "idioma original": idioma,
            "resultado traducción": resultado
        })

    LOG["total_detectados"] = pdfs
    return lista_traducibles

def procesar_pdf(path):
    filename = os.path.basename(path)
    try:
        output = process_pdf_precise_translation(path)
        print(f"✅ Completado: {filename}")
        LOG["traducidos_ok"].append(filename)

        for entry in LOG["detalles"]:
            if entry["nombre del archivo"] == filename:
                entry["resultado traducción"] = "aplicable - satisfactoria"

        return output
    except Exception as e:
        print(f"❌ Error en {filename}: {e}")
        LOG["con_errores"].append(filename)

        for entry in LOG["detalles"]:
            if entry["nombre del archivo"] == filename:
                entry["resultado traducción"] = "aplicable - error"

        return None

def procesar_en_paralelo(carpeta_pdf, max_hilos=4):
    lista = filtrar_pdfs_a_traducir(carpeta_pdf)
    print(f"📂 PDFs a traducir: {len(lista)}")

    resultados = []
    with ThreadPoolExecutor(max_workers=max_hilos) as executor:
        future_to_pdf = {executor.submit(procesar_pdf, pdf): pdf for pdf in lista}
        for future in as_completed(future_to_pdf):
            resultado = future.result()
            if resultado:
                resultados.append(resultado)

    print("📋 Resumen final:")
    print(f"   Total detectados: {len(LOG['total_detectados'])}")
    print(f"   Traducidos OK: {len(LOG['traducidos_ok'])}")
    print(f"   Omitidos por idioma: {len(LOG['omitido_por_idioma'])}")
    print(f"   Con errores: {len(LOG['con_errores'])}")

    if LOG["detalles"]:
        resumen_path = os.path.join(carpeta_pdf, "log_traduccion.xlsx")
        df = pd.DataFrame(LOG["detalles"])
        df.to_excel(resumen_path, index=False)
        print(f"📊 Log detallado guardado en: {resumen_path}")
    else:
        print("⚠️ No se generó log porque no se procesó ningún archivo.")
    df = pd.DataFrame(LOG["detalles"])
    df.to_excel(resumen_path, index=False)

    print(f"📊 Log detallado en Excel guardado en: {resumen_path}")
    return resultados

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Oculta la ventana principal

    carpeta = filedialog.askdirectory(title="Selecciona la carpeta con los PDFs a traducir")
    if not carpeta:
        messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta.")
        sys.exit(0)

    procesar_en_paralelo(carpeta_pdf=carpeta, max_hilos=4)

def extraer_texto_con_ocr(pdf_path, paginas=2):
    """Extrae texto vía OCR de las primeras `paginas` del PDF dado."""
    texto = ""
    try:
        doc = fitz.open(pdf_path)
        for i in range(min(paginas, len(doc))):
            page = doc[i]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("ppm")  # formato compatible con PIL
            img = Image.open(io.BytesIO(img_bytes))
            texto += pytesseract.image_to_string(img, lang='eng+spa+dan+deu+fra') + "\n"
        return texto.strip()
    except Exception as e:
        print(f"❌ Error OCR en {pdf_path}: {e}")
        return ""