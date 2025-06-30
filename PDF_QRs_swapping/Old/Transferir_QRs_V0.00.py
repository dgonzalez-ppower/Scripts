# Paso 1: Extraer QRs desde PDF de alta calidad
import fitz  # PyMuPDF
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from tkinter import Tk, filedialog, messagebox
import os

# Configuración
DPI = 400

# GUI para seleccionar PDF de alta calidad
root = Tk()
root.withdraw()
hq_pdf_path = filedialog.askopenfilename(title="Selecciona PDF de alta calidad", filetypes=[("PDF", "*.pdf")])
if not hq_pdf_path:
	messagebox.showinfo("Cancelado", "No se seleccionó ningún archivo.")
	exit()

# GUI para seleccionar PDF escaneado (baja calidad)
scanned_pdf_path = filedialog.askopenfilename(title="Selecciona PDF escaneado (baja calidad)", filetypes=[("PDF", "*.pdf")])
if not scanned_pdf_path:
	messagebox.showinfo("Cancelado", "No se seleccionó el PDF escaneado.")
	exit()

output_path = scanned_pdf_path.replace(".pdf", "_con_QRs_reemplazados.pdf")
log_path = scanned_pdf_path.replace(".pdf", "_log_no_reemplazados.txt")

# ---------- FASE 1: Extraer QRs y textos del PDF de alta calidad ----------
print("Extrayendo QRs del PDF de alta calidad...")
hq_doc = fitz.open(hq_pdf_path)
hq_qrs = {}  # {texto: (pixmap, width_rel, height_rel)}

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
		print(f"[HQ Página {page_num + 1}] QR capturado con texto: {txt}")
hq_doc.close()

# ---------- FASE 2: Detectar QRs en PDF escaneado y reemplazar por coincidencia de texto ----------
print("\nInsertando QRs originales en el PDF escaneado por coincidencia de texto...")
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
		msg = f"[Página {page_num + 1}] ❌ No se detectó QR escaneado."
		print(msg)
		no_match_log.append(msg)
		continue

	qr = qr_codes[0]
	txt = qr.data.decode("utf-8")
	if txt not in hq_qrs:
		msg = f"[Página {page_num + 1}] ⚠️ QR con texto '{txt}' no coincide con ninguno del HQ."
		print(msg)
		no_match_log.append(msg)
		continue

	x, y, w, h = qr.rect
	target_rect = fitz.Rect(x * scale_x, y * scale_y, (x + w) * scale_x, (y + h) * scale_y)
	qr_pix, rel_w, rel_h = hq_qrs[txt]

	page.insert_image(target_rect, pixmap=qr_pix, overlay=True)
	print(f"[Página {page_num + 1}] ✅ QR reemplazado por coincidencia de texto.")

# Guardar log si hay páginas sin reemplazo
if no_match_log:
	with open(log_path, "w", encoding="utf-8") as f:
		f.write("\n".join(no_match_log))
	print(f"\nSe creó un log con las páginas no reemplazadas: {log_path}")

# Guardar PDF final
scanned_doc.save(output_path)
scanned_doc.close()

messagebox.showinfo("¡Hecho!", f"PDF generado con QRs insertados por coincidencia de texto:\n{output_path}")
