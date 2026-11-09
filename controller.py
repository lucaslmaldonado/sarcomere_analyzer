from tkinter import filedialog
import numpy as np
import matplotlib.pyplot as plt
from model import ImageModel
from view import ImageView

class ImageController:
    def __init__(self, root):
        self.model = ImageModel(self)
        self.view = ImageView(root, self)
        self.root = root

        # Bind slider callbacks
        self.view.bind_start_slider(self.on_start_slider_change)
        self.view.bind_end_slider(self.on_end_slider_change)

        # Store current slider values
        self._slider_start = 0
        self._slider_end = 0

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.tif;*.tiff;*.bmp;*.jpeg")]
        )
        if not file_path:
            return
        img = self.model.load_image(file_path)
        self.view.show_image(img)
        self.view.set_line_selector(self.on_line_select)

    def set_pixel_size(self):
        new_size = self.view.get_user_input(
            "Pixel Size",
            "Enter a pixel size in micrometers:",
            initialvalue=0
        )
        if new_size:
            try:
                self.model.pixel_size = float(new_size)
            except ValueError:
                self.view.show_error("Please enter a valid number.")
    
    def get_pixel_size(self):
        return self.model.pixel_size

    def on_line_select(self, vertices):
        if len(vertices) < 2:
            print("Need at least 2 points for a profile")
            self.view.clear_profile()
            return
        
        img = self.model.image
        if img is None:
            return
        
        h, w = img.shape[:2]
        
        # Initialize arrays for the complete profile
        all_profile_x = np.array([], dtype=float)
        all_profile_y = np.array([], dtype=float)
        
        # Process each segment of the polyline
        for i in range(len(vertices) - 1):
            p0, p1 = vertices[i], vertices[i + 1]
            x0, y0 = p0
            x1, y1 = p1
            
            # Convert to image coordinates with clipping
            c0 = np.clip(int(round(x0)), 0, w - 1)
            r0 = np.clip(int(round(y0)), 0, h - 1)
            c1 = np.clip(int(round(x1)), 0, w - 1)
            r1 = np.clip(int(round(y1)), 0, h - 1)
            
            # Get profile for this segment
            segment_x, segment_y = self.model.get_profile(c0, r0, c1, r1, len(all_profile_x)-1)
            
            if segment_y is not None:
                # For segments beyond the first, we need remove 
                # the first element (it's equal to the last
                #  element of the previous segment).
                if i > 0:
                    segment_x = segment_x[1:]
                    segment_y = segment_y[1:]
                
                # Append this segment's data
                all_profile_x = np.concatenate([all_profile_x, segment_x])
                all_profile_y = np.concatenate([all_profile_y, segment_y])
        
        if len(all_profile_y) > 0:
            # Show the complete profile
            self.view.show_profile((all_profile_x, all_profile_y))
            
            # Update sliders for the complete profile
            n = len(all_profile_y)
            self._slider_start = 0
            self._slider_end = n - 1
            self.view.update_sliders(n)
            self.view.update_vertical_lines(self._slider_start, self._slider_end)

            # Pass complete profile to model
            self.model.set_profile((all_profile_x, all_profile_y))

            # Store the vertices for reference
            self.current_vertices = vertices
            print(f"Processed segmented line with {len(vertices)} points, {n} profile points")
        else:
            print("No valid profile data generated")


    def on_start_slider_change(self, val):
        val = int(val)
        # Enforce start ≤ end
        if val > self._slider_end:
            val = self._slider_end
            self.view.start_slider.set(val)
        self._slider_start = val
        self._update_profile_interval()

    def on_end_slider_change(self, val):
        val = int(val)
        # Enforce end ≥ start
        if val < self._slider_start:
            val = self._slider_start
            self.view.end_slider.set(val)
        self._slider_end = val
        self._update_profile_interval()

    def _update_profile_interval(self):
        # Update vertical lines
        self.view.update_vertical_lines(self._slider_start, self._slider_end)

    def analyze_profile(self):
        self.model.analyze_profile(self._slider_start, self._slider_end)

    def show_results(self, x, y, peaks, valleys, HM_points, valley_HM_points):
        self.view.show_results(x, y, peaks, valleys, HM_points, valley_HM_points)

    def save_data(self):
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",  # or .png, .csv etc.
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Save Data As"
        )
        self.model.save_data(save_path, self.current_vertices)

    def quit_app(self):
        plt.close('all')
        self.root.destroy()