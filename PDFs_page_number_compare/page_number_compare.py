import os
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
import pandas as pd

def contar_paginas_pdf(ruta_pdf):
    try:
        with fitz.open(ruta_pdf) as doc:
            return len(doc)
    except Exception as e:
        return f"Error: {e}"

def comparar_pdfs(carpeta1, carpeta2):
    resultados = []

    archivos_carpeta1 = {f for f in os.listdir(carpeta1) if f.lower().endswith('.pdf')}
    archivos_carpeta2 = {f for f in os.listdir(carpeta2) if f.lower().endswith('.pdf')}

    archivos_comunes = archivos_carpeta1.intersection(archivos_carpeta2)

    for archivo in sorted(archivos_comunes):
        ruta1 = os.path.join(carpeta1, archivo)
        ruta2 = os.path.join(carpeta2, archivo)
        paginas1 = contar_paginas_pdf(ruta1)
        paginas2 = contar_paginas_pdf(ruta2)
        resultados.append({
            'Nombre PDF': archivo,
            'Páginas Carpeta Origen': paginas1,
            'Páginas Carpeta Comparar': paginas2
        })

    return resultados

def guardar_resultados_en_excel(resultados, carpeta_destino):
    df = pd.DataFrame(resultados)
    ruta_excel = os.path.join(carpeta_destino, 'comparativa_paginas_pdfs.xlsx')
    df.to_excel(ruta_excel, index=False)
    return ruta_excel

def main():
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo("Seleccionar Carpeta", "Selecciona la carpeta ORIGEN")
    carpeta1 = filedialog.askdirectory(title="Selecciona carpeta ORIGEN")
    if not carpeta1:
        return

    messagebox.showinfo("Seleccionar Carpeta", "Selecciona la carpeta a COMPARAR")
    carpeta2 = filedialog.askdirectory(title="Selecciona carpeta COMPARAR")
    if not carpeta2:
        return

    resultados = comparar_pdfs(carpeta1, carpeta2)

    if not resultados:
        messagebox.showinfo("Resultado", "No se encontraron PDFs comunes entre las dos carpetas.")
        return

    ruta_guardado = guardar_resultados_en_excel(resultados, carpeta1)
    messagebox.showinfo("Éxito", f"Comparativa guardada en:\n{ruta_guardado}")

if __name__ == "__main__":
    main()
