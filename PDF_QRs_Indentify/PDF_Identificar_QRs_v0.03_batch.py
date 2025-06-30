import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import re
from pyzbar.pyzbar import decode
from tkinter import Tk, filedialog, messagebox

DPI = 400

def process_pdf(pdf_path, output_folder):
	doc = fitz.open(pdf_path)

	for page_num in range(len(doc)):
		page = doc[page_num]
		pix = page.get_pixmap(dpi=DPI)

		img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
		if pix.n == 4:
			img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

		gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
		_, bin_img = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

		qr_codes = decode(bin_img)

		if qr_codes:
			first_qr_text = qr_codes[0].data.decode("utf-8")
			page.insert_text(
				fitz.Point(50, 20),
				first_qr_text,
				fontsize=10,
				color=(1, 0, 0),
				overlay=True
			)

	# Nombre de salida con sufijo _QR_marked
	doc_basename = os.path.splitext(os.path.basename(pdf_path))[0]
	output_filename = f"{doc_basename}_QR_marked.pdf"
	output_path = os.path.join(output_folder, output_filename)

	doc.save(output_path)
	doc.close()

def main():
	root = Tk()
	root.withdraw()

	source_folder = filedialog.askdirectory(title="Selecciona la carpeta de origen")
	if not source_folder:
		messagebox.showinfo("Cancelado", "No se seleccionó carpeta de origen.")
		return

	dest_folder = filedialog.askdirectory(title="Selecciona la carpeta de destino")
	if not dest_folder:
		messagebox.showinfo("Cancelado", "No se seleccionó carpeta de destino.")
		return

	pdf_files = [f for f in os.listdir(source_folder) if f.lower().endswith('.pdf')]
	if not pdf_files:
		messagebox.showinfo("Vacío", "No hay archivos PDF en la carpeta seleccionada.")
		return

	for pdf_file in pdf_files:
		full_path = os.path.join(source_folder, pdf_file)
		process_pdf(full_path, dest_folder)

	messagebox.showinfo("¡Hecho!", f"Se procesaron {len(pdf_files)} archivos PDF.")

if __name__ == "__main__":
	main()
