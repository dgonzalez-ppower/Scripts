from tkinter import simpledialog, Label, Button  # además del resto que ya tienes
from tkinter import Tk


def seleccionar_pdf():
	"""
	Abre un cuadro de diálogo para seleccionar un archivo PDF.
	"""
	root = Tk()
	root.withdraw()
	return filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")])

# Función para solicitar 3 textos desde un GUI
def obtener_textos_usuario():
	root = Tk()
	root.title("Ingresar textos a buscar")
	root.geometry("400x250")

	textos = []

	labels = [
		("Texto 1 (🔴 Rojo):", "🔴"),
		("Texto 2 (🟢 Verde):", "🟢"),
		("Texto 3 (🔵 Azul claro):", "🔵")
	]

	entries = []

	for i, (label_text, _) in enumerate(labels):
		lbl = Label(root, text=label_text)
		lbl.pack(pady=5)
		entry = simpledialog.Entry(root, width=50)
		entry.pack(pady=2)
		entries.append(entry)

	def submit():
		for e in entries:
			textos.append(e.get().strip())
		root.destroy()

	btn = Button(root, text="Aceptar", command=submit)
	btn.pack(pady=20)

	root.mainloop()
	return textos

# Colores por texto: rojo, verde, azul claro
COLORES_RGB = [(1, 0, 0), (0, 1, 0), (0.3, 0.7, 1)]  # RGB para fitz

# Reemplaza la parte final de tu script por esto:
print("📌 Selecciona un archivo PDF...")
pdf_path = seleccionar_pdf()
if not pdf_path:
	print("🚫 No se seleccionó archivo. Fin del programa.")
	exit()

print("📝 Introduce hasta 3 textos que deseas buscar...")
textos_usuario = obtener_textos_usuario()

# Rellena textos vacíos si el usuario puso menos de 3
while len(textos_usuario) < 3:
	textos_usuario.append("")

pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
output_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_marked.pdf")

print("🚀 Comenzando escaneo y marcado del PDF...")
marcar_textos_y_colorear(pdf_path, textos_usuario, output_pdf_path)

# Cambia la función de marcado original por esto:
def marcar_textos_y_colorear(pdf_path, textos_objetivo, output_pdf_path, dpi=300):
	doc = fitz.open(pdf_path)
	images = convert_from_path(pdf_path, dpi=dpi, fmt='ppm')

	for i, page in enumerate(doc):
		if es_tamano_a3_o_mayor(page):
			continue

		image = images[i]
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

		for idx, objetivo in enumerate(textos_objetivo):
			if not objetivo:
				continue
			for palabra in palabras:
				if parece_igual(palabra["text"], objetivo):
					rect = pixel_rect_to_pdf(palabra, dpi)
					page.draw_rect(rect, color=COLORES_RGB[idx], width=1.5)
					print(f"🎯 Texto {idx+1} encontrado: '{palabra['text']}' en página {i+1}")

	doc.save(output_pdf_path)
	print(f"\n✅ PDF guardado con resultados: {output_pdf_path}")
