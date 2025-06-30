# Transferencia de QRs entre PDFs (individual o por lotes)
import fitz  # PyMuPDF
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from tkinter import Tk, filedialog, messagebox
import os

# Configuración
DPI = 400
MARGEN_QR_H = 0.075  # Margen horizontal
MARGEN_QR_V = 0.075  # Margen vertical

# Iniciar GUI y determinar modo
root = Tk()
root.withdraw()
messagebox.showinfo("Transferencia de QRs", "Selecciona un archivo escaneado (baja calidad) para modo individual. Si cancelas, se activará el modo por lotes.")

scanned_pdf_path = filedialog.askopenfilename(title="Selecciona PDF escaneado (baja calidad)", filetypes=[("PDF", "*.pdf")])

if scanned_pdf_path:
	# ----- MODO INDIVIDUAL -----
	hq_pdf_path = filedialog.askopenfilename(title="Selecciona PDF de alta calidad", filetypes=[("PDF", "*.pdf")])
	if not hq_pdf_path:
		messagebox.showinfo("Cancelado", "No se seleccionó el archivo de alta calidad.")
		exit()

	scanned_name = os.path.splitext(os.path.basename(scanned_pdf_path))[0]
	dest_folder = os.path.dirname(scanned_pdf_path)
	output_path = os.path.join(dest_folder, scanned_name + "_con_QRs_reemplazados.pdf")
	log_path = os.path.join(dest_folder, scanned_name + "_log_no_reemplazados.txt")

	pdf_pairs = [(scanned_pdf_path, hq_pdf_path, output_path, log_path)]

else:
	# ----- MODO POR LOTES -----
	scanned_dir = filedialog.askdirectory(title="Selecciona carpeta de PDFs escaneados")
	hq_dir = filedialog.askdirectory(title="Selecciona carpeta de PDFs de alta calidad")
	dest_dir = filedialog.askdirectory(title="Selecciona carpeta destino")

	pdf_pairs = []
	global_log = []

	for filename in os.listdir(scanned_dir):
		if not filename.lower().endswith(".pdf"):
			continue
		scanned_path = os.path.join(scanned_dir, filename)
		hq_path = os.path.join(hq_dir, filename)
		if not os.path.exists(hq_path):
			global_log.append(f"❌ {filename}: no se encontró PDF de alta calidad correspondiente.")
			continue
		output_path = os.path.join(dest_dir, filename.replace(".pdf", "_con_QRs_reemplazados.pdf"))
		log_path = os.path.join(dest_dir, filename.replace(".pdf", "_log_no_reemplazados.txt"))
		pdf_pairs.append((scanned_path, hq_path, output_path, log_path))

	if global_log:
		with open(os.path.join(dest_dir, "_log_global_no_procesados.txt"), "w", encoding="utf-8") as f:
			f.write("\n".join(global_log))

# ----- PROCESAMIENTO COMÚN -----
for scanned_pdf_path, hq_pdf_path, output_path, log_path in pdf_pairs:
	print(f"\nProcesando: {os.path.basename(scanned_pdf_path)}")

	hq_doc = fitz.open(hq_pdf_path)
	hq_qrs = {}
	for page_num in range(len(hq_doc)):
		page = hq_doc[page_num]
		pix = page.get_pixmap(dpi=DPI)
		img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
		if pix.n == 4:
			img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
		gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
		_, bin_img = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
		scale_x = page.rect.width / pix.width
		scale_y = page.rect.height / pix.height
		qr_codes = decode(bin_img)
		if qr_codes:
			qr = qr_codes[0]
			txt = qr.data.decode("utf-8")
			x, y, w, h = qr.rect
			rect = fitz.Rect(x * scale_x, y * scale_y, (x + w) * scale_x, (y + h) * scale_y)
			qr_pix = page.get_pixmap(clip=rect, dpi=DPI)
			rel_w = rect.width / page.rect.width
			rel_h = rect.height / page.rect.height
			hq_qrs[txt] = (qr_pix, rel_w, rel_h)
	hq_doc.close()

	scanned_doc = fitz.open(scanned_pdf_path)
	no_match_log = []

	for page_num in range(len(scanned_doc)):
		page = scanned_doc[page_num]
		pix = page.get_pixmap(dpi=DPI)
		img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
		if pix.n == 4:
			img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
		gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
		_, bin_img = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
		scale_x = page.rect.width / pix.width
		scale_y = page.rect.height / pix.height
		qr_codes = decode(bin_img)
		if not qr_codes:
			no_match_log.append(f"[Página {page_num + 1}] ❌ No se detectó QR escaneado.")
			continue
		qr = qr_codes[0]
		txt = qr.data.decode("utf-8")
		if txt not in hq_qrs:
			no_match_log.append(f"[Página {page_num + 1}] ⚠️ QR con texto '{txt}' no coincide con ninguno del HQ.")
			continue
		x, y, w, h = qr.rect
		target_rect = fitz.Rect(x * scale_x, y * scale_y, (x + w) * scale_x, (y + h) * scale_y)
		qr_pix, rel_w, rel_h = hq_qrs[txt]
		clean_rect = fitz.Rect(
			target_rect.x0 - MARGEN_QR_H,
			target_rect.y0 - MARGEN_QR_V,
			target_rect.x1 + MARGEN_QR_H,
			target_rect.y1 + MARGEN_QR_V
		)
		page.draw_rect(clean_rect, fill=(1, 1, 1), color=(1, 1, 1), overlay=True)
		page.insert_image(target_rect, pixmap=qr_pix, overlay=True)

	scanned_doc.save(output_path)
	scanned_doc.close()

	if no_match_log:
		with open(log_path, "w", encoding="utf-8") as f:
			f.write("\n".join(no_match_log))
		print(f"Se creó log por errores: {log_path}")
	else:
		print("✅ Completado sin errores.")

messagebox.showinfo("Finalizado", "Proceso de transferencia de QRs completado.")
