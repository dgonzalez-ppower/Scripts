import subprocess

dwg_path = r"C:\Scripts\python\tools\DWG_print\pruebas\A1K1_17.DWG"
scr_path = r"C:\Scripts\python\tools\DWG_print\print_model.scr"
accoreconsole = r"C:\Program Files\Autodesk\DWG TrueView 2026 - English\accoreconsole.exe"

subprocess.run([
    accoreconsole,
    "/i", dwg_path,
    "/s", scr_path
])
