import subprocess
import os
from tkinter import Tk, filedialog, messagebox

def main():
    root = Tk()
    root.withdraw()
    messagebox.showinfo("OCR Forzado", "Selecciona el archivo PDF al que quieres forzar OCR")
    pdf_path = filedialog.askopenfilename(
        title="Selecciona PDF",
        filetypes=[("Archivos PDF", "*.pdf")])

    if not pdf_path:
        messagebox.showerror("Error", "No has seleccionado ningún archivo PDF.")
        return

    out_pdf = os.path.splitext(pdf_path)[0] + "_OCR.pdf"
    messagebox.showinfo("OCR Forzado", f"Se generará: {out_pdf}")

    try:
        result = subprocess.run([
            "ocrmypdf",
            "--force-ocr",
            "--language", "spa",
            pdf_path,
            out_pdf
        ], capture_output=True, text=True)

        salida = result.stdout + "\n" + result.stderr
        if result.returncode == 0 and os.path.exists(out_pdf):
            messagebox.showinfo("OCR Forzado", f"OCR realizado con éxito:\n{out_pdf}")
        else:
            messagebox.showerror("Fallo OCR", f"Hubo un error:\n\n{salida}")
    except Exception as e:
        messagebox.showerror("Fallo grave", f"Error al lanzar ocrmypdf:\n{e}")

if __name__ == "__main__":
    main()
