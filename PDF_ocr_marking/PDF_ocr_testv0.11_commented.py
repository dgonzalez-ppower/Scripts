import fitz  # PyMuPDF: Used for editing PDF files, including drawing shapes and saving.
import pytesseract  # Tesseract OCR: A tool that converts images of text into actual text.
from pdf2image import convert_from_path  # Converts PDF pages into images so they can be scanned by OCR.
from tkinter import Tk, filedialog  # GUI elements to let user pick a file via a dialog box.
import os
import re
import difflib
from collections import Counter

# === List of known reference codes that the script will try to find in the PDF using OCR ===
CANDIDATOS = [
	"70215-40-YQ_-QNQ-UTE-007",
	"70215-40-YQ_-QNQ-UTE-008",
	"70215-40-YQ_-QNQ-UTE-013",
	# ... (list continues)
	"70215-40-YQ_-QNQ-UTE-033",
]

# === HELPER FUNCTIONS ===

def parece_igual(cadena1, cadena2, umbral=0.85):
	"""
	Compares two strings and returns True if they are similar enough,
	based on a threshold (default is 85% similarity).
	"""
	ratio = difflib.SequenceMatcher(None, cadena1.strip(), cadena2.strip()).ratio()
	return ratio >= umbral

def pixel_rect_to_pdf(palabra, dpi):
	"""
	Converts a rectangle given in pixel coordinates (from OCR) to PDF coordinates.
	This is needed to draw accurately on the PDF page.
	"""
	scale = 72 / dpi
	x0 = palabra['x'] * scale
	y0 = palabra['y'] * scale
	x1 = (palabra['x'] + palabra['w']) * scale
	y1 = (palabra['y'] + palabra['h']) * scale
	return fitz.Rect(x0, y0, x1, y1)

def reconstruir_cadena(centro, palabras, direccion, valor_objetivo, tolerancia_altura=15, max_palabras=6, distancia_max=300):
	"""
	Attempts to rebuild a multi-word string near a slash ("/") character by scanning to the left or right.
	Used when OCR splits identifiers across multiple words.
	"""
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
			else:
				match = palabra["text"] + match
			grupo.append(palabra)

			if parece_igual(match, valor_objetivo):
				return grupo
			if len(grupo) >= max_palabras:
				break
	return None

def detectar_actividad_ppi_desde_texto(texto):
	"""
	Searches for specific keywords (like 'PPI') in the text using a regex pattern.
	Tries to extract a code that usually follows 'actividad(es)' and 'PPI'.
	"""
	patron = r"actividad\(es\).*?PPI[:：]?\s*([A-Z0-9\-_/.]+)"
	match = re.search(patron, texto, re.IGNORECASE)
	return match.group(1).strip() if match else None

def extraer_texto_pytesseract(image, config=""):
	"""
	Runs Tesseract OCR on an image and returns the detected text.
	Optionally, a config string can be passed for specific OCR modes.
	"""
	return pytesseract.image_to_string(image, config=config)

def determinar_actividad_por_mayoria(imagen):
	"""
	Runs OCR on the first page image multiple times using different settings,
	then returns the most common detected activity code if any.
	"""
	resultados = []

	print("🔎 OCR normal...")
	text1 = extraer_texto_pytesseract(imagen)
	r1 = detectar_actividad_ppi_desde_texto(text1)
	if r1:
		resultados.append(r1)

	print("🔎 OCR mode PSM 6...")
	text2 = extraer_texto_pytesseract(imagen, config="--psm 6")
	r2 = detectar_actividad_ppi_desde_texto(text2)
	if r2:
		resultados.append(r2)

	print("🔎 OCR mode PSM 11...")
	text3 = extraer_texto_pytesseract(imagen, config="--psm 11")
	r3 = detectar_actividad_ppi_desde_texto(text3)
	if r3:
		resultados.append(r3)

	if not resultados:
		print("❌ No activity code found in any OCR pass.")
		return None

	# Vote: if the same result appears twice or more, consider it a valid match
	votos = Counter(resultados)
	ganador, cantidad = votos.most_common(1)[0]
	if cantidad >= 2:
		print(f"✅ Majority vote picked activity: {ganador}")
		return ganador
	else:
		print("❌ No consensus reached.")
		return None

