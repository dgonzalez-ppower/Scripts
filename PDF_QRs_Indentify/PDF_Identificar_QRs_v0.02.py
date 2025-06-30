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

	# Insertar contenido del primer QR arriba del encabezado
	if qr_codes:
		first_qr_text = qr_codes[0].data.decode("utf-8")
		top_text_position = fitz.Point(50, 20)  # Muy arriba del documento
		page.insert_text(
			top_text_position,
			first_qr_text,
			fontsize=10,
			color=(1, 0, 0),  # Rojo para destacar
			overlay=True
		)

	for qr in qr_codes:
		x, y, w, h = qr.rect
		data = qr.data.decode("utf-8")

		# Convert pixels to PDF points
		rect = fitz.Rect(
			x * scale_x,
			y * scale_y,
			(x + w) * scale_x,
			(y + h) * scale_y
		)
		#page.draw_rect(rect, color=(1, 0, 0), width=2)

		# Prepare text box below the QR code
		text_x0 = rect.x0
		text_y0 = rect.y1 + 5  # 5 pts below QR
		text_width = 200       # Limit width for wrapping
		text_height = 30       # Initial height (can grow with wrapping)

		text_rect = fitz.Rect(text_x0, text_y0, text_x0 + text_width, text_y0 + text_height)

		# Draw a white background with transparency
		page.draw_rect(text_rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True, fill_opacity=0.8)

		# Add wrapped text inside the box
		#page.insert_textbox(
		#	text_rect,
		#	data,
		#	fontsize=8,
		#	color=(0, 0, 1),
		#	overlay=True,
		#	align=0  # Left-aligned
		#)

# Guardar documento nuevo
doc.save(output_path)
doc.close()

messagebox.showinfo("¡Hecho!", f"PDF generado con texto:\n{output_path}")