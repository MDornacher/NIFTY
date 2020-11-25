import logging

import numpy as np
from PyAstronomy import pyasl  # TODO: replace me?

LOGGER = logging.getLogger(__name__)
RANGE_STEP_SIZE = 0.1
RANGE_SHIFT_SIZE = 0.1
VELOCITY_SHIFT_STEP_SIZE = 1  # km/s


class PlotConfig:
    def __init__(self, xs=None, ys=None, dibs=None, xs_ref=None, ys_ref=None, stellar_lines=None):
        # parse parameters
        self.xs_base = xs
        self.ys_base = ys
        self.dibs = dibs
        self.xs = np.copy(self.xs_base)
        self.ys = np.copy(self.ys_base)
        if xs_ref is None or ys_ref is None:
            self.ref_data = False
            self.xs_ref_base = None
            self.ys_ref_base = None
            self.xs_ref = None
            self.ys_ref = None
        else:
            self.ref_data = True
            self.xs_ref_base = xs_ref
            self.ys_ref_base = ys_ref
            self.xs_ref = np.copy(self.xs_ref_base)
            self.ys_ref = np.copy(self.ys_ref_base)
        self.stellar_lines = stellar_lines

        # initialize measurements
        self.measurements = None
        self.reset_measurements()

        # parameter for norm plot
        self.slope = None
        self.intercept = None
        self.fit_indices = set()
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
        self.x_range_shift = 0.
        self.update_x_range()

        # create masks
        self.masks = {
            "data": None,
            "ref": None,
            "dibs": None,
            "stellar_lines": None,
        }

        # starting velocities for doppler shift
        self.velocity_shifts = {
            "data": 0.,
            "ref": 0.,
        }

    def reset_measurements(self):
        self.measurements = {str(dib): {"ew": [],
                                        "notes": "",
                                        "marked": False,
                                        "mode": [],
                                        "range": [],
                                        "fwhm": []}
                             for dib in self.dibs}

    def reset_x_range_shift(self):
        self.x_range_shift = 0.

    def update_x_range(self):
        self.x_range_min = self.selected_dib * (1 - self.x_range_factor) + self.x_range_shift
        self.x_range_max = self.selected_dib * (1 + self.x_range_factor) + self.x_range_shift

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

    def reset_fit(self):
        self.slope = None
        self.intercept = None
        self.fit_indices = set()
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

    def increase_x_range(self, step_size=RANGE_STEP_SIZE):
        self.x_range_factor *= 1 + step_size

    def decrease_x_range(self, step_size=RANGE_STEP_SIZE):
        self.x_range_factor *= 1 - step_size

    # TODO: add some catch in case the range is shifted completely beyond the spectrum
    def shift_x_range_up(self, step_size=RANGE_SHIFT_SIZE):
        shift = (self.x_range_max - self.x_range_min) * step_size
        self.x_range_shift += shift

    def shift_x_range_down(self, step_size=RANGE_SHIFT_SIZE):
        shift = (self.x_range_max - self.x_range_min) * step_size
        self.x_range_shift -= shift

    def shift_data_up(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        self.velocity_shifts["data"] += step_size
        self.apply_velocity_shifts()

    def shift_data_down(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        self.velocity_shifts["data"] -= step_size
        self.apply_velocity_shifts()

    def shift_ref_data_up(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        if not self.ref_data:
            LOGGER.info("No ref data available for shifting.")
            return
        self.velocity_shifts["ref"] += step_size
        self.apply_velocity_shifts()

    def shift_ref_data_down(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        if not self.ref_data:
            LOGGER.info("No ref data available for shifting.")
            return
        self.velocity_shifts["ref"] -= step_size
        self.apply_velocity_shifts()

    def apply_velocity_shifts(self):
        self.ys, self.xs = pyasl.dopplerShift(self.xs_base, self.ys_base,
                                              self.velocity_shifts["data"])
        if self.ref_data:
            self.ys_ref, self.xs_ref = pyasl.dopplerShift(self.xs_ref_base, self.ys_ref_base,
                                                          self.velocity_shifts["ref"])
