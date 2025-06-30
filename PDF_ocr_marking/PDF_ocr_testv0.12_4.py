import fitz
import pytesseract
from pdf2image import convert_from_path
from tkinter import Tk, filedialog, simpledialog, Label, Button, Entry
import os
import difflib

def seleccionar_pdf():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")])

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

def es_tamano_a3_o_mayor(pagina):
    width, height = pagina.rect.width, pagina.rect.height
    return width >= 842 or height >= 1190

def obtener_textos_usuario():
    root = Tk()
    root.title("Ingresar textos a buscar")
    root.geometry("400x250")
    root.attributes("-topmost", True)

    textos = []
    labels = [
        ("Texto 1 (🔴 Rojo):", "🔴"),
        ("Texto 2 (🟢 Verde):", "🟢"),
        ("Texto 3 (🔵 Azul claro):", "🔵")
    ]
    entries = []

    for label_text, _ in labels:
        lbl = Label(root, text=label_text)
        lbl.pack(pady=5)
        entry = Entry(root, width=50)
        entry.pack(pady=2)
        entries.append(entry)

    def submit():
        for e in entries:
            textos.append(e.get().strip())
        root.destroy()

    btn = Button(root, text="Aceptar", command=submit)
    btn.pack(pady=20)

    root.mainloop()
    return textos

COLORES_RGB = [(1, 0, 0), (0, 1, 0), (0.3, 0.7, 1)]

def marcar_textos_stream(pdf_path, textos_objetivo, output_pdf_path, dpi=300):
    doc = fitz.open(pdf_path)
    total_paginas = len(doc)

    for i, page in enumerate(doc):
        print(f"➡️ Procesando página {i+1} de {total_paginas}...")

        if es_tamano_a3_o_mayor(page):
            print(f"⏩ Página {i+1} omitida (tamaño grande)")
            continue

        # Convertir solo esta página a imagen
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

print("📝 Introduce hasta 3 textos que deseas buscar...")
textos_usuario = obtener_textos_usuario()
print("📌 Textos ingresados:", textos_usuario)

while len(textos_usuario) < 3:
    textos_usuario.append("")

pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
output_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_marked.pdf")

print("🚀 Iniciando escaneo del PDF página por página...")
marcar_textos_stream(pdf_path, textos_usuario, output_pdf_path)
