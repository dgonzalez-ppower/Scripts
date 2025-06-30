import re
import os
import fitz
import pytesseract
from pytesseract import Output
from deep_translator import GoogleTranslator
from langdetect import detect
import io
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
import tkinter as tk
from tkinter import filedialog, messagebox
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image

# ---------- FUNCIONES CORE OCR + TRADUCCIÓN ----------

export_words_coords = []
export_lines_coords = []
export_translated_lines = []

def is_scanned(pdf_path):
    with fitz.open(pdf_path) as doc:
        for page in doc:
            if page.get_text().strip():
                return False
    return True

def run_ocr_by_coordinates(pdf_path):
    doc = fitz.open(pdf_path)
    pages_data = []
    for page_num, page in enumerate(doc, start=1):
        print(f"🧾 OCR: Procesando página {page_num} de {len(doc)}...")
        try:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        except Exception as e:
            print(f"[ERROR] Fallo al convertir pixmap a imagen: {e}")
            continue
        data = pytesseract.image_to_data(img, output_type=Output.DICT, lang='deu+eng+spa+dan+nor')
        pages_data.append(data)

    return pages_data

def run_ocr_by_lines(pdf_path):
    doc = fitz.open(pdf_path)
    pages_text = []
    for page_num, page in enumerate(doc, start=1):
        print(f"🧾 OCR: Procesando página {page_num} de {len(doc)}...")
        pix = page.get_pixmap(dpi=300)
        img = pix.tobytes("png")
        text = pytesseract.image_to_string(img, lang='deu+eng+spa+dan+nor')

        raw_lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        fused_lines = []
        i = 0

        # Expresiones típicas de encabezados
        index_pattern = re.compile(r"^(?:\d{1,2}(?:\.\d{1,2})?|[Cc]ap[ií]tulo\s+\d+|[Aa]rt[íi]culo\s+\d+)$")

        while i < len(raw_lines):
            current = raw_lines[i]
            next_line = raw_lines[i + 1] if i + 1 < len(raw_lines) else ""

            if index_pattern.match(current) and next_line:
                # Fusionar índice + contenido
                fused_lines.append(f"{current} {next_line}")
                i += 2
            elif (
                i + 1 < len(raw_lines)
                and len(current.split()) <= 2
                and current[-1] not in ".:;"
                and len(next_line.split()) >= 2
            ):
                # Heurística alternativa para líneas cortas seguidas de contenido
                fused_lines.append(f"{current} {next_line}")
                i += 2
            else:
                fused_lines.append(current)
                i += 1

        pages_text.append(fused_lines)
            
    return pages_text

