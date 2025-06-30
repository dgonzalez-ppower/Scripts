import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd


def mover_archivos():
    # GUI para seleccionar Excel
    excel_path = filedialog.askopenfilename(title="Selecciona el archivo Excel", filetypes=[("Excel Files", "*.xlsx *.xls")])
    if not excel_path:
        messagebox.showerror("Error", "No se seleccionó ningún archivo Excel")
        return

    # Leer Excel
    try:
        df = pd.read_excel(excel_path)
        rutas_origen = df['Ruta origen'].dropna().astype(str).tolist()
    except Exception as e:
        messagebox.showerror("Error leyendo Excel", str(e))
        return

    # GUI para seleccionar carpeta destino
    carpeta_destino = filedialog.askdirectory(title="Selecciona la carpeta de destino")
    if not carpeta_destino:
        messagebox.showerror("Error", "No se seleccionó carpeta de destino")
        return

    resultados = []

    for ruta in rutas_origen:
        try:
            if os.path.exists(ruta) and os.path.isfile(ruta):
                nombre_archivo = os.path.basename(ruta)
                destino = os.path.join(carpeta_destino, nombre_archivo)
                shutil.copy2(ruta, destino)
                resultados.append((ruta, "Copiado"))
            else:
                resultados.append((ruta, "No encontrado"))
        except Exception as e:
            resultados.append((ruta, f"Error: {str(e)}"))

    df_resultado = pd.DataFrame(resultados, columns=["Ruta origen", "Resultado"])
    output_path = os.path.splitext(excel_path)[0] + "_resultado_copiados.xlsx"
    df_resultado.to_excel(output_path, index=False)
    messagebox.showinfo("Completado", f"Proceso terminado. Resultado guardado en:\n{output_path}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    mover_archivos()
