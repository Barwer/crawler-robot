"""Tkinter presentation only: widgets, rendering and user callbacks."""
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import random


class CrawlerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Crawler Robot Control")
        self.root.resizable(True, True)
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{min(1200, screen_w-80)}x{min(760, screen_h-100)}")
        self.root.minsize(min(720, screen_w-80), min(480, screen_h-100))
        if self.root.state() != 'withdrawn':
            try:
                self.root.state('zoomed')
            except tk.TclError:
                pass
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        controls = ttk.LabelFrame(self.root, text="ควบคุมการทำงาน", padding=8)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        controls.columnconfigure(2, weight=1)
        self.run_button = ttk.Button(controls, text="Run")
        self.run_button.grid(row=0, column=0, padx=(0, 6))
        self.test_button = ttk.Button(controls, text="Test")
        self.test_button.grid(row=0, column=1, padx=(0, 12))
        self.mode_label = ttk.Label(controls, text="พักการทำงาน")
        self.mode_label.grid(row=0, column=2, sticky="w")
        ttk.Label(controls, text="จำนวนหุ่นยนต์:").grid(row=0, column=3, padx=6)
        self.robot_count = tk.IntVar(value=1)
        self.robot_selector = tk.OptionMenu(controls, self.robot_count, 1, 2)
        self.robot_selector.grid(row=0, column=4)
        ttk.Label(controls, text="โหมดเดี่ยวใช้:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.single_robot_id = tk.IntVar(value=1)
        self.single_robot_selector = tk.OptionMenu(controls, self.single_robot_id, 1, 2)
        self.single_robot_selector.grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Label(controls, text="ไฟล์ Q-table:").grid(row=1, column=0, pady=(8, 0), sticky="w")
        self.filename = ttk.Entry(controls)
        self.filename.insert(0, 'qvalue_%04d.log' % random.randint(0, 10000))
        self.filename.grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=(8, 0))
        self.save_button = ttk.Button(controls, text="บันทึก Q-table")
        self.save_button.grid(row=1, column=3, padx=6, pady=(8, 0))
        self.load_button = ttk.Button(controls, text="โหลด Q-table")
        self.load_button.grid(row=1, column=4, pady=(8, 0))

        connections = ttk.LabelFrame(self.root, text="สถานะการเชื่อมต่อ", padding=8)
        connections.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        connections.columnconfigure(0, weight=1)
        self.broker_label = tk.Label(connections, text="MQTT Broker: กำลังเชื่อมต่อ", anchor="w")
        self.broker_label.grid(row=0, column=0, sticky="ew")
        self.robot_labels = {}
        for robot_id in (1, 2):
            label = tk.Label(connections, text=f"Robot {robot_id}: ยังไม่พบข้อความตอบกลับ", anchor="w", justify="left", fg="#666666")
            label.grid(row=robot_id, column=0, sticky="ew", pady=2)
            self.robot_labels[robot_id] = label
        connections.bind('<Configure>', lambda event: [label.configure(wraplength=max(200, event.width-30)) for label in self.robot_labels.values()])

        self.panes = ttk.Panedwindow(self.root, orient="horizontal")
        self.panes.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        camera_panel = ttk.LabelFrame(self.panes, text="กล้อง · ArUco ID 1 / 2", padding=4)
        camera_panel.columnconfigure(0, weight=1)
        camera_panel.rowconfigure(0, weight=1)
        self.camera = tk.Canvas(camera_panel, width=320, height=240, bg="#16212e", highlightthickness=0)
        self.camera.grid(row=0, column=0, sticky="nsew")
        self.image_item = self.camera.create_image(0, 0, anchor="center")
        self._last_frame = None
        self.camera.bind('<Configure>', self._resize_camera)
        ttk.Label(camera_panel, text="หุ่นยนต์ต้องส่ง MQTT จึงยืนยันสถานะได้ระหว่างใช้งาน", wraplength=300).grid(row=1, column=0, sticky="w", pady=4)
        analysis_panel = ttk.LabelFrame(self.panes, text="การเรียนรู้ · State / Q-table", padding=4)
        analysis_panel.columnconfigure(0, weight=1)
        analysis_panel.rowconfigure(0, weight=1)
        self.analysis = tk.Canvas(analysis_panel, width=400, height=240, bg="white", highlightthickness=0)
        self.analysis.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(analysis_panel, orient="vertical", command=self.analysis.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(analysis_panel, orient="horizontal", command=self.analysis.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.analysis.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.panes.add(camera_panel, weight=1)
        self.panes.add(analysis_panel, weight=1)
        self.status = tk.StringVar(value="พร้อมใช้งาน · พักการทำงาน")
        ttk.Label(self.root, textvariable=self.status, relief="sunken", padding=5).grid(row=3, column=0, sticky="ew")

    def bind(self, controller):
        self.run_button.configure(command=controller.setPauseRun)
        self.test_button.configure(command=controller.setTest)
        self.save_button.configure(command=controller.dumpQvalues)
        self.load_button.configure(command=controller.loadQvalues)
        self.root.protocol("WM_DELETE_WINDOW", controller.close)

    def get_filename(self):
        return self.filename.get().strip()

    def render_connections(self, snapshot):
        connected = snapshot['broker_connected']
        self.broker_label.configure(
            text="MQTT Broker: " + ("เชื่อมต่อแล้ว" if connected else "ไม่ได้เชื่อมต่อ"),
            fg="#16733b" if connected else "#b3261e")
        states = {
            'recent': ("ได้รับคำตอบล่าสุด", "#16733b"),
            'waiting': ("กำลังรอคำตอบ", "#9a6700"),
            'timeout': ("ไม่ตอบคำสั่งภายในเวลาที่กำหนด", "#b3261e"),
            'unknown': ("ยังไม่พบข้อความตอบกลับ", "#666666"),
            'stale': ("ไม่มีข้อความใหม่ — ยังไม่ยืนยันการเชื่อมต่อ", "#9a6700"),
            'broker_offline': ("ตรวจสอบไม่ได้ — Broker ไม่เชื่อมต่อ", "#666666"),
        }
        for robot in snapshot['robots']:
            text, color = states[robot['state']]
            age = "" if robot['age'] is None else f" | {int(robot['age'])} วินาทีที่แล้ว"
            payload = "" if robot['payload'] is None else f" | {robot['payload'][:60]}"
            self.robot_labels[robot['id']].configure(
                text=f"Robot {robot['id']}: {text}{age}{payload}", fg=color)

    def set_mode(self, paused, testing):
        self.run_button.configure(text="Run" if paused else "Pause")
        self.test_button.configure(text="Pause" if testing else "Test")
        self.robot_selector.configure(state="normal" if paused and not testing else "disabled")
        self.single_robot_selector.configure(state="normal" if paused and not testing else "disabled")
        self.mode_label.configure(text="ทดสอบนโยบาย (Greedy)" if testing else ("พักการทำงาน" if paused else "กำลังฝึก (Training)"))

    def get_robot_count(self):
        return self.robot_count.get()

    def get_single_robot_id(self):
        return self.single_robot_id.get()

    def set_robot_count(self, count):
        self.robot_count.set(count)

    def show_frame(self, frame):
        if frame is None:
            self.status.set("Camera frame unavailable")
            return
        self._last_frame = frame
        self._resize_camera()

    def _resize_camera(self, event=None):
        if self._last_frame is None:
            return
        width, height = self.camera.winfo_width(), self.camera.winfo_height()
        if width <= 1 or height <= 1:
            width, height = 320, 240
        image = Image.fromarray(self._last_frame)
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        self.camera.itemconfig(self.image_item, image=self.photo)
        self.camera.coords(self.image_item, width/2, height/2)

    def render_analysis(self, snapshot):
        canvas = self.analysis
        canvas.delete("all")
        canvas.create_text(30, 15, anchor="w", text="State value")
        canvas.create_text(30, 245, anchor="w", text="Q-values: hand-down / hand-up / arm-down / arm-up")
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
            x = 30+i*125
            y = 270+j*38
            for k, action in enumerate(actions):
                value = cell['q'][action]
                canvas.create_rectangle(x+k*30, y, x+k*30+29, y+36, fill=color(value),
                                        outline='orange' if active and action == snapshot['action'] else 'black')
                canvas.create_text(x+k*30+14, y+18, text=f"{value:.1f}", fill='white', font=('Arial', 7))
        canvas.configure(scrollregion=(0, 0, 670, 475))
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
