from PIL import Image
from pyzbar.pyzbar import decode

# Cargar directamente las imágenes desde sus rutas
img1 = Image.open(r"C:\Scripts\python\tools\QRs_comparar\pruebas\QR_1.png")
img2 = Image.open(r"C:\Scripts\python\tools\QRs_comparar\pruebas\QR_2.png")

# Decodificar QRs
data1 = decode(img1)
data2 = decode(img2)

# Obtener texto
text1 = data1[0].data.decode("utf-8") if data1 else None
text2 = data2[0].data.decode("utf-8") if data2 else None

# Mostrar resultados
print("===== COMPARACIÓN DE QRs =====")
if text1:
	print("QR 1:", text1)
else:
	print("QR 1: ❌ No se detectó ningún QR.")

if text2:
	print("QR 2:", text2)
else:
	print("QR 2: ❌ No se detectó ningún QR.")

if text1 and text2:
	print("✅ ¿Los textos son iguales?:", "Sí" if text1 == text2 else "No")

