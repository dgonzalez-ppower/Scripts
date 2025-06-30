import os  # Provides functions to interact with the file system (folders, paths, etc.)
import re  # Regular expressions, used for sorting files naturally (e.g., 1, 2, 10 instead of 1, 10, 2)
import tkinter as tk  # GUI toolkit for building graphical interfaces in Python
from tkinter import filedialog, messagebox  # Tools to open folder dialogs and show message popups
from pypdf import PdfReader, PdfWriter  # Library for reading and writing PDF files

# === Natural Sorting Utility ===
def natural_key(string_):
	"""
	Splits a string into a list of numbers and letters to enable natural sorting.
	For example: ['file', 1, '.pdf'], ['file', 10, '.pdf']
	"""
	return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', string_)]

# === Directory Tree Builder ===
def build_tree(folder_path):
	"""
	Creates a hierarchical tree structure of folders and PDF files.
	This structure helps in traversing and merging PDFs in a logical order.
	"""
	node = {
		'folder_path': folder_path,
		'folder_name': os.path.basename(folder_path),
		'pdf_files': [],  # PDF files in the current folder
		'children': []  # List of subfolder nodes
	}
	cover_pdfs = []
	other_pdfs = []

	# Loop through items in the folder and classify them
	for item in sorted(os.listdir(folder_path), key=natural_key):
		full_path = os.path.join(folder_path, item)
		if os.path.isfile(full_path) and item.lower().endswith('.pdf'):
			if "cover" in item.lower():
				cover_pdfs.append(full_path)
			else:
				other_pdfs.append(full_path)
		elif os.path.isdir(full_path):
			node['children'].append(build_tree(full_path))

	node['pdf_files'] = cover_pdfs + other_pdfs  # Covers first
	return node

# === PDF Check Helper ===
def merge_tree_has_pdf(node):
	"""
	Returns True if the node or any of its children contains PDF files.
	Used to decide if a bookmark should be added for a folder.
	"""
	return bool(node['pdf_files']) or any(merge_tree_has_pdf(child) for child in node['children'])

# === Tree Merger ===
def merge_tree(node, writer, current_offset, parent_bookmark, pdf_reader_cache):
	"""
	Recursively merges PDF files found in a folder tree.
	Adds bookmarks for folders and files.
	"""
	has_pdf = bool(node['pdf_files']) or any(merge_tree_has_pdf(child) for child in node['children'])
	bookmark = None
	first_pdf_offset = current_offset
	child_offsets = []

	# Helper function to add internal bookmarks from a PDF
	def add_internal_bookmarks(outlines, parent, base_offset):
		for item in outlines:
			if isinstance(item, list):
				add_internal_bookmarks(item, parent, base_offset)
			else:
				try:
					title = item.title if hasattr(item, "title") else "Untitled"
					page_index = reader.get_destination_page_number(item)
					internal_bm = writer.add_outline_item(title, base_offset + page_index, parent=parent)
					print(f"✔ Internal bookmark added: {title} → page {base_offset + page_index}")
				except Exception as e:
					print(f"⚠️ Error processing internal bookmark '{title}': {e}")

	# If the folder has any PDFs, add a bookmark
	if has_pdf:
		bookmark = writer.add_outline_item(node['folder_name'], first_pdf_offset, parent=parent_bookmark)

	multiple_pdfs = len(node['pdf_files']) > 1

	# Loop through PDF files in the current folder
	for i, pdf_path in enumerate(node['pdf_files']):
		if pdf_path in pdf_reader_cache:
			reader = pdf_reader_cache[pdf_path]
		else:
			try:
				reader = PdfReader(pdf_path)
				pdf_reader_cache[pdf_path] = reader
			except Exception as e:
				messagebox.showerror("Error", f"Failed to read PDF '{pdf_path}': {e}")
				continue

		pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
		pdf_bookmark = None

		if i == 0:
			first_pdf_offset = current_offset

		# Add each page to the final PDF
		for page in reader.pages:
			writer.add_page(page)
		num_pages = len(reader.pages)

		# Add bookmark for the file if there are multiple PDFs in the folder
		if multiple_pdfs:
			pdf_bookmark = writer.add_outline_item(pdf_name, current_offset, parent=bookmark)

		# If the PDF has its own bookmarks, include them
		if reader.outline:
			add_internal_bookmarks(reader.outline, pdf_bookmark or bookmark, current_offset)

		current_offset += num_pages

	# Process subfolders recursively
	for child in sorted(node['children'], key=lambda x: natural_key(x['folder_name'])):
		child_offset_before = current_offset
		current_offset = merge_tree(child, writer, current_offset, bookmark, pdf_reader_cache)
		child_offsets.append(child_offset_before)

	# If the folder has no files but child folders do, assign the bookmark to the first child's page
	if not node['pdf_files'] and child_offsets and bookmark is not None:
		bookmark.page_number = child_offsets[0]

	return current_offset

# === Final PDF Assembly ===
def assemble_pdf(source_folder, destination_folder):
	"""
	Main function to initiate PDF merging process.
	Builds folder tree, processes each file, and saves the merged output.
	"""
	writer = PdfWriter()
	current_offset = 0
	pdf_reader_cache = {}  # Stores loaded PDFs to avoid reloading

	tree = build_tree(source_folder)
	merge_tree(tree, writer, current_offset, parent_bookmark=None, pdf_reader_cache=pdf_reader_cache)

	folder_name = os.path.basename(os.path.normpath(source_folder))
	output_filename = f"{folder_name}_merged.pdf"
	output_path = os.path.join(destination_folder, output_filename)

	try:
		with open(output_path, "wb") as f_out:
			writer.write(f_out)
		messagebox.showinfo("Success", f"Merged PDF saved to:\n{output_path}")
	except Exception as e:
		messagebox.showerror("Error", f"Could not save merged PDF:\n{e}")

# === GUI Launcher ===
def main():
	"""
	GUI for selecting source and destination folders and launching the merge process.
	"""
	root = tk.Tk()
	root.title("PDF Merger with Covers and Smart Bookmarks")
	root.geometry("600x220")

	source_var = tk.StringVar()
	dest_var = tk.StringVar()

	def browse_source():
		folder = filedialog.askdirectory(title="Select Source Folder")
		if folder:
			source_var.set(folder)

	def browse_dest():
		folder = filedialog.askdirectory(title="Select Destination Folder")
		if folder:
			dest_var.set(folder)

	def run_assemble():
		source = source_var.get()
		dest = dest_var.get()
		if not source or not dest:
			messagebox.showerror("Error", "You must select both source and destination folders.")
			return
		assemble_pdf(source, dest)

	tk.Label(root, text="Source Folder:").pack(pady=5)
	tk.Entry(root, textvariable=source_var, width=80).pack(pady=5)
	tk.Button(root, text="Browse Source Folder", command=browse_source).pack(pady=5)

	tk.Label(root, text="Destination Folder:").pack(pady=5)
	tk.Entry(root, textvariable=dest_var, width=80).pack(pady=5)
	tk.Button(root, text="Browse Destination Folder", command=browse_dest).pack(pady=5)

	tk.Button(root, text="Merge PDFs", command=run_assemble, bg="green", fg="white").pack(pady=10)

	root.mainloop()

# === Entry Point ===
if __name__ == "__main__":
	main()