def run_ocr_by_visual_lines(pdf_path, y_tolerance=5):
    
    global export_words_coords, export_lines_coords, export_translated_lines
    
    doc = fitz.open(pdf_path)
    pages_text = []

    for page_num, page in enumerate(doc, start=1):
        print(f"🧾 OCR visual: Procesando página {page_num} de {len(doc)}...")
        pix = page.get_pixmap(dpi=300, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        data = pytesseract.image_to_data(img, output_type=Output.DICT, lang='deu+eng+spa+dan+nor')

        words = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text:
                word = {
                    'text': text,
                    'left': data['left'][i],
                    'top': data['top'][i]
                }
                words.append(word)
                export_words_coords.append(f"Page {page_num}\t{text}\tLEFT={word['left']}\tTOP={word['top']}")

        lines = []
        for word in sorted(words, key=lambda x: x['top']):
            placed = False
            for line in lines:
                if abs(word['top'] - line['top']) <= y_tolerance:
                    line['words'].append(word)
                    placed = True
                    break
            if not placed:
                lines.append({'top': word['top'], 'words': [word]})

        result_lines = []
        for line in lines:
            sorted_words = sorted(line['words'], key=lambda x: x['left'])
            text_line = ' '.join(w['text'] for w in sorted_words)
            top_line = min(w['top'] for w in line['words'])
            result_lines.append({'text': text_line, 'top': top_line})
            export_lines_coords.append(f"Page {page_num}\tY≈{top_line}\t{text_line}")

        pages_text.append(result_lines)

    return pages_text

def translate_lines_by_page(pages_text):
    """
    Translate every visual-OCR line to Spanish while keeping the original TOP
    coordinate.  Robust against Google Translate returning None or raising.
    """
    translated_pages = []

    for page_num, lines in enumerate(pages_text, start=1):
        print(f"🌐 Traduciendo página {page_num} de {len(pages_text)}…")

        # quick language sniff – skip pages that are already ES / EN
        try:
            lang_sample = detect(" ".join(l["text"] for l in lines))
        except Exception:
            lang_sample = "und"

        if lang_sample in ("es", "en"):
            print(f"↪ Página {page_num} ya en {lang_sample.upper()}.")
            translated_pages.append([])      # keep page empty
            continue

        page_out = []

        for line in lines:
            src_text = line["text"] or ""        # never None
            tgt_text = None

            # ---------- 1) translate ---------------------------------------------------
            try:
                tgt_text = GoogleTranslator(source="auto", target="es").translate(src_text)
            except Exception as e:
                print(f"⚠️  Fallo al traducir «{src_text[:25]}…»: {e}")

            if not tgt_text:                      # covers None or ""
                tgt_text = src_text               # graceful fallback

            # ---------- 2) normalise --------------------------------------------------
            tgt_text = str(tgt_text)              # make absolutely sure it’s a string
            flat = " ".join(
                seg.strip() for seg in tgt_text.replace("\r", "").splitlines() if seg.strip()
            )

            page_out.append({"text": flat, "top": line["top"]})

        translated_pages.append(page_out)

    return translated_pages


def translate_lines_by_page(pages_text):
    translated_pages = []

    for page_num, lines in enumerate(pages_text, start=1):
        print(f"🌐 Traduciendo página {page_num} de {len(pages_text)}...")

        # Detección de idioma para toda la página
        try:
            full_text = " ".join(l.get("text", "") for l in lines)
            lang = detect(full_text)
        except:
            lang = "und"

        if lang in ["es", "en"]:
            print(f"↪ Página {page_num} ya en {lang.upper()}. Se omite.")
            translated_pages.append([])
            continue

        translated_lines = []

        for line in lines:
            original_text = line.get("text", "") or ""
            translated_text = None

            try:
                translated_text = GoogleTranslator(source="auto", target="es").translate(original_text)
            except Exception as e:
                print(f"⚠️ Error al traducir línea «{original_text[:30]}…»: {e}")

            # Asegurar que traducido sea string válido
            if not translated_text:
                translated_text = original_text

            # 🔐 Bloque robusto contra None:
            if not isinstance(translated_text, str):
                translated_text = str(translated_text)

            try:
                clean_text = " ".join(
                    seg.strip() for seg in translated_text.replace("\r", "").splitlines() if seg.strip()
                )
            except Exception as e:
                print(f"🚨 FALLO al procesar línea traducida: {translated_text} — {e}")
                clean_text = original_text

            translated_lines.append({
                "text": clean_text,
                "top": line.get("top", 50)
            })

        translated_pages.append(translated_lines)

    return translated_pages

def create_overlay_from_words(translated_pages, original_pdf_path, overlay_path):
    doc = fitz.open(original_pdf_path)
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(doc[0].rect.width, doc[0].rect.height))
    for page_num, words in enumerate(translated_pages):
        for word in words:
            x = word['left']
            y = doc[page_num].rect.height - word['top']
            c.setFont("Helvetica", 6)
            c.drawString(x, y, word['text'])
        c.showPage()
    c.save()
    packet.seek(0)
    with open(overlay_path, "wb") as f:
        f.write(packet.read())

def merge_overlay(original_pdf, overlay_pdf, output_pdf):
    original = PdfReader(original_pdf)
    overlay = PdfReader(overlay_pdf)
    writer = PdfWriter()
    for i in range(len(original.pages)):
        base = original.pages[i]
        if i < len(overlay.pages):
            base.merge_page(overlay.pages[i])
        writer.add_page(base)
    with open(output_pdf, "wb") as f:
        writer.write(f)

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])