def es_tamano_a3_o_mayor(pagina):
	"""
	Skip pages that are too large (e.g. A3 size or bigger).
	This helps to exclude special pages or schematics that aren't meant to be processed.
	"""
	width, height = pagina.rect.width, pagina.rect.height
	return width >= 842 or height >= 1190

def seleccionar_pdf():
	"""
	Opens a file selection dialog to allow the user to choose a PDF file to process.
	"""
	root = Tk()
	root.withdraw()
	return filedialog.askopenfilename(title="Select a PDF", filetypes=[("PDF", "*.pdf")])

# === MAIN FUNCTION: applies OCR and highlights on PDF ===
def marcar_textos_y_ppi_actividad(pdf_path, textos_objetivo, output_pdf_path, dpi=300):
	"""
	Main processing function that scans a PDF and highlights certain texts using OCR.
	Red highlights for direct matches with known codes.
	Green highlights for inferred or detected codes.
	"""
	doc = fitz.open(pdf_path)  # Open the PDF file for editing

	# Extract image of first page to determine main activity code
	print("📄 Scanning first page for activity code...")
	primera_img = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)[0]
	actividad_ppi_valor = determinar_actividad_por_mayoria(primera_img)
	ppi_valor = textos_objetivo[0]  # Expected known string to match directly

	# Convert all pages to images for OCR
	images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=len(doc), fmt='ppm')

	# Iterate through each page of the PDF
	for i, page in enumerate(doc):
		page_num = i + 1

		# Skip large pages (likely not standard documents)
		if es_tamano_a3_o_mayor(page):
			print(f"⚠️ Skipping oversized page {page_num}.")
			continue

		print(f"📄 Processing page {page_num}...")
		image = images[i]  # Get the image version of the current page

		# Run OCR on this page and collect all words with their coordinates
		ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
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

		# RED HIGHLIGHT: Try to match known PPI code directly
		rojo_detectado = False
		for palabra in palabras:
			if parece_igual(palabra["text"], ppi_valor):
				rect = pixel_rect_to_pdf(palabra, dpi)
				page.draw_rect(rect, color=(1, 0, 0), width=1.5)
				rojo_detectado = True
				print(f"🟥 Found red match: '{palabra['text']}' on page {page_num}")

		# GREEN HIGHLIGHT: Try to match inferred activity
		verde_detectado = False
		if actividad_ppi_valor:
			for palabra in palabras:
				if parece_igual(palabra["text"], actividad_ppi_valor):
					rect = pixel_rect_to_pdf(palabra, dpi)
					page.draw_rect(rect, color=(0, 1, 0), width=1.5)
					verde_detectado = True

		# Look for slashes and try fuzzy reconstruction left and right
		slash_words = [w for w in palabras if w["text"] == "/"]
		for slash in slash_words:
			if not verde_detectado and actividad_ppi_valor:
				grupo_verde = reconstruir_cadena(slash, palabras, "derecha", actividad_ppi_valor)
				if grupo_verde:
					for palabra in grupo_verde:
						rect = pixel_rect_to_pdf(palabra, dpi)
						page.draw_rect(rect, color=(0, 1, 0), width=1.5)
					print(f"🧩 Fuzzy GREEN match reconstructed on page {page_num}")

			if not rojo_detectado and ppi_valor:
				grupo_rojo = reconstruir_cadena(slash, palabras, "izquierda", ppi_valor)
				if grupo_rojo:
					for palabra in grupo_rojo:
						rect = pixel_rect_to_pdf(palabra, dpi)
						page.draw_rect(rect, color=(1, 0, 0), width=1.5)
					print(f"🧩 Fuzzy RED match reconstructed on page {page_num}")

	# Save the modified PDF with all highlighted matches
	doc.save(output_pdf_path)
	print(f"\n✅ Output saved as: {output_pdf_path}")

# === ENTRY POINT ===
print("📌 Please select a PDF file to scan...")
pdf_path = seleccionar_pdf()
if not pdf_path:
	print("🚫 No file selected. Exiting.")
	exit()

pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
output_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_marked.pdf")

print("🚀 Beginning full scan and mark process...")
marcar_textos_y_ppi_actividad(pdf_path, CANDIDATOS, output_pdf_path)
