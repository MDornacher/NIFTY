import logging

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector, TextBox

from nifty.io import save_measurements
from nifty.prints import (print_measurements,
                          print_navigation_keyboard_shortcuts)

LOGGER = logging.getLogger(__name__)


class PlotUI:
    def __init__(self, config, output_file, measurements=None, title=None):
        # parse input
        self.config = config
        if measurements is not None:
            self.config.measurements = measurements
            self.validate_measurements()
        self.output_file = output_file

        # create figure
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, figsize=(8, 6))  # , constrained_layout=True)
        self.fig.canvas.set_window_title('NIFTY')
        if title is not None:
            self.fig.suptitle(title)  # TODO: fig title is fig centered while ax titles are ax centered => unaligned
        plt.get_current_fig_manager().window.wm_iconbitmap("icon.ico")
        plt.get_current_fig_manager().window.state('zoomed')

        # define events
        self.cid = self.fig.canvas.mpl_connect('key_press_event', self.on_press)
        # TODO: add 'close_event' to autosave measurements
        self.span_fit = SpanSelector(self.ax2, self.onselect_fit_range, 'horizontal', useblit=True,
                                     rectprops=dict(alpha=0.5, facecolor='yellow'))
        self.span_ew = SpanSelector(self.ax3, self.onselect_ew_range, 'horizontal', useblit=True,
                                    rectprops=dict(alpha=0.5, facecolor='yellow'))

        # text box widget
        # TODO: the whole textbox is super hacky and some of the settings dont work right yet
        plt.subplots_adjust(bottom=0.1)
        axbox = plt.axes([0.1, 0.01, 0.8, 0.05])
        self.text_box = TextBox(axbox, 'Notes:', initial="")
        self.text_box.on_submit(self.submit_text)
        self.text_box.set_active(False)

        self.reset_plot()
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

        self.reset_textbox()

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

        # TODO: those limits are just temporarily
        self.ax1.set_ylim([-0.2, 1.7])

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
            self.span_ew.set_active(True)

        else:
            self.ax3.plot(self.config.xs[self.config.masks["data"]],
                          self.config.ys[self.config.masks["data"]],
                          '-', color='C0')
            # "block" third plot if no fit
            self.span_ew.set_active(False)

        self.plot_dibs(self.ax3)

        if self.config.stellar_lines is not None:
            self.plot_stellar_lines(self.ax3)

        self.plot_notes(self.ax3)
        self.plot_results(self.ax3)
        self.plot_marked(self.ax3)

    def onselect_fit_range(self, xmin, xmax):
        # get x and y values of selection
        indmin, indmax = np.searchsorted(self.config.xs, (xmin, xmax))
        indmin = max(0, indmin - 2)
        indmax = min(len(self.config.xs) - 1, indmax)

        thisx = self.config.xs[indmin:indmax]
        thisy = self.config.ys[indmin:indmax]

        # append to fit region and attempt to fit
        # TODO: only add points once, don't double add them if they are selected again
        self.config.xs_fit_data = np.append(thisx, self.config.xs_fit_data)
        self.config.ys_fit_data = np.append(thisy, self.config.ys_fit_data)
        # noinspection PyTupleAssignmentBalance
        self.config.slope, self.config.intercept = np.polyfit(self.config.xs_fit_data, self.config.ys_fit_data, 1)
        self.config.ys_fit = np.array([self.config.slope * x + self.config.intercept for x in self.config.xs])
        self.config.ys_norm = self.config.ys / self.config.ys_fit

        # redraw relevant subplots
        self.reset_plot_middle()
        self.plot_fit_data()
        # self.ax2.legend()
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
        # self.ax3.legend()
        self.fig.canvas.draw()

    def plot_ew_data(self, indmin, indmax, ew):
        self.ax3.fill_between(self.config.xs, self.config.ys_norm, 1,
                              where=(self.config.xs > self.config.xs[indmin]) & (self.config.xs <= self.config.xs[indmax]),
                              color='C2', alpha=0.5, label='EW={:6.6f}'.format(ew))

    def submit_text(self, text):
        self.config.measurements[str(self.config.selected_dib)]["notes"] = text
        # TODO: resetting colors has no effect, but works when activating textbox
        self.text_box.color = '.95'
        self.text_box.hovercolor = '.95'
        self.reset_plot_bottom()
        self.plot_notes(self.ax3)
        self.fig.canvas.draw()
        self.text_box.set_active(False)

    def activate_textbox(self):
        self.text_box.set_active(True)
        self.text_box.color = '1'
        self.fig.canvas.draw()

    def reset_textbox(self):
        self.text_box.set_val(self.config.measurements[str(self.config.selected_dib)]["notes"])

    def plot_dibs(self, ax):
        for dib in self.config.dibs[self.config.masks["dibs"]]:
            ax.axvline(dib, color='C3', alpha=0.5)
        ax.axvline(self.config.selected_dib, color='C1', alpha=0.5, linewidth=1.5)
        ax.axvline(self.config.selected_dib, color='C3', alpha=0.5)

    def plot_stellar_lines(self, ax):
        for stellar_line in self.config.stellar_lines[self.config.masks["stellar_lines"]]:
            ax.axvline(stellar_line, color='C4', alpha=0.5)

    def plot_notes(self, ax):
        bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9)
        s = self.config.measurements[str(self.config.selected_dib)]['notes'].strip()
        ax.text(.05, .95, s, transform=ax.transAxes, ha="left", va="top", bbox=bbox_props)

    def plot_results(self, ax):
        bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9)
        s = "\n".join([str(result) for result in self.config.measurements[str(self.config.selected_dib)]['results']])
        ax.text(.95, .95, s, transform=ax.transAxes, ha="right", va="top", bbox=bbox_props)

    def plot_marked(self, ax):
        if not self.config.measurements[str(self.config.selected_dib)]["marked"]:
            color = "gray"
        else:
            color = "C3"
        ax.plot(0.05, 0.05, marker="o", markersize="15", color=color, markeredgewidth=1., markeredgecolor="k", transform=ax.transAxes)

    def on_press(self, event):
        if hasattr(self, "text_box") and self.text_box.get_active():
            print("textbox is active")
            return
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
            self.plot_marked(self.ax3)
            self.fig.canvas.draw()
            return
        if event.key == 'n':
            # TODO: the first n will always be printed in textbox
            self.activate_textbox()
            return
        if event.key == 'backspace':
            self.delete_last_measurement_result()
            self.reset_plot()
            return
        if event.key == ' ':
            LOGGER.info(f'Saving measurements to {self.output_file}')
            save_measurements(self.config.measurements, self.output_file)
            print_measurements(self.config.measurements)
            return
        if event.key == 'escape':
            # TODO: 'Process finished with exit code -1073741819 (0xC0000005)' but closing it with X button works fine
            plt.close('all')
            return
        if event.key == 'alt':
            return
        print(f"Unrecognized keyboard shortcut ({event.key}). Press 'h' for full list of shortcuts.")

    def delete_last_measurement_result(self):
        if self.config.measurements[str(self.config.selected_dib)]["results"]:
            last_measurement = self.config.measurements[str(self.config.selected_dib)]["results"].pop()
            print(f'Removed the measurement {last_measurement} for DIB {self.config.selected_dib}'
                  f' - {len(self.config.measurements[str(self.config.selected_dib)]["results"])} result(s) remaining.')
        else:
            print(f'No measurement result for DIB {self.config.selected_dib} found.')

    def toggle_measurement_mark(self):
        if self.config.measurements[str(self.config.selected_dib)]["marked"]:
            self.config.measurements[str(self.config.selected_dib)]["marked"] = False
        else:
            self.config.measurements[str(self.config.selected_dib)]["marked"] = True
