import os
import PyPDF2
import tkinter as tk
from tkinter import filedialog, messagebox

class PDFConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to TXT Converter")
        self.root.geometry("400x250")

        # Variables to store folder paths
        self.source_folder = tk.StringVar()
        self.dest_folder = tk.StringVar()

        # GUI Elements
        # Source folder selection
        tk.Label(root, text="Source Folder (PDFs):").pack(pady=5)
        tk.Entry(root, textvariable=self.source_folder, width=40).pack(pady=5)
        tk.Button(root, text="Browse", command=self.browse_source).pack(pady=5)

        # Destination folder selection
        tk.Label(root, text="Destination Folder (TXTs):").pack(pady=5)
        tk.Entry(root, textvariable=self.dest_folder, width=40).pack(pady=5)
        tk.Button(root, text="Browse", command=self.browse_dest).pack(pady=5)

        # Convert button
        tk.Button(root, text="Convert PDFs to TXT", command=self.convert_pdfs).pack(pady=20)

    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder with PDFs")
        if folder:
            self.source_folder.set(folder)

    def browse_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Folder for TXTs")
        if folder:
            self.dest_folder.set(folder)

    def convert_pdfs(self):
        source = self.source_folder.get()
        dest = self.dest_folder.get()

        if not source or not dest:
            messagebox.showerror("Error", "Please select both source and destination folders!")
            return

        if not os.path.exists(source):
            messagebox.showerror("Error", f"Source folder '{source}' does not exist!")
            return

        if not os.path.exists(dest):
            os.makedirs(dest)

        processed_count = 0

        for filename in os.listdir(source):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(source, filename)
                
                try:
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        num_pages = len(pdf_reader.pages)
                        text_content = ""

                        for page_num in range(num_pages):
                            page = pdf_reader.pages[page_num]
                            text_content += page.extract_text()

                        txt_filename = os.path.splitext(filename)[0] + '.txt'
                        txt_path = os.path.join(dest, txt_filename)

                        with open(txt_path, 'w', encoding='utf-8') as txt_file:
                            txt_file.write(text_content)

                        processed_count += 1
                        print(f"Converted: {filename} -> {txt_filename}")

                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")

        messagebox.showinfo("Complete", f"Conversion finished!\nProcessed {processed_count} PDF files.")

def main():
    root = tk.Tk()
    app = PDFConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()