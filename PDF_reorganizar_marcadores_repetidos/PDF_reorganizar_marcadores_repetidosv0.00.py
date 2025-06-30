import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter

def seleccionar_pdf():
	root = tk.Tk()
	root.withdraw()
	return filedialog.askopenfilename(
		title="Selecciona un archivo PDF",
		filetypes=[("Archivos PDF", "*.pdf")]
	)

def extraer_bookmarks(reader):
	bookmarks = []

	def recorrer(outlines):
		for item in outlines:
			if isinstance(item, list):
				recorrer(item)
			else:
				try:
					page_number = reader.get_destination_page_number(item)
					bookmarks.append((item.title.strip(), page_number))
				except Exception as e:
					print(f"Error procesando bookmark: {e}")

	# PyPDF2 3.x usa .outline
	try:
		outlines = reader.outline
	except Exception as e:
		messagebox.showerror("Error", f"No se pudieron leer los bookmarks: {e}")
		return []

	recorrer(outlines)
	return bookmarks

def limpiar_nombre(nombre):
	return re.sub(r'[\\/*?:"<>|]', '_', nombre)

def reconstruir_pdf(pdf_path):
	reader = PdfReader(pdf_path)
	bookmarks_raw = extraer_bookmarks(reader)

	if not bookmarks_raw:
		messagebox.showerror("Error", "No se encontraron bookmarks.")
		return

	bookmarks_raw.sort(key=lambda x: x[1])

	# Identificar portada si existe
	cover_page = None
	if bookmarks_raw[0][0].lower() == "cover":
		cover_page = bookmarks_raw[0][1]

	# Agrupar páginas por bookmark
	paginas_por_bm = {}
	n = len(bookmarks_raw)
	for i in range(n):
		nombre, pagina = bookmarks_raw[i]
		pagina_fin = len(reader.pages) if i == n - 1 else bookmarks_raw[i + 1][1]
		rango_paginas = list(range(pagina, pagina_fin))
		if nombre.lower() != "cover":
			if nombre not in paginas_por_bm:
				paginas_por_bm[nombre] = []
			paginas_por_bm[nombre].extend(rango_paginas)

	# Reconstruir PDF
	writer = PdfWriter()
	pagina_indices_map = {}  # nombre_bm: índice_inicio_en_writer

	if cover_page is not None:
		writer.add_page(reader.pages[cover_page])
		pagina_indices_map["Cover"] = 0

	for nombre, paginas in paginas_por_bm.items():
		pagina_indices_map[nombre] = len(writer.pages)
		for p in paginas:
			writer.add_page(reader.pages[p])

	# Agregar marcadores
	for nombre, indice in pagina_indices_map.items():
		writer.add_outline_item(title=nombre, page_number=indice)

	# Guardar
	nombre_base = os.path.splitext(os.path.basename(pdf_path))[0]
	nombre_salida = os.path.join(os.path.dirname(pdf_path), f"{nombre_base}_reordenado.pdf")
	with open(nombre_salida, "wb") as f_out:
		writer.write(f_out)

	messagebox.showinfo("Éxito", f"PDF reordenado creado:\n{nombre_salida}")

if __name__ == "__main__":
	ruta_pdf = seleccionar_pdf()
	if ruta_pdf:
		reconstruir_pdf(ruta_pdf)
