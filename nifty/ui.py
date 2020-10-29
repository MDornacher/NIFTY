import logging

import numpy as np
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector

from nifty.io import save_measurements
from nifty.prints import print_navigation_keyboard_shortcuts, print_measurements


LOGGER = logging.getLogger(__name__)


class PlotUI:
    def __init__(self, config, output_file, results=None):
        # parse input
        self.config = config
        if results is not None:
            self.config.measurements.results = results
            self.validate_measurements()
        self.output_file = output_file

        # create figure
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, figsize=(8, 6), constrained_layout=True)
        self.fig.canvas.set_window_title('NIFTY')

        self.reset_plot()

        # define events
        self.cid = self.fig.canvas.mpl_connect('key_press_event', self.on_press)
        self.span_fit = SpanSelector(self.ax2, self.onselect_fit_range, 'horizontal', useblit=True,
                                     rectprops=dict(alpha=0.5, facecolor='yellow'))
        self.span_ew = SpanSelector(self.ax3, self.onselect_ew_range, 'horizontal', useblit=True,
                                    rectprops=dict(alpha=0.5, facecolor='yellow'))
        plt.show()

    def validate_measurements(self):
        dibs_test_list = [str(dib) for dib in self.config.dibs]
        results_test_list = list(self.config.measurements.keys())

        dibs_test_list.sort()
        results_test_list.sort()

        if dibs_test_list != results_test_list:
            LOGGER.warning('The features and the loaded measurements do not match. '
                           'Therefore the measurements will be ignored '
                           'and when saving them the output file will be overwritten.')
            self.config.reset_measurements()

    def reset_plot(self):
        self.config.reset_fit()
        self.config.calculate_masks()

        self.reset_plot_top()
        self.reset_plot_middle()
        self.reset_plot_bottom()

        self.fig.canvas.draw()

    def reset_plot_top(self):
        self.ax1.clear()
        self.ax1.set_title('Full Spectrum')
        self.ax1.grid()
        if self.config.ref_data:
            self.ax1.plot(self.config.xs_ref, self.config.ys_ref, '-', color='k', alpha=0.5)
        self.ax1.plot(self.config.xs, self.config.ys, '-', color='C0')
        self.ax1.plot(self.config.dibs, [1.1] * len(self.config.dibs), 'k|')
        self.ax1.plot(self.config.selected_dib, [1.1], 'rv')
        # self.ax1.axvspan(self.config.x_range_min, self.config.x_range_max, alpha=0.3, color='yellow')
        if self.config.x_range_min > self.config.xs.min():
            self.ax1.axvspan(self.config.xs.min(), self.config.x_range_min, alpha=0.15, color='black')
        if self.config.x_range_max < self.config.xs.max():
            self.ax1.axvspan(self.config.x_range_max, self.config.xs.max(), alpha=0.15, color='black')

    def reset_plot_middle(self):
        self.ax2.clear()
        self.ax2.set_title('DIB Region')
        self.ax2.grid()

        if self.config.ref_data:
            self.ax2.plot(self.config.xs_ref[self.config.masks["ref"]],
                          self.config.ys_ref[self.config.masks["ref"]],
                          '-', color='k', alpha=0.5)

        self.ax2.plot(self.config.xs[self.config.masks["data"]],
                      self.config.ys[self.config.masks["data"]],
                      '-', color='C0')

        self.plot_dibs(self.ax2)

        if self.config.stellar_lines is not None:
            self.plot_stellar_lines(self.ax2)

    def reset_plot_bottom(self):
        self.ax3.clear()
        self.ax3.set_title('Local Norm')
        self.ax3.grid()

        if self.config.ref_data:
            self.ax3.plot(self.config.xs_ref[self.config.masks["ref"]],
                          self.config.ys_ref[self.config.masks["ref"]],
                          '-', color='k', alpha=0.5)

        if self.config.ys_norm.size > 0:
            self.ax3.plot(self.config.xs[self.config.masks["data"]],
                          self.config.ys_norm[self.config.masks["data"]],
                          '-', color='C0')

        else:
            self.ax3.plot(self.config.xs[self.config.masks["data"]],
                          self.config.ys[self.config.masks["data"]],
                          '-', color='C0')
            # "block" third plot if no fit
            block_x_min = self.config.xs[self.config.masks["data"]].min()
            block_x_max = self.config.xs[self.config.masks["data"]].max()
            self.ax3.axvspan(block_x_min, block_x_max, alpha=0.15, color='black')
            # self.ax3.text(0.5, 0.5, 'BLOCKED', fontsize=32, horizontalalignment='center', verticalalignment='center', transform=self.ax3.transAxes)

        self.plot_dibs(self.ax3)

        if self.config.stellar_lines is not None:
            self.plot_stellar_lines(self.ax3)

    def onselect_fit_range(self, xmin, xmax):
        # get x and y values of selection
        indmin, indmax = np.searchsorted(self.config.xs, (xmin, xmax))
        indmin = max(0, indmin - 2)
        indmax = min(len(self.config.xs) - 1, indmax)

        thisx = self.config.xs[indmin:indmax]
        thisy = self.config.ys[indmin:indmax]

        # append to fit region and attempt to fit
        self.config.xs_fit_data = np.append(thisx, self.config.xs_fit_data)
        self.config.ys_fit_data = np.append(thisy, self.config.ys_fit_data)
        # noinspection PyTupleAssignmentBalance
        self.config.slope, self.config.intercept = np.polyfit(self.config.xs_fit_data, self.config.ys_fit_data, 1)
        self.config.ys_fit = np.array([self.config.slope * x + self.config.intercept for x in self.config.xs])
        self.config.ys_norm = self.config.ys / self.config.ys_fit

        # redraw relevant subplots
        self.reset_plot_middle()
        self.plot_fit_data()
        self.ax2.legend()
        self.reset_plot_bottom()
        self.fig.canvas.draw()

    def plot_fit_data(self):
        self.ax2.plot(self.config.xs[self.config.masks["data"]],
                      self.config.ys_fit[self.config.masks["data"]],
                      '-', color='k', alpha=0.5, label='k={:6.6f}'.format(self.config.slope))
        self.ax2.plot(self.config.xs_fit_data,
                      self.config.ys_fit_data,
                      'o', color='C1', alpha=0.5)

    def onselect_ew_range(self, xmin, xmax):
        # get x and y values of selection
        indmin, indmax = np.searchsorted(self.config.xs, (xmin, xmax))
        indmin = max(0, indmin - 2)
        indmax = min(len(self.config.xs) - 1, indmax)

        diff = (1 - self.config.ys_norm[indmin:indmax]) * (self.config.xs[1] - self.config.xs[0])
        ew = sum(diff)
        self.config.measurements[str(self.config.selected_dib)]["results"].append(ew)

        self.reset_plot_bottom()
        self.plot_ew_data(indmin, indmax, ew)
        self.ax3.legend()
        self.fig.canvas.draw()

    def plot_ew_data(self, indmin, indmax, ew):
        self.ax3.fill_between(self.config.xs, self.config.ys_norm, 1,
                              where=(self.config.xs > self.config.xs[indmin]) & (self.config.xs <= self.config.xs[indmax]),
                              color='C2', alpha=0.5, label='EW={:6.6f}'.format(ew))

    def plot_dibs(self, ax):
        for dib in self.config.dibs[self.config.masks["dibs"]]:
            ax.axvline(dib, color='C3', alpha=0.3)
        ax.axvline(self.config.selected_dib, color='C3', alpha=0.5)

    def plot_stellar_lines(self, ax):
        for stellar_line in self.config.stellar_lines[self.config.masks["stellar_lines"]]:
            ax.axvline(stellar_line, color='C0', alpha=0.3)

    def on_press(self, event):
        if event.key == 'h':
            print_navigation_keyboard_shortcuts()
            return
        if event.key == 'r':
            self.reset_plot()
            return
        if event.key == 'left':
            self.config.previous_dib()
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'right':
            self.config.next_dib()
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'up':
            self.config.shift_ref_data_up()
            self.reset_plot()
            return
        if event.key == 'down':
            self.config.shift_ref_data_down()
            self.reset_plot()
            return
        if event.key == 'alt+up':
            self.config.shift_spectral_lines_up()
            self.reset_plot()
            return
        if event.key == 'alt+down':
            self.config.shift_spectral_lines_down()
            self.reset_plot()
            return
        if event.key == '+':
            self.config.decrease_x_range()
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == '-':
            self.config.increase_x_range()
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'm':
            self.toggle_measurement_mark()
            return
        if event.key == 'n':
            self.add_note_to_measurement()
            return
        if event.key == 'backspace':
            self.delete_last_measurement_result()
            return
        if event.key == ' ':
            print(f'Saving measurements to {self.output_file}')
            save_measurements(self.config.measurements, self.output_file)
            print_measurements(self.config.measurements)
            return
        if event.key == 'escape':
            # TODO: 'Process finished with exit code -1073741819 (0xC0000005)' but closing it with X button works fine
            plt.close('all')
        print("Unrecognized keyboard shortcuts. Press 'h' for full list of shortcuts.")

    def delete_last_measurement_result(self):
        if self.config.measurements[str(self.config.selected_dib)]["results"]:
            last_measurement = self.config.measurements[str(self.config.selected_dib)]["results"].pop()
            print(f'Removed the measurement {last_measurement} for DIB {self.config.selected_dib}'
                  f' - {len(self.config.measurements[str(self.config.selected_dib)]["results"])} result(s) remaining.')
        else:
            print(f'No measurement result for DIB {self.config.selected_dib} found.')

    def add_note_to_measurement(self):
        note = input(f"Add note to feature {self.config.selected_dib}: ").strip()
        self.config.measurements[str(self.config.selected_dib)]["notes"] += note + "\n"
        print(f"Full note:\n{self.config.measurements[str(self.config.selected_dib)]['notes']}")

    def toggle_measurement_mark(self):
        if self.config.measurements[str(self.config.selected_dib)]["marked"]:
            print(f"Removed mark from feature {self.config.selected_dib}.")
            self.config.measurements[str(self.config.selected_dib)]["marked"] = False
        else:
            print(f"Marked feature {self.config.selected_dib}.")
            self.config.measurements[str(self.config.selected_dib)]["marked"] = True


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
            print("No ref data available for shifting.")
            return
        step_size = self.xs_ref[1] - self.xs_ref[0]
        self.xs_ref += step_size

    def shift_ref_data_down(self):
        if not self.ref_data:
            print("No ref data available for shifting.")
            return
        step_size = self.xs[1] - self.xs[0]
        self.stellar_lines -= step_size

    def shift_spectral_lines_up(self):
        if not self.ref_data:
            print("No stellar lines available for shifting.")
            return
        step_size = self.xs[1] - self.xs[0]
        self.stellar_lines += step_size

    def shift_spectral_lines_down(self):
        if not self.ref_data:
            print("No stellar lines available for shifting.")
            return
        step_size = self.xs[1] - self.xs[0]
        self.stellar_lines -= step_size
