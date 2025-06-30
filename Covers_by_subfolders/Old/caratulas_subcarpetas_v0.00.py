import os
import tkinter as tk
from tkinter import filedialog, messagebox
from docx import Document
from docx2pdf import convert

# === Font-Preserving Placeholder Replacement ===
def replace_placeholder_and_save(template_path, folder_name, output_path):
    doc = Document(template_path)
    
    for para in doc.paragraphs:
        for run in para.runs:
            if "{{FOLDER_NAME}}" in run.text:
                run.text = run.text.replace("{{FOLDER_NAME}}", folder_name)
    doc.save(output_path)

# === PDF Generation using docx2pdf ===
def convert_docx_to_pdf(docx_path):
    convert(docx_path)  # Saves PDF next to DOCX

# === Batch Cover Generator ===
def generate_covers_ui(template_path, root_folder):
    folders_created = 0
    for folder_name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder_name)
        if os.path.isdir(folder_path):
            docx_output = os.path.join(folder_path, f"{folder_name}_COVER.docx")

            try:
                replace_placeholder_and_save(template_path, folder_name, docx_output)
                convert_docx_to_pdf(docx_output)
                folders_created += 1
            except Exception as e:
                print(f"⚠️ Error processing {folder_name}: {e}")

    messagebox.showinfo("✅ Done", f"Covers generated for {folders_created} folders!")

# === GUI Code ===
def select_template():
    path = filedialog.askopenfilename(filetypes=[("Word Documents", "*.docx")])
    template_path_var.set(path)

def select_root_folder():
    path = filedialog.askdirectory()
    root_folder_var.set(path)

def on_generate():
    template = template_path_var.get()
    root = root_folder_var.get()

    if not template or not root:
        messagebox.showerror("❌ Error", "Please select both a template and a root folder.")
        return

    generate_covers_ui(template, root)

# === Setup GUI ===
app = tk.Tk()
app.title("🚀 Carátulas por Subcarpeta")
app.geometry("500x240")

template_path_var = tk.StringVar()
root_folder_var = tk.StringVar()

tk.Label(app, text="📄 Select Word Template:").pack(pady=5)
tk.Entry(app, textvariable=template_path_var, width=60).pack()
tk.Button(app, text="Browse", command=select_template).pack()

tk.Label(app, text="📁 Select Folder with Subfolders:").pack(pady=5)
tk.Entry(app, textvariable=root_folder_var, width=60).pack()
tk.Button(app, text="Browse", command=select_root_folder).pack()

tk.Button(app, text="⚙️ Generate Covers", command=on_generate, bg="#4CAF50", fg="white", height=2).pack(pady=15)

app.mainloop()
