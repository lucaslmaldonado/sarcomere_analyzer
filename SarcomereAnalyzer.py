from model import ImageModel
from view import ImageView
from controller import ImageController
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    controller = ImageController(root)
    root.mainloop()