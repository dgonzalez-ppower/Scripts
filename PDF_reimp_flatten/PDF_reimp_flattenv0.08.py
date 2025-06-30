import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

def reimprimir_pdf_ghostscript(input_path, output_path, gs_executable="gswin64c"):
    """
    Reimprime el PDF usando Ghostscript. En Windows, generalmente se usa 'gswin64c'
    o 'gswin32c' según tu instalación.
    """
    try:
        # Lista de parámetros Ghostscript
        command = [
            gs_executable,
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.7",
            "-dEmbedAllFonts=true",
            "-dSubsetFonts=true",
            "-sFONTPATH=C:\\Windows\\Fonts",
            "-sOutputFile=" + output_path,
            input_path
        ]
        
        # Ejecutamos Ghostscript con la lista de parámetros
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error reimprimiendo (Ghostscript) '{os.path.basename(input_path)}': {e}")
        return False
    except Exception as e:
        print(f"Excepción en reimprimir (Ghostscript) '{os.path.basename(input_path)}': {e}")
        return False

def flatten_pdf_pdftk(input_path, output_path):
    """
    Usa PDFtk para aplanar el PDF.
    Ejecuta el comando:
      pdftk input_path output output_path flatten
    """
    try:
        command = ["pdftk", input_path, "output", output_path, "flatten"]
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error aplanando '{os.path.basename(input_path)}': {e}")
        return False
    except Exception as e:
        print(f"Excepción aplanando '{os.path.basename(input_path)}': {e}")
        return False

def main():
    root = tk.Tk()
    root.withdraw()

    folder_path = filedialog.askdirectory(title="Selecciona la carpeta que contiene los PDFs")
    if not folder_path:
        print("No se ha seleccionado ninguna carpeta. Saliendo.")
        return

    timestamp = datetime.now().strftime("%y%m%d%H%M")
    output_folder = os.path.join(folder_path, f"reimp_{timestamp}")
    os.makedirs(output_folder, exist_ok=True)

    pdf_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(folder_path, f))
    ]
    if not pdf_files:
        print("No se encontraron archivos PDF en la carpeta seleccionada.")
        return

    print("Procesando archivos PDF...\n")
    for pdf_file in pdf_files:
        input_file = os.path.join(folder_path, pdf_file)
        base_name, ext = os.path.splitext(pdf_file)

        reimp_file = os.path.join(output_folder, f"{base_name}_reimp{ext}")
        final_file = os.path.join(output_folder, f"{base_name}_reimp_aplanado{ext}")

        # Reimprimir con Ghostscript
        if reimprimir_pdf_ghostscript(input_file, reimp_file):
            print(f"Reimpreso (Ghostscript): '{pdf_file}' -> '{base_name}_reimp{ext}'")
            # Aplanar con PDFtk
            if flatten_pdf_pdftk(reimp_file, final_file):
                print(f"Aplanado: '{base_name}_reimp{ext}' -> '{base_name}_reimp_aplanado{ext}'")
                # Se ha removido la eliminación del archivo intermedio para conservarlo
                print(f"Archivo intermedio conservado: '{base_name}_reimp{ext}'")
            else:
                print(f"Fallo al aplanar: '{base_name}_reimp{ext}'. Se conserva el intermedio.")
        else:
            print(f"Fallo al reimprimir: '{pdf_file}'")
    
    print("\nProceso completado.")
    print(f"Los archivos finales (aplanados) se encuentran en: {output_folder}")

if __name__ == "__main__":
    main()
