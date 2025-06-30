import os
import subprocess
import sys

VENV_DIR = "ocr_env"
PYTHON_EXE = os.path.join(VENV_DIR, "Scripts", "python.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "python")

def create_virtualenv():
    print("Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

def install_requirements():
    print("Installing requirements...")
    subprocess.check_call([PYTHON_EXE, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([PYTHON_EXE, "-m", "pip", "install", "-r", "requirements.txt"])

def main():
    need_setup = False

    # Crear entorno si no existe
    if not os.path.isdir(VENV_DIR) or not os.path.isfile(PYTHON_EXE):
        need_setup = True
    else:
        try:
            subprocess.check_call([PYTHON_EXE, "-c", "import fitz"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            need_setup = True

    if need_setup:
        if not os.path.isdir(VENV_DIR):
            create_virtualenv()
        install_requirements()

    print("Launching app...")
    subprocess.check_call([PYTHON_EXE, "traducir_pdf_gui.py"])


if __name__ == "__main__":
    main()
