import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import datetime
import pandas as pd
from PyPDF2 import PdfReader

from Organizador_RFIs_funciones import extract_bookmarks, is_undivided, move_whole_file, move_split_files, split_pdf_by_bookmarks

# --- GUI Setup ---

class RFIApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Gestor de RFIs")
        self.master.geometry("700x500")

        self.pdf_folder = None
        self.excel_path = None

        # --- Botones y etiquetas ---
        tk.Button(master, text="Seleccionar Carpeta de PDFs", command=self.select_pdf_folder).pack(pady=5)
        self.label_pdf = tk.Label(master, text="Carpeta no seleccionada")
        self.label_pdf.pack()

        tk.Button(master, text="Seleccionar Índice Excel", command=self.select_excel_file).pack(pady=5)
        self.label_excel = tk.Label(master, text="Archivo no seleccionado")
        self.label_excel.pack()

        tk.Button(master, text="Procesar", command=self.process).pack(pady=10)

        # --- Consola de logs ---
        self.log_text = scrolledtext.ScrolledText(master, height=20, width=80)
        self.log_text.pack(pady=10)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        print(msg)

    def select_pdf_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.pdf_folder = folder
            self.label_pdf.config(text=folder)

    def select_excel_file(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls *.xlsm")])
        if file:
            self.excel_path = file
            self.label_excel.config(text=file)

    def process(self):
        if not self.pdf_folder or not self.excel_path:
            messagebox.showwarning("Faltan datos", "Selecciona carpeta PDF y archivo Excel.")
            return

        try:
            self.log("[INFO] Iniciando procesamiento de RFIs...")

            excel_dir = os.path.dirname(self.excel_path)
            df_index = pd.read_excel(self.excel_path, header=0, dtype=str)
            df_index = df_index.rename(columns={
                df_index.columns[9]:  "Nombre RFI",
                df_index.columns[22]: "Subindice",
                df_index.columns[23]: "Subindice_2",
                df_index.columns[25]: "Nombre PDF Destino",
                df_index.columns[26]: "Enlace Destino"
            })
            df_index.columns = df_index.columns.str.strip()

            for archivo in os.listdir(self.pdf_folder):
                if not archivo.lower().endswith(".pdf"):
                    continue
                ruta_pdf = os.path.join(self.pdf_folder, archivo)
                self.log(f"[PDF] Procesando: {archivo}")

                reader = PdfReader(ruta_pdf)
                bookmarks = extract_bookmarks(reader)
                base_name = os.path.splitext(os.path.basename(archivo))[0]

                if is_undivided(bookmarks):
                    self.log("[INFO] El PDF no se divide.")
                    move_whole_file(base_name, ruta_pdf, df_index, excel_dir)
                else:
                    self.log("[INFO] El PDF será dividido en sub-RFIs.")
                    split_files = split_pdf_by_bookmarks(base_name, ruta_pdf, bookmarks, df_index, excel_dir)
                    move_split_files(base_name, split_files, df_index, excel_dir)

            # === Reporte ===
            pdf_names_in_folder = set()
            for archivo in os.listdir(self.pdf_folder):
                if archivo.lower().endswith(".pdf"):
                    nombre_base = os.path.splitext(archivo)[0]
                    pdf_names_in_folder.add(nombre_base)

            indice_names = set(df_index['Nombre RFI'].astype(str).str.strip())
            no_en_indice = pdf_names_in_folder - indice_names
            no_en_carpeta = indice_names - pdf_names_in_folder

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            reporte_path = os.path.join(excel_dir, f"reporte_RFIs_{timestamp}.txt")

            with open(reporte_path, "w", encoding="utf-8") as f:
                f.write("[PDFs en carpeta que NO aparecen en el índice]\n")
                for pdf in sorted(no_en_indice):
                    f.write(f"  - {pdf}\n")
                f.write("\n[Entradas del índice que NO tienen PDF asociado]\n")
                for rfi in sorted(no_en_carpeta):
                    filas = df_index[df_index['Nombre RFI'].astype(str).str.strip() == rfi].index.tolist()
                    for fila in filas:
                        f.write(f"  - Fila {fila + 2}: {rfi}\n")

            self.log(f"[OK] Reporte generado: {reporte_path}")
            self.log("[✅] Procesamiento finalizado correctamente.")

        except Exception as e:
            self.log(f"[ERROR] {str(e)}")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = RFIApp(root)
    root.mainloop()

