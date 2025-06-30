import os
import fitz  # PyMuPDF
import pikepdf
from tkinter import Tk, filedialog

def obtener_marcadores(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc(simple=True)
    doc.close()
    return toc

def aplicar_marcadores(pdf_path, toc, salida_path):
    # Abrimos el PDF con PyMuPDF para aplicar marcadores
    doc = fitz.open(pdf_path)
    doc.set_toc(toc)
    doc.save(salida_path)
    doc.close()

def seleccionar_carpeta(titulo):
    root = Tk()
    root.withdraw()
    carpeta = filedialog.askdirectory(title=titulo)
    return carpeta

def main():
    origen = seleccionar_carpeta("Selecciona la carpeta con PDFs con marcadores (ORIGEN)")
    destino = seleccionar_carpeta("Selecciona la carpeta con PDFs sin marcadores (DESTINO)")
    salida = seleccionar_carpeta("Selecciona carpeta para guardar PDFs con marcadores aplicados")

    for filename in os.listdir(origen):
        if not filename.lower().endswith(".pdf"):
            continue

        ruta_origen = os.path.join(origen, filename)
        ruta_destino = os.path.join(destino, filename)

        if not os.path.exists(ruta_destino):
            print(f"⚠ No se encontró en destino: {filename}")
            continue

        try:
            toc = obtener_marcadores(ruta_origen)
            if not toc:
                print(f"⚠ Sin marcadores: {filename}")
                continue

            salida_path = os.path.join(salida, filename)
            aplicar_marcadores(ruta_destino, toc, salida_path)
            print(f"✔ Marcadores copiados en: {filename}")

        except Exception as e:
            print(f"❌ Error con {filename}: {e}")

    print("\n🎉 Proceso finalizado.")

if __name__ == "__main__":
    main()
