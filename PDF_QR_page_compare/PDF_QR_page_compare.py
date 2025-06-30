import os
import fitz  # PyMuPDF
from pyzbar.pyzbar import decode
from PIL import Image
import pandas as pd
from io import BytesIO
from tkinter import Tk, filedialog, messagebox, Button, Label

def extraer_qrs_pdf(ruta_pdf):
	qrs_por_pagina = {}
	ilegibles = set()

	with fitz.open(ruta_pdf) as doc:
		for num_pagina, pagina in enumerate(doc, start=1):
			pix = pagina.get_pixmap(dpi=200)
			img = Image.open(BytesIO(pix.tobytes('png')))
			decoded = decode(img)

			if not decoded:
				continue  # No hay QR

			try:
				qr = decoded[0].data.decode('utf-8')
				qrs_por_pagina[num_pagina] = qr
			except Exception:
				ilegibles.add(num_pagina)

	return qrs_por_pagina, ilegibles

def comparar_qrs(qrs_a, qrs_b):
	valores_a = set(qrs_a.values())
	valores_b = set(qrs_b.values())

	no_en_b = [pag for pag, qr in qrs_a.items() if qr not in valores_b]
	no_en_a = [pag for pag, qr in qrs_b.items() if qr not in valores_a]

	return no_en_b, no_en_a

def obtener_pdf_comunes(path_a, path_b):
	archivos_a = set(os.listdir(path_a))
	archivos_b = set(os.listdir(path_b))
	return sorted(list(archivos_a & archivos_b))

def seleccionar_carpeta_a():
	global carpeta_a
	carpeta_a = filedialog.askdirectory(title="Selecciona carpeta A")
	label_a.config(text=f"📁 Carpeta A: {carpeta_a}")

def seleccionar_carpeta_b():
	global carpeta_b
	carpeta_b = filedialog.askdirectory(title="Selecciona carpeta B")
	label_b.config(text=f"📁 Carpeta B: {carpeta_b}")

def ejecutar_comparacion():
	if not carpeta_a or not carpeta_b:
		messagebox.showerror("Error", "Debes seleccionar ambas carpetas")
		return

	resultados = []
	pdfs_comunes = obtener_pdf_comunes(carpeta_a, carpeta_b)

	if not pdfs_comunes:
		messagebox.showinfo("Sin coincidencias", "No hay archivos PDF con el mismo nombre en ambas carpetas.")
		return

	for nombre_pdf in pdfs_comunes:
		ruta_pdf_a = os.path.join(carpeta_a, nombre_pdf)
		ruta_pdf_b = os.path.join(carpeta_b, nombre_pdf)

		print(f"Comparando: {nombre_pdf}")

		qrs_a, ilegibles_a = extraer_qrs_pdf(ruta_pdf_a)
		qrs_b, ilegibles_b = extraer_qrs_pdf(ruta_pdf_b)

		no_en_b, no_en_a = comparar_qrs(qrs_a, qrs_b)

		for pag in no_en_b:
			resultados.append([nombre_pdf, pag, "", ""])

		for pag in no_en_a:
			resultados.append(["", "", nombre_pdf, pag])

		for pag in ilegibles_a:
			resultados.append([nombre_pdf, f"{pag} (QR ilegible)", "", ""])

		for pag in ilegibles_b:
			resultados.append(["", "", nombre_pdf, f"{pag} (QR ilegible)"])

	df = pd.DataFrame(resultados, columns=[
		"Nombre PDF carpeta A",
		"Página PDF carpeta A que no está en B",
		"Nombre PDF carpeta B",
		"Página PDF carpeta B que no está en A"
	])

	ruta_excel = os.path.join(carpeta_a, "comparacion_qr_resultado.xlsx")
	df.to_excel(ruta_excel, index=False)

	messagebox.showinfo("Listo", f"✅ Comparación completada.\nExcel guardado en:\n{ruta_excel}")

# GUI
carpeta_a = ""
carpeta_b = ""

ventana = Tk()
ventana.title("Comparador de PDFs por QR")
ventana.geometry("500x250")

Label(ventana, text="Selecciona las carpetas con los PDFs a comparar", font=("Segoe UI", 12)).pack(pady=10)

Button(ventana, text="Seleccionar Carpeta A", command=seleccionar_carpeta_a, width=30).pack(pady=5)
label_a = Label(ventana, text="📁 Carpeta A: No seleccionada", wraplength=450)
label_a.pack()

Button(ventana, text="Seleccionar Carpeta B", command=seleccionar_carpeta_b, width=30).pack(pady=5)
label_b = Label(ventana, text="📁 Carpeta B: No seleccionada", wraplength=450)
label_b.pack()

Button(ventana, text="🔍 Ejecutar Comparación", command=ejecutar_comparacion, width=30, bg="lightblue").pack(pady=20)

ventana.mainloop()
