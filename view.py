import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from line_interactor import LineInteractor

class ImageView:
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        self.master.title("Sarcomere Analyzer")

        try:
            self.master.state('zoomed')  # Works on Windows
        except tk.TclError:
            # Fallback for Linux/Mac
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()
            self.master.geometry(f"{screen_width}x{screen_height}+0+0")

        self.fig, (self.ax_img, self.ax_profile) = plt.subplots(1, 2, figsize=(10, 5))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)
        self.ax_img.set_xticks([])
        self.ax_img.set_yticks([])
        self.ax_profile.set_title("Intensity Profile")
        self.ax_profile.set_xlabel("Distance (pixels)")
        self.ax_profile.set_ylabel("Intensity")

        # Add toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.master)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.slider_frame = tk.Frame(master)
        self.slider_frame.pack(fill=tk.X, padx=10, pady=5)
        # Start slider
        self.start_slider = tk.Scale(
            self.slider_frame, from_=0, to=0, orient=tk.HORIZONTAL,
            label="Start", command=self._on_start_slider_change
        )
        self.start_slider.pack(side=tk.TOP, fill=tk.X, expand=True, padx=5)
        # End slider
        self.end_slider = tk.Scale(
            self.slider_frame, from_=0, to=0, orient=tk.HORIZONTAL,
            label="End", command=self._on_end_slider_change
        )
        self.end_slider.pack(side=tk.BOTTOM, fill=tk.X, expand=True, padx=5)

        # Add analyze button
        self.analyze_button = tk.Button(self.master, text="Analyze Profile", command=self.controller.analyze_profile)
        self.analyze_button.pack(side=tk.LEFT, fill=tk.X, padx=5)
        # Add save button
        self.save_button = tk.Button(self.master, text='Save', command=self.controller.save_data)
        self.save_button.pack(side=tk.LEFT, fill=tk.X, padx=5)

        # Vertical lines on profile plot
        self.vline_start = self.ax_profile.axvline(0, color='green', linestyle='--')
        self.vline_end = self.ax_profile.axvline(0, color='red', linestyle='--')

        # Callback placeholders (to be assigned by controller)
        self._start_slider_callback = None
        self._end_slider_callback = None

        # Menu bar
        self.menu_bar = tk.Menu(self.master)
        # File cascade
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Open Image", command = self.controller.load_image)
        self.file_menu.add_command(label="Exit", command = self.controller.quit_app)
        # Settings cascade
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=self.settings_menu)
        self.settings_menu.add_command(label="Set Pixel Size...", command = self.controller.set_pixel_size)

        self.master.config(menu=self.menu_bar)

        self._line_interactor = None


    def show_image(self, image):
        self.ax_img.clear()
        self.ax_profile.clear()
        self.ax_img.imshow(image, cmap='gray', origin='upper')
        self.ax_img.set_title("")
        self.ax_img.set_axis_off()
        self.ax_profile.set_title("Intensity Profile")
        self.ax_profile.set_xlabel("Distance")
        self.ax_profile.set_ylabel("Intensity")
        self.canvas.draw_idle()

    def set_line_selector(self, onselect_callback):
        if self._line_interactor is not None:
            self._line_interactor.disconnect()
        self._line_interactor = LineInteractor(self.ax_img, self.canvas, self.toolbar, onselect_callback,
                                               line_props=dict(color='red', linewidth=1))
        self.canvas.draw_idle()

    def show_profile(self, profile):
        profile_x, profile_y = profile
        self.ax_profile.clear()
        self.ax_profile.plot(profile_x, profile_y)
        self.vline_start = self.ax_profile.axvline(0, color='green', linestyle='--')
        self.vline_end = self.ax_profile.axvline(0, color='red', linestyle='--')
        self.ax_profile.set_title("Intensity Profile")
        self.ax_profile.set_xlabel("Distance")
        self.ax_profile.set_ylabel("Intensity")
        self.canvas.draw_idle()

    def clear_profile(self):
        self.ax_profile.clear()

    def _on_start_slider_change(self, val):
        if self._start_slider_callback:
            self._start_slider_callback(int(val))

    def _on_end_slider_change(self, val):
        if self._end_slider_callback:
            self._end_slider_callback(int(val))

    def bind_start_slider(self, func):
        self._start_slider_callback = func

    def bind_end_slider(self, func):
        self._end_slider_callback = func

    def update_sliders(self, n_points):
        # Initialize slider ranges and positions based on profile length
        self.start_slider.config(to=max(0, n_points - 1))
        self.end_slider.config(to=max(0, n_points - 1))
        self.start_slider.set(0)
        self.end_slider.set(max(0, n_points - 1))

    def update_vertical_lines(self, start_idx, end_idx):
        # Update vertical indicator lines on the profile plot
        pixel_size = self.controller.get_pixel_size()
        if not pixel_size:
            pixel_size = 1
        self.vline_start.set_xdata([start_idx*pixel_size, start_idx*pixel_size])
        self.vline_end.set_xdata([end_idx*pixel_size, end_idx*pixel_size])
        self.canvas.draw_idle()

    def show_results(self, x, y, peaks, valleys, HM_points, valley_HM_points):
        s = 16
        self.ax_profile.scatter([x[i] for i in peaks], [y[i] for i in peaks], c='red', s=s)
        self.ax_profile.scatter([x[i] for i in valleys], [y[i] for i in valleys], c='red', s=s)
        for (hm_x, hm_y) in HM_points:
            self.ax_profile.scatter(hm_x, hm_y, c='cyan', s=s)
        for (hm_x, hm_y) in valley_HM_points:
            self.ax_profile.scatter(hm_x, hm_y, c='purple', s=s)
        self.canvas.draw_idle()

    def show_error(self, message):
        messagebox.showerror("Error", message)
    
    def get_user_input(self, title, prompt, **kwargs):
        return simpledialog.askstring(title, prompt, parent=self.master, **kwargs)