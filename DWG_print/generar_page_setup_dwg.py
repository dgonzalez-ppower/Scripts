import ezdxf
from pathlib import Path

# Crear nuevo archivo DWG
doc = ezdxf.new(dxfversion="R2018")
msp = doc.modelspace()

# Añadir rectángulo A3 horizontal (420x297 mm)
msp.add_lwpolyline([(0, 0), (420, 0), (420, 297), (0, 297), (0, 0)], close=True)

# Nombre de salida
output_path = Path(r"C:\Scripts\python\tools\DWG_print\pruebas\PDF_A3_Template.dwg")
doc.saveas(output_path)
print(f"Archivo guardado en: {output_path}")
