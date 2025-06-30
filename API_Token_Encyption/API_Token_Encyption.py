import tkinter as tk
from tkinter import filedialog, messagebox
from cryptography.fernet import Fernet
import base64
import hashlib
import os

def generate_key(password: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())

def encrypt_token(token: str, password: str, filepath: str):
    key = generate_key(password)
    f = Fernet(key)
    encrypted = f.encrypt(token.encode())

    with open(filepath, "wb") as file:
        file.write(encrypted)

    messagebox.showinfo("Success", f"Token encrypted and saved to:\n{filepath}")

def browse_location():
    filepath = filedialog.asksaveasfilename(defaultextension=".enc", filetypes=[("Encrypted files", "*.enc")])
    if filepath:
        path_var.set(filepath)

def execute_encryption():
    token = token_entry.get("1.0", tk.END).strip()
    password = password_entry.get().strip()
    filepath = path_var.get().strip()

    if not token or not password or not filepath:
        messagebox.showerror("Error", "All fields are required.")
        return

    try:
        encrypt_token(token, password, filepath)
    except Exception as e:
        messagebox.showerror("Encryption Failed", str(e))

# GUI setup
root = tk.Tk()
root.title("Token Encryptor")
root.geometry("500x300")

# Token input
tk.Label(root, text="Paste your API Token:").pack(anchor="w", padx=10, pady=(10, 0))
token_entry = tk.Text(root, height=4, width=60)
token_entry.pack(padx=10)

# Password input
tk.Label(root, text="Enter encryption password:").pack(anchor="w", padx=10, pady=(10, 0))
password_entry = tk.Entry(root, show="*", width=60)
password_entry.pack(padx=10)

# File save location
tk.Label(root, text="Select where to save encrypted token:").pack(anchor="w", padx=10, pady=(10, 0))
path_frame = tk.Frame(root)
path_frame.pack(padx=10, fill="x")
path_var = tk.StringVar()
tk.Entry(path_frame, textvariable=path_var, width=45).pack(side="left", fill="x", expand=True)
tk.Button(path_frame, text="Browse", command=browse_location).pack(side="right")

# Encrypt button
tk.Button(root, text="Encrypt and Save Token", command=execute_encryption, bg="#4CAF50", fg="white").pack(pady=20)

root.mainloop()
