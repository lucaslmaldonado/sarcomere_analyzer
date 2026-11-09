from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import numpy as np

class LineInteractor:
    def __init__(self, ax, canvas, toolbar, onselect, line_props=None, vertex_props=None):
        self.ax = ax
        self.canvas = canvas
        self.toolbar = toolbar
        self.onselect = onselect

        self.distance_threshold=8
        
        # Store all segments and vertices
        self.segments = []
        self.vertices = []
        self.vertex_markers = []
        
        # Interaction state
        self.dragging = False
        self.selected_vertex = None
        self.new_segment_start = None
        
        # Style properties
        self.line_props = line_props or dict(color='r', linewidth=2, alpha=0.8)
        self.vertex_props = vertex_props or dict(color='red', radius=0.2, alpha=0.8)
        self.temp_line_props = dict(color='r', linewidth=2, alpha=0.5, linestyle='--')
        
        # Connect events
        self.cid_press = canvas.mpl_connect('button_press_event', self._on_press)
        self.cid_motion = canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.cid_release = canvas.mpl_connect('button_release_event', self._on_release)
        self.cid_key = canvas.mpl_connect('key_press_event', self._on_key_press)
        
        # Temporary line for drawing new segments
        self.temp_line = None
        
    def _on_press(self, event):
        if event.inaxes != self.ax or self.toolbar.mode != '':
            return
            
        if event.button == 1:  # Left click
            if self._is_near_vertex(event):
                self.dragging = True
            else:
                self._handle_new_vertex(event)
                
        elif event.button == 3:  # Right click
            self._delete_nearest_vertex(event)
    
    def _on_motion(self, event):
        if event.inaxes != self.ax:
            return
            
        if self.dragging and self.selected_vertex is not None:
            self._drag_vertex(event)
        elif self.new_segment_start is not None:
            self._draw_temp_line(event)
    
    def _on_release(self, event):
        if event.button != 1 or event.inaxes != self.ax:
            self._cleanup_temp()
            return
            
        if self.dragging:
            self.dragging = False
            self.selected_vertex = None
            self._update_display()
        elif self.new_segment_start is not None and event.xdata is not None:
            self._complete_segment(event)
    
    def _on_key_press(self, event):
        if event.key == 'delete' and self.selected_vertex is not None:
            self._delete_vertex(self.selected_vertex)
        elif event.key == 'escape':
            self._cleanup_temp()
    
    def _is_near_vertex(self, event):
        """Check if click is near existing vertex"""
        for i, (x, y) in enumerate(self.vertices):
            if np.hypot(event.xdata - x, event.ydata - y) < self.distance_threshold:
                self.selected_vertex = i
                return True
        return False
    
    def _handle_new_vertex(self, event):
        """Handle creation of new vertex or segment"""
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
            
        if not self.vertices:
            self.vertices.append((x, y))
            self._update_display()
        else:
            self.new_segment_start = self.vertices[-1] if self.vertices else (x, y)
            self.temp_line = Line2D([self.new_segment_start[0], x], 
                                  [self.new_segment_start[1], y], 
                                  **self.temp_line_props)
            self.ax.add_line(self.temp_line)
    
    def _drag_vertex(self, event):
        """Drag an existing vertex"""
        if event.xdata is None or event.ydata is None:
            return
            
        self.vertices[self.selected_vertex] = (event.xdata, event.ydata)
        
        self._update_display()
        if self.onselect:
            self.onselect(self.vertices)
    
    def _draw_temp_line(self, event):
        """Draw temporary line for new segment"""
        if self.temp_line and event.xdata is not None and event.ydata is not None:
            self.temp_line.set_data([self.new_segment_start[0], event.xdata],
                                  [self.new_segment_start[1], event.ydata])
            self.canvas.draw_idle()
    
    def _complete_segment(self, event):
        """Complete the new segment"""
        end_point = (event.xdata, event.ydata)
        
        if not self._is_near_vertex(event):
            self.vertices.append(end_point)
        
        if self.temp_line:
            self.temp_line.remove()
            self.temp_line = None
        
        self.new_segment_start = None
        self._update_display()
        
        if self.onselect:
            self.onselect(self.vertices)
    
    def _delete_nearest_vertex(self, event):
        """Delete vertex nearest to click"""
        if not self.vertices:
            return
            
        distances = [np.hypot(event.xdata - vx, event.ydata - vy) 
                    for vx, vy in self.vertices]
        nearest_index = np.argmin(distances)
        
        if distances[nearest_index] < self.distance_threshold:  # Deletion threshold
            self._delete_vertex(nearest_index)
    
    def _delete_vertex(self, index):
        """Delete specific vertex"""
        if 0 <= index < len(self.vertices):
            self.vertices.pop(index)
            self._update_display()
            
            # Call onselect with updated vertices
            if self.onselect:
                self.onselect(self.vertices)
    
    def _update_display(self):
        """Update all visual elements"""
        # Clear existing elements
        for segment in self.segments:
            segment.remove()
        for marker in self.vertex_markers:
            marker.remove()
        
        self.segments = []
        self.vertex_markers = []
        
        # Draw line segments
        if len(self.vertices) > 1:
            for i in range(len(self.vertices) - 1):
                x1, y1 = self.vertices[i]
                x2, y2 = self.vertices[i + 1]
                line = Line2D([x1, x2], [y1, y2], **self.line_props)
                self.ax.add_line(line)
                self.segments.append(line)
        
        # Draw vertices
        for x, y in self.vertices:
            circle = Circle((x, y), **self.vertex_props)
            self.ax.add_patch(circle)
            self.vertex_markers.append(circle)
        
        self.canvas.draw_idle()
    
    def _cleanup_temp(self):
        """Clean up temporary drawing state"""
        if self.temp_line:
            self.temp_line.remove()
            self.temp_line = None
        self.new_segment_start = None
        self.dragging = False
        self.selected_vertex = None
        self.canvas.draw_idle()
    
    def disconnect(self):
        """Disconnect all event handlers and clean up"""
        self.canvas.mpl_disconnect(self.cid_press)
        self.canvas.mpl_disconnect(self.cid_motion)
        self.canvas.mpl_disconnect(self.cid_release)
        self.canvas.mpl_disconnect(self.cid_key)
        
        # Remove all visual elements
        for segment in self.segments:
            segment.remove()
        for marker in self.vertex_markers:
            marker.remove()
        if self.temp_line:
            self.temp_line.remove()
        
        self.segments = []
        self.vertex_markers = []
        self.vertices = []
        self.canvas.draw_idle()
    
    def get_vertices(self):
        """Get current vertices"""
        return self.vertices.copy()
    
    def clear(self):
        """Clear all vertices and segments"""
        self.vertices = []
        self._update_display()