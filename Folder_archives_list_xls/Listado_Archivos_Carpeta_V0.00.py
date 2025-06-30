import os
import pandas as pd
from tkinter import Tk, filedialog, messagebox

# Ocultar ventana principal de Tkinter
root = Tk()
root.withdraw()

# Diálogo para seleccionar carpeta
carpeta = filedialog.askdirectory(title="Selecciona la carpeta a listar")

if not carpeta:
    messagebox.showwarning("Cancelado", "No se seleccionó ninguna carpeta.")
    exit()

# Recorrer carpeta y listar archivos
archivos = []
for root_dir, _, files in os.walk(carpeta):
    for file in files:
        ruta_completa = os.path.join(root_dir, file)
        archivos.append({
            "Archivo": file,
            "Ruta completa": ruta_completa,
            "Tamaño (KB)": round(os.path.getsize(ruta_completa) / 1024, 2)
        })

# Exportar a Excel
df = pd.DataFrame(archivos)
nombre_excel = os.path.join(carpeta, "listado_archivos.xlsx")
df.to_excel(nombre_excel, index=False)

# Confirmación
messagebox.showinfo("¡Éxito!", f"Listado guardado como:\n{nombre_excel}")
