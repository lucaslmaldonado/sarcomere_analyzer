import numpy as np
from scipy import signal
import pandas as pd
from skimage import io
from skimage.measure import profile_line
import matplotlib.pyplot as plt


class ImageModel:
    def __init__(self, controller):
        self.image = None
        self.controller = controller
        self.pixel_size = None

    def load_image(self, path):
        img = io.imread(path)
        if img.ndim == 3:
            if img.shape[2] == 4:
                img = img[..., :3]
            img = np.mean(img, axis=2)
        self.image = img.astype(float)
        return self.image

    def get_profile(self, x1, y1, x2, y2, cumulative_distance):
        cumulative_distance = 0 if cumulative_distance < 0 else cumulative_distance

        if self.image is None:
            return None
        profile_y = profile_line(self.image, (y1, x1), (y2, x2),
                            order=1, mode='reflect', linewidth=1)
        N = len(profile_y)
        profile_x = (np.linspace(0, N-1, N)+cumulative_distance)
        if self.pixel_size:
            profile_x *= self.pixel_size
        return (profile_x, profile_y)
    
    def set_profile(self, p):
        self.profile_x = p[0]
        self.profile_y = p[1]
    
    def find_next_peak(self, id):
        return [i for i in self.peaks if i>id][0]

    def find_previous_peak(self, id):
        return [i for i in self.peaks if i<id][-1]

    def find_next_valley(self, id):
        return [i for i in self.valleys if i>id][0]
    
    def find_myosin_peaks(self):
        self.peaks, self._p = signal.find_peaks(self.cropped_profile_y)
    
    def is_value_in_interval(self, v, endpoints):
        if endpoints[0]<=v<=endpoints[1] or endpoints[1]<=v<=endpoints[0]:
            return True
        return False

    def find_intersection(self, x, y, v):
        if self.is_value_in_interval(v, (y[0],y[-1])):
            upper_i = [i for i in range(len(y)-1,-1,-1) if y[i]>v][-1]
            lower_i = [i for i in range(len(y)) if y[i]<v][-1]
            if lower_i > upper_i:
                lower_i, upper_i = upper_i, lower_i
            a = (y[upper_i]-y[lower_i])/(x[upper_i]-x[lower_i])
            b = y[upper_i]-a*x[upper_i]
            return (v-b)/a
        else:
            print("Warning: Poorly defined peak/valley found.", \
                " Approximate point will be used.",\
                " Check if your data follows our requirements.")
            i = min(range(len(y)), key=lambda i: abs(y[i]-v))
            return x[i]

    def find_intersarcomere_valleys(self):
        # Find valleys between sarcomeres
        self.valleys = [0]
        for i in range(1,len(self.peaks)-1,2):
            sy = -1*np.array(self.cropped_profile_y[self.peaks[i]:self.peaks[i+1]+1])
            v, _p = signal.find_peaks(sy)
            self.valleys.extend(v+self.peaks[i])
        self.valleys.append(len(self.cropped_profile_x)-1)

    def find_myosin_HM_points(self):
        self.HM_points = []
        for i in range(len(self.valleys)-1):
            half_maximum = (max(self.cropped_profile_y[self.valleys[i]: self.valleys[i+1]+1])+min(self.cropped_profile_y[self.valleys[i]: self.valleys[i+1]+1]))/2
            next_peak = self.find_next_peak(self.valleys[i])
            first_intersection = self.find_intersection(self.cropped_profile_x[self.valleys[i]: next_peak+1], self.cropped_profile_y[self.valleys[i]: next_peak+1], half_maximum)
            self.HM_points.append((first_intersection, half_maximum))
            previous_peak = self.find_previous_peak(self.valleys[i+1])
            second_intersection = self.find_intersection(self.cropped_profile_x[previous_peak: self.valleys[i+1]+1], self.cropped_profile_y[previous_peak: self.valleys[i+1]+1], half_maximum)
            self.HM_points.append((second_intersection, half_maximum))

    def find_valey_HM_points(self):
        self.valley_HM_points = []
        for i in range(1, len(self.peaks)-1,2):
            max_peak = max(self.cropped_profile_y[self.peaks[i]], self.cropped_profile_y[self.peaks[i+1]])
            valley = self.find_next_valley(self.peaks[i])
            valley_HM = (max_peak+self.cropped_profile_y[valley])/2
            first_intersection = self.find_intersection(self.cropped_profile_x[self.peaks[i]:valley+1], self.cropped_profile_y[self.peaks[i]:valley+1], valley_HM)
            self.valley_HM_points.append((first_intersection, valley_HM))
            second_intersection = self.find_intersection(self.cropped_profile_x[valley:self.peaks[i+1]+1], self.cropped_profile_y[valley:self.peaks[i+1]+1], valley_HM)
            self.valley_HM_points.append((second_intersection, valley_HM))
    
    def analyze_profile(self, start, end):
        self.cropped_profile_x = self.profile_x[start:end+1]
        if self.pixel_size:
            self.xcropped_profile_x = self.cropped_profile_x*self.pixel_size
        self.cropped_profile_y = self.profile_y[start:end+1]

        self.find_myosin_peaks()
        self.find_intersarcomere_valleys()
        self.find_myosin_HM_points()
        self.find_valey_HM_points()

        self.H_zone = [self.cropped_profile_x[self.peaks[i+1]]-self.cropped_profile_x[self.peaks[i]] for i in range(0,len(self.peaks),2)]
        self.A_band = [self.HM_points[i+1][0]-self.HM_points[i][0] for i in range(0,len(self.HM_points),2)]
        self.I_band = [self.valley_HM_points[i+1][0]-self.valley_HM_points[i][0] for i in range(0,len(self.valley_HM_points),2)]
        self.sarcomere = [self.cropped_profile_x[self.valleys[i+1]]-self.cropped_profile_x[self.valleys[i]] for i in range(0,len(self.valleys)-1,1)]

        self.controller.show_results(self.profile_x, self.profile_y, np.array(self.peaks)+start, np.array(self.valleys)+start,
                                      np.array(self.HM_points), np.array(self.valley_HM_points))       
    
    def save_data(self, path, vertices):
        fig_save, ax_save = plt.subplots(1, 1, figsize=(5, 5))
        ax_save.imshow(self.image, cmap="Greys_r")
        x = [c for (c,r) in vertices]
        y = [r for (c,r) in vertices]
        ax_save.plot(x,y, c='red')
        img_path = path.split(".")[0]+".tif"
        plt.savefig(img_path)

        columns = ['H zone', 'A band', 'I band', 'Sarcomere']
        aux_dict1 = {'H zone': self.H_zone, 'A band': self.A_band, 'Sarcomere': self.sarcomere}
        aux_dict2 = {'I band': self.I_band}
        df1 = pd.DataFrame(aux_dict1)
        df2 = pd.DataFrame(aux_dict2)
        df = pd.concat([df1,df2], axis=1)[columns]

        df.to_excel(path, index=False)
   