"""Tkinter presentation only: widgets, rendering and user callbacks."""
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import random


class CrawlerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Crawler GUI")
        self.root.resizable(False, False)
        controls = tk.Frame(self.root)
        controls.pack(fill="x", padx=8, pady=8)
        self.run_button = tk.Button(controls, text="Run")
        self.run_button.pack(side="left")
        self.save_button = tk.Button(controls, text="Dump QValues")
        self.save_button.pack(side="left", padx=4)
        self.filename = tk.Entry(controls, width=25)
        self.filename.insert(0, 'qvalue_%04d.log' % random.randint(0, 10000))
        self.filename.pack(side="left")
        self.load_button = tk.Button(controls, text="Load QValues")
        self.load_button.pack(side="left", padx=4)
        self.test_button = tk.Button(controls, text="Test")
        self.test_button.pack(side="left")
        self.camera = tk.Canvas(self.root, width=640, height=480)
        self.camera.pack()
        self.image_item = self.camera.create_image(0, 0, anchor="nw")
        self.status = tk.StringVar(value="Paused")
        tk.Label(self.root, textvariable=self.status).pack(fill="x")
        self.analysis = tk.Canvas(self.root, width=1000, height=250, bg="white")
        self.analysis.pack()

    def bind(self, controller):
        self.run_button.configure(command=controller.setPauseRun)
        self.test_button.configure(command=controller.setTest)
        self.save_button.configure(command=controller.dumpQvalues)
        self.load_button.configure(command=controller.loadQvalues)
        self.root.protocol("WM_DELETE_WINDOW", controller.close)

    def get_filename(self):
        return self.filename.get().strip()

    def set_mode(self, paused, testing):
        self.run_button.configure(text="Run" if paused else "Pause")
        self.test_button.configure(text="Pause" if testing else "Test")

    def show_frame(self, frame):
        if frame is None:
            self.status.set("Camera frame unavailable")
            return
        # Tracker supplies RGB pixels; all Tk image work stays on the UI thread.
        self.photo = ImageTk.PhotoImage(Image.fromarray(frame).resize((640, 480)))
        self.camera.itemconfig(self.image_item, image=self.photo)

    def render_analysis(self, snapshot):
        canvas = self.analysis
        canvas.delete("all")
        canvas.create_text(30, 15, anchor="w", text="State value")
        canvas.create_text(340, 15, anchor="w", text="Q-values: hand-down / hand-up / arm-down / arm-up")
        vals = [value for cell in snapshot['cells'] for value in cell['q'].values()]
        low, high = min(vals, default=0), max(vals, default=0)
        def color(value):
            if value < 0 and low < 0:
                return '#%02x0000' % int(value / low * 165)
            if value > 0 and high > 0:
                return '#00%02x00' % int(value / high * 165)
            return 'grey'
        actions = ('hand-down', 'hand-up', 'arm-down', 'arm-up')
        for cell in snapshot['cells']:
            i, j = cell['state']
            x, y = 30+i*52, 35+j*38
            active = cell['state'] == snapshot['state']
            canvas.create_rectangle(x, y, x+50, y+36,
                                    fill='orange' if active else color(cell['value']))
            canvas.create_text(x+25, y+18, text=f"{cell['value']:.2f}", fill='white')
            x = 340+i*125
            for k, action in enumerate(actions):
                value = cell['q'][action]
                canvas.create_rectangle(x+k*30, y, x+k*30+29, y+36, fill=color(value),
                                        outline='orange' if active and action == snapshot['action'] else 'black')
                canvas.create_text(x+k*30+14, y+18, text=f"{value:.1f}", fill='white', font=('Arial', 7))
        self.status.set(f"Step: {snapshot['step']} | epsilon: {snapshot['epsilon']:.4f}")

    def warning(self, title, text):
        messagebox.showwarning(title, text, parent=self.root)

    def error(self, title, text):
        messagebox.showerror(title, text, parent=self.root)

    def after(self, delay, callback):
        return self.root.after(delay, callback)

    def cancel(self, job):
        self.root.after_cancel(job)

    def start(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy()
