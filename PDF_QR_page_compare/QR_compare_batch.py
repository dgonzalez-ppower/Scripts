import os
import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

def select_folder(title="Select folder"):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title=title)

def extract_qr_list(pdf_path):
    doc = fitz.open(pdf_path)
    result = []
    for page in doc:
        text = page.get_text()
        lines = text.splitlines()
        candidates = [line.strip() for line in lines if "INS" in line and "," in line]
        result.append(candidates[0] if candidates else None)
    return result

def compare_qrs(pdf_a, pdf_b):
    qrs_a = extract_qr_list(pdf_a)
    qrs_b = extract_qr_list(pdf_b)

    all_qrs_b = set(filter(None, qrs_b))
    all_qrs_a = set(filter(None, qrs_a))

    max_len = max(len(qrs_a), len(qrs_b))
    data = []

    for i in range(max_len):
        qr_a = qrs_a[i] if i < len(qrs_a) else None
        qr_b = qrs_b[i] if i < len(qrs_b) else None

        equivalent_b = next((j + 1 for j, val in enumerate(qrs_b) if val == qr_a), None)
        equivalent_a = next((j + 1 for j, val in enumerate(qrs_a) if val == qr_b), None)

        data.append({
            "Page": i + 1,
            "QR in PDF A": qr_a,
            "QR in PDF B": qr_b,
            "Equivalent Page in B": equivalent_b,
            "Equivalent Page in A": equivalent_a,
            "QR A not in B": qr_a if qr_a and qr_a not in all_qrs_b else None,
            "QR B not in A": qr_b if qr_b and qr_b not in all_qrs_a else None
        })

    return pd.DataFrame(data)

def main():
    folder_a = select_folder("Selecciona la carpeta A (PDFs referencia)")
    folder_b = select_folder("Selecciona la carpeta B (PDFs comparación)")

    for file in os.listdir(folder_a):
        if file.lower().endswith(".pdf") and file in os.listdir(folder_b):
            path_a = os.path.join(folder_a, file)
            path_b = os.path.join(folder_b, file)

            df = compare_qrs(path_a, path_b)

            output_file = os.path.join(folder_a, f"{Path(file).stem}_qr_comparison.xlsx")
            df.to_excel(output_file, index=False)
            print(f"Archivo generado: {output_file}")

if __name__ == "__main__":
    main()