def create_translation_pages(translated_pages, output_path, original_pdf_path):
    print("📄 Creando PDF de traducciones en memoria...")

    original = PdfReader(original_pdf_path)
    writer = PdfWriter()

    for i, original_page in enumerate(original.pages):
        writer.add_page(original_page)

        if i >= len(translated_pages) or not translated_pages[i]:
            continue

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica", 10)

        y = A4[1] - 50  # comenzar desde arriba (margen superior)
        line_height = 14  # espacio vertical entre líneas
        
        for line in translated_pages[i]:
            if y < 50:  # margen inferior
                c.showPage()
                c.setFont("Helvetica", 10)
                y = A4[1] - 50
            c.drawString(40, y, line['text'][:120])
            export_translated_lines.append(f"Page {i+1}\tY≈{int(line['top'])}\t{line['text']}")
            y -= line_height

        c.showPage()
        c.save()
        buffer.seek(0)

        translated_reader = PdfReader(buffer)
        for page in translated_reader.pages:
            writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"✅ PDF final guardado en: {output_path}")
    
    translated_txt_path = os.path.join(
        os.path.dirname(output_path),
        f"{os.path.splitext(os.path.basename(output_path))[0]}_translated_lines.txt"
    )
    with open(translated_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(export_translated_lines))

    print(f"📝 Guardado TXT de líneas traducidas en: {translated_txt_path}")
        

def process_pdf_precise_translation(input_pdf):
    print("📥 Abriendo PDF...")

    folder = os.path.dirname(input_pdf)
    filename = os.path.splitext(os.path.basename(input_pdf))[0]
    output_pdf = os.path.join(folder, filename + "_es.pdf")

    print("🔍 Detectando si el PDF está escaneado...")

    if is_scanned(input_pdf):
        print("📸 PDF escaneado. Aplicando OCR con coordenadas...")
        data = run_ocr_by_visual_lines(input_pdf)

        print("🧠 Traduciendo palabra por palabra...")
        translated = translate_lines_by_page(data)

        print("📄 Generando páginas traducidas intercaladas...")
        create_translation_pages(translated, output_pdf, input_pdf)

        print(f"✅ PDF traducido generado: {output_pdf}")
        return output_pdf

    else:
        print("📝 PDF ya tiene texto. Ejecutando OCR visual para respetar disposición...")

        # Ejecutar OCR visual para obtener líneas con coordenadas reales
        ocr_visual_lines = run_ocr_by_visual_lines(input_pdf)

        # Exportar los TXT auxiliares como hasta ahora
        coords_txt_path = os.path.join(folder, f"{filename}_ocr_coords.txt")                
        lines_txt_path = os.path.join(folder, f"{filename}_ocr_lines.txt")

        print(f"[DEBUG] export_words_coords total: {len(export_words_coords)}")
        print(f"[DEBUG] export_lines_coords total: {len(export_lines_coords)}")

        with open(coords_txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(export_words_coords))

        with open(lines_txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(export_lines_coords))

        print(f"📝 Guardado TXT OCR con coordenadas en: {coords_txt_path}")
        print(f"📝 Guardado TXT OCR con líneas fusionadas en: {lines_txt_path}")

        # Traducir línea por línea con preservación de altura
        print("🧠 Traduciendo línea por línea con conservación de altura...")
        translated_pages = translate_lines_by_page(ocr_visual_lines)

        # Generar el PDF final con páginas traducidas
        print("📄 Generando páginas traducidas intercaladas...")
        create_translation_pages(translated_pages, output_pdf, input_pdf)

        print(f"✅ PDF traducido generado: {output_pdf}")
        return output_pdf

# ---------- GUI ----------

def select_and_process_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if not file_path:
        return
    try:
        result_path = process_pdf_precise_translation(file_path)
        if result_path:
            messagebox.showinfo("Éxito", f"PDF traducido creado:\n{result_path}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

root = tk.Tk()
root.title("OCR + Traducción a Español")
root.geometry("400x150")
tk.Label(root, text="Selecciona un archivo PDF escaneado para traducirlo al español", wraplength=350, pady=20).pack()
tk.Button(root, text="Seleccionar PDF", command=select_and_process_file, width=20, height=2).pack()
root.mainloop()
