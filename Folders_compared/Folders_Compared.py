import os
import tkinter as tk
from tkinter import filedialog, messagebox
from openpyxl import Workbook

def get_files(folder, extension=None):
	if extension:
		extension = extension.lower().strip()
		return set(f for f in os.listdir(folder) if f.lower().endswith(extension))
	else:
		return set(os.listdir(folder))

def compare_folders(folder_a, folder_b, extension=None):
	files_a = get_files(folder_a, extension)
	files_b = get_files(folder_b, extension)

	only_in_a = sorted(files_a - files_b)
	only_in_b = sorted(files_b - files_a)

	return sorted(files_a), sorted(files_b), only_in_a, only_in_b


def select_folder(entry):
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)

def run_comparison():
	folder_a = entry_a.get()
	folder_b = entry_b.get()

	if not os.path.isdir(folder_a) or not os.path.isdir(folder_b):
		messagebox.showerror("Error", "¡Selecciona carpetas válidas!")
		return

	files_a, files_b, only_in_a, only_in_b = compare_folders(folder_a, folder_b, entry_ext.get().strip())

	result_text = "Archivos en A pero NO en B:\n" + "\n".join(only_in_a) + \
				  "\n\nArchivos en B pero NO en A:\n" + "\n".join(only_in_b)

	# Save text result
	output_path = os.path.join(os.getcwd(), "resultado_comparacion.txt")
	with open(output_path, "w", encoding="utf-8") as f:
		f.write(result_text)

	# Save Excel result
	excel_path = save_comparison_to_excel(files_a, files_b, only_in_a, only_in_b)

	messagebox.showinfo("Resultado", f"¡Comparación completada!\n\nTXT: {output_path}\nExcel: {excel_path}")


def save_comparison_to_excel(files_a, files_b, only_in_a, only_in_b):
	from openpyxl import Workbook

	wb = Workbook()
	ws = wb.active
	ws.title = "Folder Comparison"
	ws.append(["Folder A", "Folder B", "A not in B", "B not in A"])

	max_len = max(len(files_a), len(files_b), len(only_in_a), len(only_in_b))
	for i in range(max_len):
		row = [
			files_a[i] if i < len(files_a) else "",
			files_b[i] if i < len(files_b) else "",
			only_in_a[i] if i < len(only_in_a) else "",
			only_in_b[i] if i < len(only_in_b) else ""
		]
		ws.append(row)

	excel_path = os.path.join(os.getcwd(), "comparacion_folders.xlsx")
	wb.save(excel_path)
	return excel_path

# GUI setup
root = tk.Tk()
root.title("Comparador de TXT entre dos carpetas")

tk.Label(root, text="Carpeta A").grid(row=0, column=0, padx=10, pady=5, sticky="e")
entry_a = tk.Entry(root, width=50)
entry_a.grid(row=0, column=1, padx=10)
tk.Button(root, text="Seleccionar", command=lambda: select_folder(entry_a)).grid(row=0, column=2, padx=10)

tk.Label(root, text="Carpeta B").grid(row=1, column=0, padx=10, pady=5, sticky="e")
entry_b = tk.Entry(root, width=50)
entry_b.grid(row=1, column=1, padx=10)
tk.Button(root, text="Seleccionar", command=lambda: select_folder(entry_b)).grid(row=1, column=2, padx=10)

tk.Label(root, text="Extensión de archivo (opcional, ej. .txt)").grid(row=2, column=0, padx=10, pady=5, sticky="e")
entry_ext = tk.Entry(root, width=50)
entry_ext.grid(row=2, column=1, padx=10)

tk.Button(root, text="Comparar", command=run_comparison, bg="lightblue").grid(row=3, column=1, pady=20)

root.mainloop()
