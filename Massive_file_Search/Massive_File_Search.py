import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import pandas as pd


def buscar_archivos():
    # GUI para seleccionar Excel
    excel_path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel Files", "*.xlsx *.xls")])
    if not excel_path:
        messagebox.showerror("Error", "No Excel file selected")
        return

    # Leer Excel
    try:
        df = pd.read_excel(excel_path)
        nombres = df['Archivo'].dropna().astype(str).tolist()
    except Exception as e:
        messagebox.showerror("Error leyendo Excel", str(e))
        return

    # GUI para seleccionar carpeta base
    carpeta_base = filedialog.askdirectory(title="Select Base Folder")
    if not carpeta_base:
        messagebox.showerror("Error", "No folder selected")
        return

    # Pedir extensión de archivo (opcional)
    extension = simpledialog.askstring("Extensión", "¿Qué extensión quieres buscar? (ej: pdf, txt, docx). Déjalo en blanco para todas:")
    if extension:
        extension = "." + extension.strip().lstrip(".")  # Asegura el punto inicial

    rutas_encontradas = []

    for nombre in nombres:
        ruta_archivo = ""
        for root, _, files in os.walk(carpeta_base):
            for file in files:
                if file.startswith("~") or file.startswith("$"):
                    continue  # Descarta archivos temporales
                if extension and not file.lower().endswith(extension.lower()):
                    continue
                if nombre.lower() in file.lower():
                    ruta_archivo = os.path.join(root, file)
                    break
            if ruta_archivo:
                break
        rutas_encontradas.append(ruta_archivo)

    df['Ruta encontrada'] = rutas_encontradas

    output_path = os.path.splitext(excel_path)[0] + "_con_resultados.xlsx"
    df.to_excel(output_path, index=False)
    messagebox.showinfo("Completado", f"Resultado guardado en:\n{output_path}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    buscar_archivos()
