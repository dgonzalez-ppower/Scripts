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

	# PyPDF2 3.x usa .outline en lugar de .outlines
	try:
		outlines = reader.outline
	except Exception as e:
		messagebox.showerror("Error", f"No se pudieron leer los bookmarks: {e}")
		return []

	recorrer(outlines)
	return bookmarks



def limpiar_nombre(nombre):
	# Reemplaza cualquier carácter que no sea alfanumérico o guion bajo por "_"
	return re.sub(r'[\\/*?:"<>|]', '_', nombre)

def dividir_por_bookmarks(pdf_path):
	reader = PdfReader(pdf_path)
	bookmarks_raw = extraer_bookmarks(reader)
	
	if not bookmarks_raw:
		messagebox.showerror("Error", "No se encontraron bookmarks de nivel 0.")
		return

	bookmarks_raw.sort(key=lambda x: x[1])
	cover_page = None
	if bookmarks_raw[0][0].lower() == "cover":
		cover_page = bookmarks_raw[0][1]

	# Agrupar páginas por bookmark
	paginas_por_bm = {}
	n = len(bookmarks_raw)
	for i in range(n):
		nombre, pagina = bookmarks_raw[i]
		pagina_fin = len(reader.pages) if i == n - 1 else bookmarks_raw[i + 1][1]
		paginas = list(range(pagina, pagina_fin))
		if nombre not in paginas_por_bm:
			paginas_por_bm[nombre] = []
		paginas_por_bm[nombre].extend(paginas)

	# Base para nombres de archivo
	nombre_base = os.path.splitext(os.path.basename(pdf_path))[0]
	carpeta_salida = os.path.dirname(pdf_path)

	for nombre_bm, paginas in paginas_por_bm.items():
		writer = PdfWriter()

		if cover_page is not None and nombre_bm.lower() != "cover":
			writer.add_page(reader.pages[cover_page])

		for p in paginas:
			writer.add_page(reader.pages[p])

		nombre_limpio = limpiar_nombre(nombre_bm)
		nombre_archivo = f"{nombre_base}_{nombre_limpio}.pdf"
		salida_path = os.path.join(carpeta_salida, nombre_archivo)

		with open(salida_path, "wb") as f_out:
			writer.write(f_out)

	messagebox.showinfo("Éxito", f"PDFs generados correctamente en:\n{carpeta_salida}")

if __name__ == "__main__":
	ruta_pdf = seleccionar_pdf()
	if ruta_pdf:
		dividir_por_bookmarks(ruta_pdf)
