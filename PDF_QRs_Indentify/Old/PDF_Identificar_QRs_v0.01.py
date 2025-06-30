import fitz  # PyMuPDF
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from tkinter import Tk, filedialog, messagebox

# Configuración
DPI = 400

# GUI para seleccionar PDF
root = Tk()
root.withdraw()
pdf_path = filedialog.askopenfilename(title="Selecciona un archivo PDF", filetypes=[("PDF", "*.pdf")])
if not pdf_path:
	messagebox.showinfo("Cancelado", "No se seleccionó ningún archivo.")
	exit()

output_path = pdf_path.replace(".pdf", "_con_qr_y_texto.pdf")

# Abre el documento
doc = fitz.open(pdf_path)

for page_num in range(len(doc)):
	page = doc[page_num]
	pix = page.get_pixmap(dpi=DPI)

	# Obtener tamaño real del PDF en puntos
	page_width_pdf, page_height_pdf = page.rect.width, page.rect.height

	# Convertir imagen a array de OpenCV
	img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
	if pix.n == 4:
		img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

	# Escala entre imagen (pixeles) y PDF (puntos)
	scale_x = page_width_pdf / pix.width
	scale_y = page_height_pdf / pix.height

	# Preprocesamiento para mejor detección
	gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
	_, bin_img = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

	# Detectar QR
	qr_codes = decode(bin_img)
	print(f"[Página {page_num + 1}] Códigos QR detectados: {len(qr_codes)}")

	for qr in qr_codes:
		x, y, w, h = qr.rect
		data = qr.data.decode("utf-8")

		# Convertimos de pixeles (imagen) a puntos (PDF)
		rect = fitz.Rect(
			x * scale_x,
			y * scale_y,
			(x + w) * scale_x,
			(y + h) * scale_y
		)
		page.draw_rect(rect, color=(1, 0, 0), width=2)

		# Posicionar el texto a la derecha del rectángulo del QR
		text_x = rect.x1 + 5  # Un poco a la derecha del borde
		text_y = rect.y0      # Alineado arriba

		# Dibujar el contenido del QR como texto en el PDF
		page.insert_text(
			fitz.Point(text_x, text_y),
			data,
			fontsize=8,
			color=(0, 0, 1),  # Azul para diferenciar
			overlay=True
		)

# Guardar documento nuevo
doc.save(output_path)
doc.close()

messagebox.showinfo("¡Hecho!", f"PDF generado con texto:\n{output_path}")
