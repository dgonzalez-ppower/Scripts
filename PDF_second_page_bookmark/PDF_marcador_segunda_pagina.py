import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import Destination
from tqdm import tqdm

def seleccionar_archivo_excel():
	root = tk.Tk()
	root.withdraw()
	return filedialog.askopenfilename(
		title="Selecciona el archivo Excel de referencia",
		filetypes=[("Excel files", "*.xlsx")]
	)

def seleccionar_carpeta_pdfs():
	return filedialog.askdirectory(title="Selecciona la carpeta que contiene los PDFs")

def cargar_excel(path_excel):
	try:
		df = pd.read_excel(path_excel, engine='openpyxl', dtype=str)
		df = df.fillna('')  # Evitar valores NaN
		df_filtrado = df[
			(~df['ITPItems'].str.contains(',', na=False)) &
			(~df['QCForms'].str.contains(',', na=False))
		]
		return df_filtrado
	except Exception as e:
		messagebox.showerror("Error", f"No se pudo leer el Excel:\n{e}")
		return pd.DataFrame()

def generar_bookmark_text(row):
	itp_type = row['ITPType']
	itp_items = row['ITPItems']
	qcforms = row['QCForms']
	ultimos6 = qcforms[-6:] if len(qcforms) >= 6 else qcforms
	return f"{itp_type} / {itp_items} / {ultimos6}"

def procesar_pdfs(carpeta_pdfs, df_ref):
	pdfs = [f for f in os.listdir(carpeta_pdfs) if f.lower().endswith(".pdf")]
	if not pdfs:
		messagebox.showinfo("Sin PDFs", "No se encontraron archivos PDF en la carpeta.")
		return

	print("\n📦 Procesando PDFs...\n")

	for pdf_name in tqdm(pdfs, desc="Procesando PDFs"):
		base_name = os.path.splitext(pdf_name)[0]
		match = df_ref[df_ref['RfiNumber'] == base_name]

		if match.empty:
			continue

		row = match.iloc[0]
		path_pdf = os.path.join(carpeta_pdfs, pdf_name)

		try:
			reader = PdfReader(path_pdf)
			if len(reader.pages) < 2:
				continue  # Ignorar PDF con menos de 2 páginas

			writer = PdfWriter()
			for page in reader.pages:
				writer.add_page(page)

			texto_bookmark = generar_bookmark_text(row)
			nuevo_bm_insertado = False

			# Copiar bookmarks existentes y agregar el nuevo detrás de "Cover"
			try:
				for outline in reader.outline:
					if isinstance(outline, Destination):
						titulo = outline.title.strip()
						page_idx = reader.get_destination_page_number(outline)
						writer.add_outline_item(title=titulo, page_number=page_idx)

						if titulo.lower() == "cover" and not nuevo_bm_insertado:
							writer.add_outline_item(title=texto_bookmark, page_number=1)
							nuevo_bm_insertado = True
			except Exception as e:
				print(f"⚠️  Error copiando bookmarks en {pdf_name}: {e}")

			if not nuevo_bm_insertado:
				writer.add_outline_item(title=texto_bookmark, page_number=1)

			nuevo_nombre = os.path.splitext(pdf_name)[0] + "_marcado.pdf"
			salida_path = os.path.join(carpeta_pdfs, nuevo_nombre)
			with open(salida_path, "wb") as f_out:
				writer.write(f_out)

		except Exception as e:
			print(f"❌ Error con {pdf_name}: {e}")

	print("\n✅ Proceso completado.")

def main():
	path_excel = seleccionar_archivo_excel()
	if not path_excel:
		return

	carpeta_pdfs = seleccionar_carpeta_pdfs()
	if not carpeta_pdfs:
		return

	df_filtrado = cargar_excel(path_excel)
	if df_filtrado.empty:
		messagebox.showinfo("Sin resultados", "Ningún archivo cumple los filtros especificados.")
		return

	procesar_pdfs(carpeta_pdfs, df_filtrado)

if __name__ == "__main__":
	main()
