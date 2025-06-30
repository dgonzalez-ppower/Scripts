import os
import tkinter as tk
from tkinter import filedialog, messagebox

def seleccionar_carpeta():
	ruta = filedialog.askdirectory()
	if ruta:
		entry_carpeta.delete(0, tk.END)
		entry_carpeta.insert(0, ruta)

def eliminar_cadena():
	carpeta = entry_carpeta.get()
	cadena = entry_cadena.get()

	if not carpeta or not cadena:
		messagebox.showwarning("Campos vacíos", "Debes seleccionar una carpeta y escribir una cadena.")
		return

	renombrados = 0
	eliminados = 0

	for nombre_archivo in os.listdir(carpeta):
		if cadena in nombre_archivo:
			nuevo_nombre = nombre_archivo.replace(cadena, "")
			ruta_original = os.path.join(carpeta, nombre_archivo)
			ruta_nueva = os.path.join(carpeta, nuevo_nombre)

			if os.path.exists(ruta_nueva):
				# Elimina el archivo original si el nuevo nombre ya existe
				os.remove(ruta_original)
				eliminados += 1
				print(f"Eliminado (ya existía): {nombre_archivo}")
			else:
				os.rename(ruta_original, ruta_nueva)
				renombrados += 1
				print(f"Renombrado: {nombre_archivo} -> {nuevo_nombre}")

	messagebox.showinfo("Proceso completado", f"Renombrados: {renombrados}\nEliminados por conflicto: {eliminados}")

# Crear GUI
ventana = tk.Tk()
ventana.title("Eliminar cadena de nombres de archivos")

tk.Label(ventana, text="Carpeta:").grid(row=0, column=0, sticky="e")
entry_carpeta = tk.Entry(ventana, width=40)
entry_carpeta.grid(row=0, column=1)
tk.Button(ventana, text="Buscar...", command=seleccionar_carpeta).grid(row=0, column=2)

tk.Label(ventana, text="Cadena a eliminar:").grid(row=1, column=0, sticky="e")
entry_cadena = tk.Entry(ventana, width=40)
entry_cadena.grid(row=1, column=1)

tk.Button(ventana, text="Eliminar cadena", command=eliminar_cadena).grid(row=2, column=1, pady=10)

ventana.mainloop()
