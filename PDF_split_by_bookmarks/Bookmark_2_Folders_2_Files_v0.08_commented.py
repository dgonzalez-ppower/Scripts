import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF: powerful PDF processing (e.g., reading pages, splitting, editing)
from PyPDF2 import PdfReader  # PyPDF2: useful for reading bookmarks (outlines)

# --- Utility Functions ---

# Sanitize file or folder names by removing illegal characters (especially for Windows)
def sanitize(name):
	# Removes characters that are not allowed in Windows file/folder names
	return re.sub(r'[\\/*?:"<>|]', "", name)

# Print the structure of bookmarks recursively (mainly for debugging or inspection)
def print_outline(outline, indent=0):
	if isinstance(outline, list):
		for item in outline:
			print_outline(item, indent)
	else:
		try:
			# If the object has a title and page attribute, print it indented
			print(" " * indent + f"Title: {outline.title}, Page: {outline.page}")
		except AttributeError:
			# Fallback for unexpected object types
			print(" " * indent + f"Non-standard bookmark object: {outline}")

# --- Core Logic: Convert Nested Bookmarks into Flat List ---

# Convert hierarchical bookmarks into a flat list
# Each entry includes the title, page number, hierarchy level (depth), and parent titles for directory naming
def flatten_bookmarks(bookmarks, pdf_reader, depth=0, parent_titles=None):
	if parent_titles is None:
		parent_titles = []
	nodes = []
	i = 0
	while i < len(bookmarks):
		item = bookmarks[i]

		# If the item is a list (container, not a bookmark), just recurse through it
		if not hasattr(item, "title"):
			nodes.extend(flatten_bookmarks(item, pdf_reader, depth, parent_titles))
			i += 1
		else:
			# Handle the actual bookmark with a title
			try:
				title = item.title.strip() if item.title.strip() else "Untitled"
			except Exception:
				title = "Untitled"

			# Get the page number the bookmark points to
			try:
				page = pdf_reader.get_destination_page_number(item)
			except Exception as e:
				print(f"Error getting page for bookmark '{title}': {e}")
				i += 1
				continue

			# Store relevant info in a flat node
			current_node = {
				'title': title,
				'page': page,
				'depth': depth,
				'parent_titles': list(parent_titles)
			}
			nodes.append(current_node)

			# If the next item is a list, it's the children of this bookmark
			if i + 1 < len(bookmarks) and isinstance(bookmarks[i+1], list):
				children = flatten_bookmarks(bookmarks[i+1], pdf_reader, depth + 1, parent_titles + [title])
				nodes.extend(children)
				i += 2  # Skip over child container already processed
			else:
				i += 1
	return nodes

# --- Page Extraction ---

# Extract pages from original PDF based on start/end range, save them as a new file
# PyMuPDF is used for its speed and accurate page handling
def extract_pages_pymupdf(pdf_path, start_page, end_page, output_folder, bookmark_name):
	src_doc = fitz.open(pdf_path)  # Open the original PDF
	new_doc = fitz.open()  # Create a new empty PDF
	new_doc.insert_pdf(src_doc, from_page=start_page, to_page=end_page - 1)  # Copy the range of pages

	# Save the new document in a sanitized filename based on bookmark name
	output_file = os.path.join(output_folder, f"{sanitize(bookmark_name)}.pdf")
	new_doc.save(output_file)
	new_doc.close()
	src_doc.close()
	print(f"Extracted pages {start_page} to {end_page - 1} for '{bookmark_name}' into {output_file}")

# --- Main Workflow ---

# Complete workflow: read a PDF, parse bookmarks, and extract pages accordingly
def process_pdf(pdf_path):
	print("Processing PDF file:", pdf_path)
	base_dir = os.path.dirname(pdf_path)

	try:
		reader = PdfReader(pdf_path)
		outlines = reader.outline  # Extract bookmarks (also called outline)
		print("Successfully read the bookmark outline.")
	except Exception as e:
		messagebox.showerror("Error", f"Error reading PDF bookmarks: {e}")
		print(f"Error reading PDF bookmarks: {e}")
		return

	if not outlines:
		messagebox.showinfo("Info", "No bookmarks found in the PDF.")
		print("No bookmarks found.")
		return

	# Print original outline structure for debug
	print("---- Debug: Outline Structure ----")
	print_outline(outlines)
	print("---- End Debug ----")

	total_pages = len(reader.pages)
	flattened = flatten_bookmarks(outlines, reader)

	print("Flattened bookmarks:")
	for node in flattened:
		print(node)

	# For each bookmark node, extract a PDF segment
	for i, node in enumerate(flattened):
		start_page = node['page']
		if i + 1 < len(flattened):
			end_page = flattened[i+1]['page']
		else:
			end_page = total_pages

		if end_page <= start_page:
			end_page = total_pages  # Fallback if something's off

		# Build folder path using parent titles as subfolders
		folder_path = os.path.join(base_dir, *[sanitize(x) for x in node['parent_titles']], sanitize(node['title']))
		os.makedirs(folder_path, exist_ok=True)

		print(f"Extracting pages {start_page} to {end_page - 1} for '{node['title']}' into {folder_path}")
		extract_pages_pymupdf(pdf_path, start_page, end_page, folder_path, node['title'])

	# Inform the user once all extractions are done
	messagebox.showinfo("Success", "PDF sections extracted and folder structure created successfully!")
	print("Processing completed.")

# --- GUI Entry Point ---

# Open a file dialog to let user choose a PDF, then run the process
def select_pdf():
	file_path = filedialog.askopenfilename(
		title="Select a PDF file", 
		filetypes=[("PDF Files", "*.pdf")]
	)
	if file_path:
		process_pdf(file_path)

# GUI initialization and launch
if __name__ == "__main__":
	root = tk.Tk()
	root.title("PDF Bookmark Splitter (Flattened DFS)")
	root.geometry("300x100")
	btn = tk.Button(root, text="Select PDF File", command=select_pdf)
	btn.pack(expand=True)
	root.mainloop()
