import os
from pathlib import Path
from tkinter import Tk, filedialog

# Escaped HTML with doubled {{}} for CSS
HTML_HEADER = """
<!DOCTYPE html>
<html lang="en">
<head>
\t<meta charset="UTF-8">
\t<title>📁 Folder Index</title>
\t<style>
\t\tbody {{ font-family: Arial, sans-serif; background: #f4f4f4; padding: 2em; }}
\t\th1 {{ color: #333; }}
\t\tul {{ list-style-type: none; padding-left: 20px; }}
\t\tli {{ margin: 4px 0; }}
\t\t.folder > span {{ font-weight: bold; cursor: pointer; }}
\t\t.file {{ color: #555; }}
\t\t.hidden {{ display: none; }}
\t</style>
</head>
<body>
\t<h1>📂 Folder Index: {root}</h1>
\t<ul>
"""

HTML_FOOTER = """
\t</ul>
\t<script>
\t\tdocument.querySelectorAll('.folder > span').forEach(span => {{
\t\t\tspan.addEventListener('click', () => {{
\t\t\t\tconst sublist = span.nextElementSibling;
\t\t\t\tsublist.classList.toggle('hidden');
\t\t\t}});
\t\t}});
\t</script>
</body>
</html>
"""

def build_file_tree_html(base_path: Path, current_path: Path) -> str:
	html = ""
	entries = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
	for entry in entries:
		rel_path = entry.relative_to(base_path).as_posix()  # Use POSIX-style for web links
		if entry.is_dir():
			sub_html = build_file_tree_html(base_path, entry)
			html += f'''
			<li class="folder">
				<span>📁 {entry.name}</span>
				<ul class="hidden">
					{sub_html}
				</ul>
			</li>'''
		else:
			html += f'<li class="file"><a href="{rel_path}" target="_blank">📄 {entry.name}</a></li>'
	return html

def generate_index(root_path: Path):
	tree_html = build_file_tree_html(root_path, root_path)
	html_content = HTML_HEADER.format(root=root_path.name) + tree_html + HTML_FOOTER

	output_file = root_path / "index.html"
	with open(output_file, "w", encoding="utf-8") as f:
		f.write(html_content)

	print(f"✅ HTML index generated at: {output_file}")

def select_folder_gui():
	root = Tk()
	root.withdraw()
	folder_selected = filedialog.askdirectory(title="Select a folder to index")
	if folder_selected:
		generate_index(Path(folder_selected))
	else:
		print("❌ No folder selected.")

if __name__ == "__main__":
	select_folder_gui()
