import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter

def select_folder(title):
	root = tk.Tk()
	root.withdraw()
	return filedialog.askdirectory(title=title)

def replace_first_page(source_path, cover_path, output_path):
	log = []

	for filename in os.listdir(source_path):
		if not filename.lower().endswith('.pdf'):
			continue

		source_file = os.path.join(source_path, filename)
		cover_file = os.path.join(cover_path, filename)

		if not os.path.exists(cover_file):
			log.append(f"{filename}: Cover not found.")
			continue

		try:
			# Load PDFs
			source_pdf = PdfReader(source_file)
			cover_pdf = PdfReader(cover_file)
			
			# New PDF writer
			output_pdf = PdfWriter()

			# Add first page from cover
			output_pdf.add_page(cover_pdf.pages[0])

			# Add the rest of the source PDF
			for page in source_pdf.pages[1:]:
				output_pdf.add_page(page)

			# Save to output folder
			output_filename = os.path.splitext(filename)[0] + "_coverswapped.pdf"
			output_file_path = os.path.join(output_path, output_filename)
			with open(output_file_path, "wb") as f_out:
				output_pdf.write(f_out)

			log.append(f"{filename}: Success")

		except Exception as e:
			log.append(f"{filename}: Error - {str(e)}")

	return log

def main():
	# GUI prompts
	source_folder = select_folder("Select SOURCE PDF folder")
	cover_folder = select_folder("Select COVER PDF folder")
	output_folder = select_folder("Select OUTPUT folder")

	if not source_folder or not cover_folder or not output_folder:
		messagebox.showerror("Error", "All folders must be selected.")
		return

	# Processing
	log = replace_first_page(source_folder, cover_folder, output_folder)

	# Show final log in a messagebox and print to console
	log_text = "\n".join(log)
	print(log_text)
	messagebox.showinfo("Processing Complete", f"Operation completed.\n\nLog:\n{log_text}")

if __name__ == "__main__":
	main()
