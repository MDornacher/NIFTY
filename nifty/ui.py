import logging

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector, TextBox
from matplotlib.offsetbox import AnchoredText

from nifty.calc import lin_interp
from nifty.config import VELOCITY_SHIFT_STEP_SIZE, RANGE_STEP_SIZE, RANGE_SHIFT_SIZE
from nifty.io import save_data
from nifty.prints import (print_measurements, print_velocity_shifts,
                          print_navigation_keyboard_shortcuts)

LOGGER = logging.getLogger(__name__)


class PlotUI:
    def __init__(self, config, output_file, measurements=None, velocity_shifts=None, title=None, file_names=None):
        # parse input
        self.config = config
        if measurements is not None:
            self.config.measurements = measurements
            self.config.validate_measurements()
        if velocity_shifts is not None:
            self.config.velocity_shifts = velocity_shifts
            self.config.validate_velocity_shifts()
        self.output_file = output_file
        self.file_names = file_names

        # create figure
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, figsize=(8, 6))  # , constrained_layout=True)
        self.fig.canvas.set_window_title('NIFTY')
        # TODO: use file_names instead if available
        if title is not None:
            self.fig.suptitle(title)  # TODO: fig title is fig centered while ax titles are ax centered => unaligned
        # plt.get_current_fig_manager().window.wm_iconbitmap("icon.ico")  # TODO: somehow broken
        # plt.get_current_fig_manager().window.state('zoomed')  # TODO: only works on windows?
        mng = plt.get_current_fig_manager()
        mng.resize(*mng.window.maxsize())

        # define events
        self.cid = self.fig.canvas.mpl_connect('key_press_event', self.on_press)
        # TODO: add 'close_event' to autosave measurements
        self.span_fit = SpanSelector(self.ax2, self.on_select_fit_range, 'horizontal', useblit=True,
                                     rectprops=dict(alpha=0.5, facecolor='yellow'))
        self.span_measurement = SpanSelector(self.ax3, self.on_select_measurement_range, 'horizontal', useblit=True,
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

    def reset_plot(self):
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
            ref_label = f'Reference Spectrum ({self.file_names["ref"]})' if self.file_names is not None else 'Reference Spectrum'
            self.ax1.plot(self.config.xs_ref, self.config.ys_ref, '--', color='k', alpha=0.5,
                          label=ref_label)
        data_label = f'Test Spectrum ({self.file_names["data"]})' if self.file_names is not None else 'Test Spectrum'
        self.ax1.plot(self.config.xs, self.config.ys, '-', color='C0',
                      label=data_label)
        self.ax1.plot(self.config.dibs, [1.1] * len(self.config.dibs), 'k|', label='Test Features')
        self.ax1.plot(self.config.selected_dib, [1.1], 'rv', label='Selected Feature')
        if self.config.x_range_min > self.config.xs.min():
            self.ax1.axvspan(self.config.xs.min(), self.config.x_range_min, alpha=0.15, color='black')
        if self.config.x_range_max < self.config.xs.max():
            self.ax1.axvspan(self.config.x_range_max, self.config.xs.max(), alpha=0.15, color='black')

        # TODO: those limits are just temporarily
        self.ax1.set_xlim([self.config.xs.min(), self.config.xs.max()])
        self.ax1.set_ylim([-0.2, 1.7])
        self.ax1.legend(loc='lower right')  # ncol=5, mode='expand'

    def reset_plot_middle(self):
        # TODO: overwrite ylim to better zoom into feature
        self.ax2.clear()
        self.ax2.set_title('Feature Region')
        self.ax2.grid()

        if self.config.ref_data:
            self.ax2.plot(self.config.xs_ref[self.config.masks["ref"]],
                          self.config.ys_ref[self.config.masks["ref"]],
                          '--', color='k', alpha=0.5, label='Reference Spectrum')

        self.ax2.plot(self.config.xs[self.config.masks["data"]],
                      self.config.ys[self.config.masks["data"]],
                      '-', color='C0', label='Test Spectrum')

        self.plot_dibs(self.ax2)

        if self.config.stellar_lines is not None:
            self.plot_stellar_lines(self.ax2)

        if self.config.interstellar_lines is not None:
            self.plot_interstellar_lines(self.ax2)

        if self.config.ys_norm.size > 0:
            self.plot_fit_data(self.ax2)

        if any(self.config.velocity_shifts.values()):
            self.plot_doppler_shift(self.ax2)

        self.ax2.set_xlim(self.config.xs[self.config.masks["data"]].min(),
                          self.config.xs[self.config.masks["data"]].max())
        self.ax2.legend(loc='lower right')

    def reset_plot_bottom(self):
        # TODO: should get some mask independent xlim
        self.ax3.clear()
        self.ax3.set_title('Local Norm')
        self.ax3.grid()

        if self.config.ref_data:
            self.ax3.plot(self.config.xs_ref[self.config.masks["ref"]],
                          self.config.ys_ref[self.config.masks["ref"]],
                          '--', color='k', alpha=0.5, label='Reference Spectrum')

        if self.config.ys_norm.size > 0:
            self.ax3.plot(self.config.xs[self.config.masks["data"]],
                          self.config.ys_norm[self.config.masks["data"]],
                          '-', color='C0', label='Normed Test Spectrum')
            self.span_measurement.set_active(True)

        else:
            self.ax3.plot(self.config.xs[self.config.masks["data"]],
                          self.config.ys[self.config.masks["data"]],
                          '-', color='C0', label='Test Spectrum')
            # "block" third plot if no fit
            self.span_measurement.set_active(False)

        self.ax3.set_xlim(self.config.xs[self.config.masks["data"]].min(),
                          self.config.xs[self.config.masks["data"]].max())

        self.plot_dibs(self.ax3)

        if self.config.stellar_lines is not None:
            self.plot_stellar_lines(self.ax3)

        if self.config.interstellar_lines is not None:
            self.plot_interstellar_lines(self.ax3)

        if self.config.measurements[str(self.config.selected_dib)]['notes']:
            self.plot_notes(self.ax3)
        if self.config.measurements[str(self.config.selected_dib)]['ew']:
            self.plot_results(self.ax3)
        self.plot_marked(self.ax3)
        self.ax3.legend(loc='lower right')

    def on_select_fit_range(self, xmin, xmax):
        # get x and y values of selection
        indmin, indmax = np.searchsorted(self.config.xs, (xmin, xmax))
        indmin = max(0, indmin - 2)
        indmax = min(self.config.xs.size - 1, indmax)
        self.config.fit_indices.update(range(indmin, indmax))

        # apply new fit indices to xs and ys to get fit data
        self.config.xs_fit_data = np.take(self.config.xs, sorted(list(self.config.fit_indices)))
        self.config.ys_fit_data = np.take(self.config.ys, sorted(list(self.config.fit_indices)))
        # noinspection PyTupleAssignmentBalance
        self.config.slope, self.config.intercept = np.polyfit(self.config.xs_fit_data, self.config.ys_fit_data, 1)
        self.config.ys_fit = np.array([self.config.slope * x + self.config.intercept for x in self.config.xs])
        self.config.ys_norm = self.config.ys / self.config.ys_fit

        # redraw relevant subplots
        self.reset_plot_middle()
        # self.ax2.legend()  # TODO: write legend for middle plot
        self.reset_plot_bottom()
        self.fig.canvas.draw()

    def plot_fit_data(self, ax):
        # TODO: maybe it's best to remove this for a better overview
        # self.ax2.plot(self.config.xs[self.config.masks["data"]],
        #               self.config.ys_fit[self.config.masks["data"]],
        #               '-', color='k', alpha=0.5)
        ax.plot(self.config.xs_fit_data,
                self.config.ys_fit_data,
                'o', color='C1', alpha=0.5, label='Fitted Points')

    def on_select_measurement_range(self, xmin, xmax):
        # get x and y values of selection
        indmin, indmax = np.searchsorted(self.config.xs, (xmin, xmax))
        indmin = max(0, indmin - 2)
        indmax = min(len(self.config.xs) - 1, indmax)

        absorption_depth = (1 - self.config.ys_norm[indmin:indmax])
        dynamic_pixel_width = self.config.xs[indmin+1:indmax+1] - self.config.xs[indmin:indmax]
        ew = sum(absorption_depth * dynamic_pixel_width)
        self.config.measurements[str(self.config.selected_dib)]["ew"].append(ew)

        ew_range = [self.config.xs[indmin], self.config.xs[indmax]]
        self.config.measurements[str(self.config.selected_dib)]["range"].append(ew_range)

        # if there are minima with the same value, the first will be selected.
        # this might result in some (small) bias, but for now I think this will be fine (hopefully)
        # TODO: apply some smoothing on spectrum in selected range and use that to find minima
        # TODO: mode is not a good name for this parameter
        mode = self.config.xs[indmin:indmax][np.argmin(self.config.ys_norm[indmin:indmax])]
        self.config.measurements[str(self.config.selected_dib)]["mode"].append(mode)

        half = (1. + min(self.config.ys_norm[indmin:indmax])) / 2.0  # half of absorption depth
        signs = np.sign(np.add(self.config.ys_norm[indmin:indmax], -half))
        sign_changes = ((np.roll(signs, 1) - signs) != 0).astype(int)
        if np.sum(sign_changes) < 2:
            fwhm = None
        else:
            zero_crossings_lower = np.where(signs[0:-2] != signs[1:-1])[0][0]  # first time the sign changes
            zero_crossings_upper = np.where(signs[0:-2] != signs[1:-1])[-1][-1]  # last time the sign changes
            hmx = [lin_interp(self.config.xs[indmin:indmax], self.config.ys_norm[indmin:indmax], zero_crossings_lower, half),
                   lin_interp(self.config.xs[indmin:indmax], self.config.ys_norm[indmin:indmax], zero_crossings_upper, half)]
            fwhm = hmx[1] - hmx[0]
        self.config.measurements[str(self.config.selected_dib)]["fwhm"].append(fwhm)
        if fwhm is None or fwhm == 0:
            print("FWHM could not be determined.")

        self.reset_plot_bottom()
        self.plot_ew_data(self.ax3, indmin, indmax)
        if fwhm is not None:
            self.plot_fwhm_data(self.ax3, hmx, half)
        # self.ax3.legend()  # TODO: write legend for bottom plot
        self.fig.canvas.draw()

    def plot_ew_data(self, ax, indmin, indmax):
        ax.fill_between(self.config.xs, self.config.ys_norm, 1,
                        where=(self.config.xs > self.config.xs[indmin]) & (self.config.xs <= self.config.xs[indmax]),
                        color='C2', alpha=0.5, label="Feature Integral")  # TODO: label does not work

    def plot_fwhm_data(self, ax, hmx, half):
        ax.plot(hmx, [half]*2, color="k", alpha=0.5, label="FWHM")  # TODO: label does not work

    def submit_text(self, text):
        self.config.measurements[str(self.config.selected_dib)]["notes"] = text
        # TODO: resetting colors has no effect, but works when activating textbox
        self.text_box.color = '.95'
        self.text_box.hovercolor = '.95'
        self.reset_plot_bottom()
        if self.config.measurements[str(self.config.selected_dib)]['notes']:
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
        # the enumerate is used to only plot a legend for the first dib
        for i, dib in enumerate(self.config.dibs[self.config.masks["dibs"]]):
            ax.axvline(dib, linestyle='-.', color='C3', alpha=0.5, label='Test Features' if i == 0 else None)
        # ax.axvline(self.config.selected_dib, linestyle='-', color='C1', alpha=0.5, linewidth=4, label='Selected Feature')
        ax.axvline(self.config.selected_dib, linestyle='-.', color='C3', linewidth=4., alpha=0.5, label='Selected Feature')

    def plot_stellar_lines(self, ax):
        # the enumerate is used to only plot a legend for the first stellar line
        for i, stellar_line in enumerate(self.config.stellar_lines[self.config.masks["stellar_lines"]]):
            ax.axvline(stellar_line, linestyle=':', color='C4', linewidth=2., alpha=0.5, label='Stellar Lines' if i == 0 else None)

    def plot_interstellar_lines(self, ax):
        # the enumerate is used to only plot a legend for the first interstellar line
        for i, interstellar_line in enumerate(self.config.interstellar_lines[self.config.masks["interstellar_lines"]]):
            ax.axvline(interstellar_line, linestyle=':', color='C5', linewidth=2., alpha=0.5, label='Stellar Lines' if i == 0 else None)

    def plot_doppler_shift(self, ax):
        # bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9)  # TODO: make more "modern" with these props
        s = f'{"Test Spectrum Shift":>25}: {self.config.velocity_shifts["data"]:5} km/s'
        if self.config.ref_data:
            s += f'\n{"Reference Spectrum Shift":>25}: {self.config.velocity_shifts["ref"]:5} km/s'
        if self.config.stellar_lines is not None:
            s += f'\n{"Stellar Lines Shift":>25}: {self.config.velocity_shifts["stellar"]:5} km/s'
        anchored_text = AnchoredText(s, loc='upper right', prop={'family': 'monospace'})
        ax.add_artist(anchored_text)

    def plot_notes(self, ax):
        # bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9)
        s = self.config.measurements[str(self.config.selected_dib)]['notes'].strip()
        anchored_text = AnchoredText(s, loc='upper left', prop={'family': 'monospace'})
        ax.add_artist(anchored_text)

    def plot_results(self, ax):
        # bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9)
        s = "\n".join([str(result) for result in self.config.measurements[str(self.config.selected_dib)]['ew']])
        anchored_text = AnchoredText(s, loc='upper right', prop={'family': 'monospace'})
        ax.add_artist(anchored_text)

    def plot_marked(self, ax):
        if self.config.measurements[str(self.config.selected_dib)]["marked"]:
            s = "*"
        else:
            s = " "
        anchored_text = AnchoredText(s, loc='lower left', prop={'family': 'monospace'})
        ax.add_artist(anchored_text)

    def on_press(self, event):
        # TODO: update print_navigation_keyboard_shortcuts with new shortcuts
        # TODO: find faster solution for lots of ifs at every key press (maybe by nesting ifs?)
        # TODO: some shortcuts might interfere with os or matplotlib shortcuts
        # TODO: 'q' quits the program similar to what was planned for 'esc' but does so without crashing
        # only process keypress if the text box is inactive
        if hasattr(self, "text_box") and self.text_box.get_active():
            print("textbox is active")
            return
        if event.key == 'h':
            print_navigation_keyboard_shortcuts()
            return
        if event.key == 'r':
            self.config.reset_fit()
            self.reset_plot()
            return
        if event.key == 'left':
            self.config.previous_dib()
            self.config.reset_x_range_shift()
            self.config.update_x_range()
            self.config.reset_fit()
            self.reset_plot()
            return
        if event.key == 'right':
            self.config.next_dib()
            self.config.reset_x_range_shift()
            self.config.update_x_range()
            self.config.reset_fit()
            self.reset_plot()
            return
        if event.key == 'ctrl+left':
            self.config.previous_dib(step=10)
            self.config.reset_x_range_shift()
            self.config.update_x_range()
            self.config.reset_fit()
            self.reset_plot()
            return
        if event.key == 'ctrl+right':
            self.config.next_dib(step=10)
            self.config.reset_x_range_shift()
            self.config.update_x_range()
            self.config.reset_fit()
            self.reset_plot()
            return
        if event.key == 'alt+left':
            self.config.shift_x_range_down()
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'alt+right':
            self.config.shift_x_range_up()
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'ctrl+alt+left':
            self.config.shift_x_range_down(3 * RANGE_SHIFT_SIZE)
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'ctrl+alt+right':
            self.config.shift_x_range_up(3 * RANGE_SHIFT_SIZE)
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'up':
            self.config.shift_data_up()
            self.reset_plot()
            return
        if event.key == 'down':
            self.config.shift_data_down()
            self.reset_plot()
            return
        if event.key == 'ctrl+up':
            self.config.shift_data_up(5 * VELOCITY_SHIFT_STEP_SIZE)
            self.reset_plot()
            return
        if event.key == 'ctrl+down':
            self.config.shift_data_down(5 * VELOCITY_SHIFT_STEP_SIZE)
            self.reset_plot()
            return
        if event.key == 'alt+up':
            self.config.shift_ref_data_up()
            self.reset_plot()
            return
        if event.key == 'alt+down':
            self.config.shift_ref_data_down()
            self.reset_plot()
            return
        if event.key == 'ctrl+alt+up':
            self.config.shift_ref_data_up(5 * VELOCITY_SHIFT_STEP_SIZE)
            self.reset_plot()
            return
        if event.key == 'ctrl+alt+down':
            self.config.shift_ref_data_down(5 * VELOCITY_SHIFT_STEP_SIZE)
            self.reset_plot()
            return
        if event.key == 'pageup':
            self.config.shift_stellar_lines_up()
            self.reset_plot()
            return
        if event.key == 'pagedown':
            self.config.shift_stellar_lines_down()
            self.reset_plot()
            return
        if event.key == 'ctrl+pageup':
            self.config.shift_stellar_lines_up(5 * VELOCITY_SHIFT_STEP_SIZE)
            self.reset_plot()
            return
        if event.key == 'ctrl+pagedown':
            self.config.shift_stellar_lines_down(5 * VELOCITY_SHIFT_STEP_SIZE)
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
        if event.key == 'ctrl++':
            self.config.decrease_x_range(5 * RANGE_STEP_SIZE)
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'ctrl+-':
            self.config.increase_x_range(5 * RANGE_STEP_SIZE)
            self.config.update_x_range()
            self.reset_plot()
            return
        if event.key == 'm':
            self.toggle_measurement_mark()
            self.reset_plot_bottom()
            # self.plot_marked(self.ax3)
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
            data = {"measurements": self.config.measurements, "velocity_shifts": self.config.velocity_shifts}
            save_data(data, self.output_file)
            print_measurements(self.config.measurements)
            print_velocity_shifts(self.config.velocity_shifts)
            return
        if event.key == 'alt' or event.key == 'control':
            return
        print(f"Unrecognized keyboard shortcut ({event.key}). Press 'h' for full list of shortcuts.")

    def delete_last_measurement_result(self):
        if self.config.measurements[str(self.config.selected_dib)]["ew"]:
            last_ew = self.config.measurements[str(self.config.selected_dib)]["ew"].pop()
            last_range = self.config.measurements[str(self.config.selected_dib)]["range"].pop()
            last_mode = self.config.measurements[str(self.config.selected_dib)]["mode"].pop()
            last_fwhm = self.config.measurements[str(self.config.selected_dib)]["fwhm"].pop()
            print('Removed the measurements...\n'
                  f'\t EW = {last_ew}\n'
                  f'\t Range = {last_range}\n'
                  f'\t Mode = {last_mode}\n'
                  f'\t FWHM = {last_fwhm}\n'
                  f'{len(self.config.measurements[str(self.config.selected_dib)]["ew"])} result(s) remaining.')
        else:
            print(f'No measurement result for DIB {self.config.selected_dib} found.')

    def toggle_measurement_mark(self):
        if self.config.measurements[str(self.config.selected_dib)]["marked"]:
            self.config.measurements[str(self.config.selected_dib)]["marked"] = False
        else:
            self.config.measurements[str(self.config.selected_dib)]["marked"] = True
