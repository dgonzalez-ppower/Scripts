from procesar_multiples_pdfs import procesar_en_paralelo
import tkinter as tk
from tkinter import filedialog

def main():
    root = tk.Tk()
    root.withdraw()

    carpeta = filedialog.askdirectory(title="Selecciona la carpeta con PDFs a traducir")
    if not carpeta:
        print("⚠️ No se seleccionó carpeta. Saliendo.")
        return

    procesar_en_paralelo(carpeta_pdf=carpeta, max_hilos=4)

if __name__ == "__main__":
    print("🚀 Modo batch multihilo lanzado...")
    main()