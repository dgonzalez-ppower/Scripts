import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfReader, PdfWriter

def process_pdfs(source_folder, dest_folder):
	for filename in os.listdir(source_folder):
		if filename.lower().endswith(".pdf"):
			source_path = os.path.join(source_folder, filename)
			reader = PdfReader(source_path)
			writer = PdfWriter()

			# Copiar páginas
			for page in reader.pages:
				writer.add_page(page)

			# Añadir marcador "Cover" a la primera página
			writer.add_outline_item("Cover", 0)

			# Guardar en carpeta destino
			output_path = os.path.join(dest_folder, filename)
			with open(output_path, "wb") as f_out:
				writer.write(f_out)

	messagebox.showinfo("Listo", "Se han creado los PDFs con marcador 'Cover' en la carpeta destino.")

def select_folders():
	messagebox.showinfo("Paso 1", "Selecciona la carpeta con los PDFs originales.")
	source_folder = filedialog.askdirectory(title="Carpeta de origen")

	if not source_folder:
		return

	messagebox.showinfo("Paso 2", "Selecciona la carpeta donde guardar los PDFs modificados.")
	dest_folder = filedialog.askdirectory(title="Carpeta de destino")

	if not dest_folder:
		return

	process_pdfs(source_folder, dest_folder)

# GUI
root = tk.Tk()
root.withdraw()  # Oculta la ventana principal
select_folders()
