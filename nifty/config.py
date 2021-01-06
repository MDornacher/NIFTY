import logging

import numpy as np

LOGGER = logging.getLogger(__name__)
RANGE_STEP_SIZE = 0.1
RANGE_SHIFT_SIZE = 0.1
VELOCITY_SHIFT_STEP_SIZE = 1  # km/s
SPEED_OF_LIGHT = 299792.458  # km/s


class PlotConfig:
    def __init__(self, xs=None, ys=None, dibs=None, xs_ref=None, ys_ref=None,
                 stellar_lines=None, interstellar_lines=None):
        # TODO: basic validation, e.g. raise error if dibs is empty
        # TODO: unify 'stellar_lines' and 'stellar'
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
            self.xs_ref_base = np.copy(xs_ref)
            self.ys_ref_base = np.copy(ys_ref)
            self.xs_ref = np.copy(self.xs_ref_base)
            self.ys_ref = np.copy(self.ys_ref_base)
        self.stellar_lines_base = stellar_lines
        self.stellar_lines = np.copy(stellar_lines)
        self.interstellar_lines = interstellar_lines

        # initialize measurements
        self.measurements = None
        self.reset_measurements()

        # starting velocities for doppler shift
        self.velocity_shifts = None
        self.reset_velocity_shifts()

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
            "interstellar_lines": None,
        }

    def reset_measurements(self):
        # TODO: using str(float) is not a good idea without some rounding, unfortunately this is already used a lot
        self.measurements = {str(dib): {"ew": [],
                                        "notes": "",
                                        "marked": False,
                                        "mode": [],
                                        "range": [],
                                        "fwhm": []}
                             for dib in self.dibs}

    def validate_measurements(self):
        dibs_test_list = [str(dib) for dib in self.dibs]
        results_test_list = list(self.measurements.keys())

        dibs_test_list.sort()
        results_test_list.sort()

        if dibs_test_list != results_test_list:
            LOGGER.warning('The features and the loaded measurements do not match. '
                           'Therefore the measurements will be ignored '
                           'and when saving them the output file will be overwritten.')
            self.reset_measurements()

    def reset_velocity_shifts(self):
        self.velocity_shifts = {
            "data": 0.,
            "ref": 0.,
            "stellar": 0.,
        }

    def validate_velocity_shifts(self):
        for key in self.velocity_shifts.keys():
            if key not in ["data", "ref", "stellar"]:
                LOGGER.warning(f'The velocity shift {key} is unknown. '
                               'Therefore the velocity shifts will be ignored '
                               'and when saving them the output file will be overwritten.')
                self.reset_velocity_shifts()

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
        if self.interstellar_lines is not None:
            self.masks["interstellar_lines"] = (self.interstellar_lines > self.x_range_min) & \
                                          (self.interstellar_lines < self.x_range_max)

    def reset_fit(self):
        self.slope = None
        self.intercept = None
        self.fit_indices = set()
        self.xs_fit_data = np.array([])
        self.ys_fit_data = np.array([])
        self.ys_fit = np.array([])
        self.ys_norm = np.array([])

    def next_dib(self, step=1):
        self.selection = (self.selection + step) % len(self.dibs)
        self.selected_dib = self.dibs[self.selection]

    def previous_dib(self, step=1):
        self.selection = (self.selection - step) % len(self.dibs)
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
        self.apply_velocity_shifts(mode="data")

    def shift_data_down(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        self.velocity_shifts["data"] -= step_size
        self.apply_velocity_shifts(mode="data")

    def shift_ref_data_up(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        if not self.ref_data:
            LOGGER.info("No ref data available for shifting.")
            return
        self.velocity_shifts["ref"] += step_size
        self.apply_velocity_shifts(mode="ref")

    def shift_ref_data_down(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        if not self.ref_data:
            LOGGER.info("No ref data available for shifting.")
            return
        self.velocity_shifts["ref"] -= step_size
        self.apply_velocity_shifts(mode="ref")

    def shift_stellar_lines_up(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        self.velocity_shifts["stellar"] += step_size
        self.apply_velocity_shifts(mode="stellar")

    def shift_stellar_lines_down(self, step_size=VELOCITY_SHIFT_STEP_SIZE):
        self.velocity_shifts["stellar"] -= step_size
        self.apply_velocity_shifts(mode="stellar")

    def apply_velocity_shifts(self, mode):
        """
        Only applies velocity shift to the mode selected wavelengths
        """
        # TODO: the sign in the shift factor might be wrong
        if mode == "data":
            shift_factor_data = (1.0 + self.velocity_shifts["data"] / SPEED_OF_LIGHT)
            self.xs = self.xs_base * shift_factor_data
        if mode == "stellar" and self.stellar_lines is not None:
            shift_factor_stellar = (1.0 + self.velocity_shifts["stellar"] / SPEED_OF_LIGHT)
            self.stellar_lines = self.stellar_lines_base * shift_factor_stellar
        if mode == "ref" and self.ref_data:
            shift_factor_ref = (1.0 + self.velocity_shifts["ref"] / SPEED_OF_LIGHT)
            self.xs_ref = self.xs_ref_base * shift_factor_ref
