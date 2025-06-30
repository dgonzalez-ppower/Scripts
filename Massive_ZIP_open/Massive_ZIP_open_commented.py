import os  # Módulo para manejar rutas de archivos y directorios
import zipfile  # Permite trabajar con archivos ZIP (leer, escribir, extraer)
import tkinter as tk  # Biblioteca para crear interfaces gráficas sencillas
from tkinter import filedialog, messagebox  # Componentes adicionales de Tkinter para diálogo de archivos y mensajes emergentes

# === Función para abrir un diálogo de selección de carpeta ===
def seleccionar_carpeta():
	"""
	Abre un cuadro de diálogo para que el usuario seleccione una carpeta.
	Una vez seleccionada, llama a la función para procesar todos los archivos ZIP que estén dentro.
	"""
	carpeta = filedialog.askdirectory(title="Selecciona la carpeta con archivos ZIP")
	if carpeta:
		extraer_zips(carpeta)

# === Función para extraer todos los archivos ZIP encontrados en una carpeta ===
def extraer_zips(carpeta_origen):
	"""
	Busca archivos ZIP dentro de la carpeta seleccionada y extrae cada uno en una subcarpeta
	del mismo nombre que el archivo ZIP.
	"""
	contador = 0  # Contador de archivos extraídos exitosamente

	# Recorre todos los archivos en la carpeta
	for archivo in os.listdir(carpeta_origen):
		if archivo.endswith('.zip'):
			ruta_zip = os.path.join(carpeta_origen, archivo)  # Ruta completa del archivo ZIP
			nombre_subcarpeta = os.path.splitext(archivo)[0]  # Nombre sin extensión
			ruta_destino = os.path.join(carpeta_origen, nombre_subcarpeta)  # Carpeta de destino

			# Crea la subcarpeta si no existe
			os.makedirs(ruta_destino, exist_ok=True)

			# Abre y extrae el contenido del ZIP
			with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
				zip_ref.extractall(ruta_destino)  # Extrae todo en la subcarpeta
			print(f'Extraído: {archivo} en {ruta_destino}')
			contador += 1

	# Muestra un mensaje informando cuántos archivos fueron procesados
	messagebox.showinfo("Proceso terminado", f"Se extrajeron {contador} archivos ZIP.")

# === Configura la interfaz gráfica con un botón ===
ventana = tk.Tk()  # Crea la ventana principal
ventana.title("Extractor de ZIPs")  # Título de la ventana
ventana.geometry("300x100")  # Tamaño de la ventana

# Botón que ejecuta la función para elegir carpeta
boton = tk.Button(ventana, text="Seleccionar carpeta", command=seleccionar_carpeta)
boton.pack(pady=20)

# Inicia el bucle de eventos (muestra la ventana y espera interacciones)
ventana.mainloop()
