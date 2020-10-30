import logging

import numpy as np
from scipy import signal

LOGGER = logging.getLogger(__name__)


class PlotConfig:
    def __init__(self, xs=None, ys=None, dibs=None, xs_ref=None, ys_ref=None, stellar_lines=None):
        # parse parameters
        # TODO: distinguish between missing xs/ys and missing dibs_selection
        if any((xs is None, ys is None, dibs is None)):
            self.create_spectrum()
        else:
            self.xs = xs
            self.ys = ys
            self.dibs = dibs
        if xs_ref is None or ys_ref is None:
            self.ref_data = False
        else:
            self.ref_data = True
            self.xs_ref = xs_ref
            self.ys_ref = ys_ref
        self.stellar_lines = stellar_lines

        # initialize measurements
        self.measurements = None
        self.reset_measurements()

        # parameter for norm plot
        self.slope = None
        self.intercept = None
        self.xs_fit_data = np.array([])
        self.ys_fit_data = np.array([])
        self.ys_fit = np.array([])

        # parameter for measurement plot
        self.ys_norm = np.array([])

        # additional parameters
        self.selection = 0
        self.selected_dib = self.dibs[self.selection]
        self.x_range_factor = 0.01
        self.y_range_factor = 1.1

        # derived parameters
        self.x_range_min = None
        self.x_range_max = None
        self.update_x_range()

        # create masks
        self.masks = {
            "data": None,
            "ref": None,
            "dibs": None,
            "stellar_lines": None,
        }

    def reset_measurements(self):
        self.measurements = {str(dib): {"results": [], "notes": "", "marked": False} for dib in self.dibs}

    def update_x_range(self):
        self.x_range_min = self.selected_dib * (1 - self.x_range_factor)
        self.x_range_max = self.selected_dib * (1 + self.x_range_factor)

    # noinspection PyTypeChecker
    def calculate_masks(self):
        self.masks["data"] = (self.xs > self.x_range_min) & \
                             (self.xs < self.x_range_max)
        if self.ref_data is True:
            self.masks["ref"] = (self.xs_ref > self.x_range_min) & \
                                (self.xs_ref < self.x_range_max)
        self.masks["dibs"] = (self.dibs > self.x_range_min) & \
                             (self.dibs < self.x_range_max)
        if self.stellar_lines is not None:
            self.masks["stellar_lines"] = (self.stellar_lines > self.x_range_min) & \
                                          (self.stellar_lines < self.x_range_max)

    def create_spectrum(self, x_range=(100, 200), sigma_range=(1, 5), strength_range=(0, 1), number_of_values=300,
                        number_of_dibs=3, sn=10):
        if x_range is None:
            x_range_min, x_range_max = (100, 500)
        else:
            x_range_min, x_range_max = x_range

        self.xs = np.linspace(x_range_min, x_range_max, number_of_values)
        noise = np.random.rand(self.xs.size)
        self.ys = 1 + noise / sn - np.mean(noise / sn)

        sigma_min, sigma_max = sigma_range
        strength_min, strength_max = strength_range
        self.dibs = []
        for i in range(number_of_dibs):
            sigma = sigma_min + np.random.rand() * sigma_max
            strength = strength_min + np.random.rand() * strength_max
            gaussian = signal.gaussian(number_of_values * 2, sigma)
            dib_index = int(np.random.rand() * number_of_values)
            self.dibs.append(self.xs[dib_index])
            self.ys = self.ys - strength * gaussian[number_of_values - dib_index:2*number_of_values - dib_index]
        self.dibs.sort()
        self.dibs = np.array(self.dibs)

    def reset_fit(self):
        self.slope = None
        self.intercept = None
        self.xs_fit_data = np.array([])
        self.ys_fit_data = np.array([])
        self.ys_fit = np.array([])
        self.ys_norm = np.array([])

    def next_dib(self):
        self.selection = (self.selection + 1) % len(self.dibs)
        self.selected_dib = self.dibs[self.selection]

    def previous_dib(self):
        self.selection = (self.selection - 1) % len(self.dibs)
        self.selected_dib = self.dibs[self.selection]

    def increase_x_range(self):
        self.x_range_factor *= 1.1

    def decrease_x_range(self):
        self.x_range_factor *= 0.9

    def increase_y_range(self):
        self.y_range_factor += 0.1

    def decrease_y_range(self):
        self.y_range_factor -= 0.1

    def shift_ref_data_up(self):
        if not self.ref_data:
            LOGGER.info("No ref data available for shifting.")
            return
        step_size = self.xs_ref[1] - self.xs_ref[0]
        self.xs_ref += step_size

    def shift_ref_data_down(self):
        if not self.ref_data:
            LOGGER.info("No ref data available for shifting.")
            return
        step_size = self.xs[1] - self.xs[0]
        self.stellar_lines -= step_size

    def shift_spectral_lines_up(self):
        if self.stellar_lines is None:
            LOGGER.info("No stellar lines available for shifting.")
            return
        step_size = self.xs[1] - self.xs[0]
        self.stellar_lines += step_size

    def shift_spectral_lines_down(self):
        if self.stellar_lines is None:
            LOGGER.info("No stellar lines available for shifting.")
            return
        step_size = self.xs[1] - self.xs[0]
        self.stellar_lines -= step_size
