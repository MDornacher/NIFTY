import numpy as np
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector

from nifty.io import save_results


class PlotUI:
    def __init__(self, config, output_file, results=None):
        self.config = config
        self.measurements = Measurements(self.config.dibs)
        if results is not None:
            self.measurements.results = results
            self.validate_results()
        self.output_file = output_file

        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, figsize=(8, 6), constrained_layout=True)
        self.fig.canvas.set_window_title('NIFTY')

        self.reset_plot()

        self.cid = self.fig.canvas.mpl_connect('key_press_event', self.onpress)
        self.span_fit = SpanSelector(self.ax2, self.onselect_fit_range, 'horizontal', useblit=True,
                                rectprops=dict(alpha=0.5, facecolor='yellow'))
        self.span_ew = SpanSelector(self.ax3, self.onselect_ew_range, 'horizontal', useblit=True,
                               rectprops=dict(alpha=0.5, facecolor='yellow'))
        plt.show()

    def validate_results(self):
        dibs_test_list = [str(dib) for dib in self.config.dibs]
        results_test_list = list(self.measurements.results.keys())

        dibs_test_list.sort()
        results_test_list.sort()

        if dibs_test_list != results_test_list:
            raise ValueError(f'The list of dibs and results do not match.')

    def reset_plot(self):
        self.config.reset_fit()

        self.reset_plot_top()
        self.reset_plot_middle()
        self.reset_plot_bottom()

        self.fig.canvas.draw()

    def reset_plot_top(self):
        self.ax1.clear()
        self.ax1.set_title('Full Spectrum')
        if self.config.ref_data:
            self.ax1.plot(self.config.xs_ref, self.config.ys_ref, '-', color='k', alpha=0.5)
        self.ax1.plot(self.config.xs, self.config.ys, '-', color='k')
        self.ax1.plot(self.config.dibs, [1.1] * len(self.config.dibs), 'k|')
        self.ax1.plot(self.config.selected_dib, [1.1], 'rv')

    def reset_plot_middle(self):
        self.ax2.clear()
        self.ax2.set_title('DIB Region')
        self.ax2.set_xlim(self.config.selected_dib * (1 - self.config.x_range_factor),
                          self.config.selected_dib * (1 + self.config.x_range_factor))
        if self.config.ref_data:
            self.ax2.plot(self.config.xs_ref, self.config.ys_ref, '-', color='k', alpha=0.5)
        self.ax2.plot(self.config.xs, self.config.ys, '-', color='C0')

    def reset_plot_bottom(self):
        self.ax3.clear()
        self.ax3.set_title('Local Norm')
        self.ax3.set_xlim(self.config.selected_dib * (1 - self.config.x_range_factor),
                          self.config.selected_dib * (1 + self.config.x_range_factor))
        self.ax3.set_ylim(1. - self.config.y_range_factor, 1.1)
        if self.config.ref_data:
            self.ax3.plot(self.config.xs_ref, self.config.ys_ref, '-', color='k', alpha=0.5)
        self.ax3.plot(self.config.xs, self.config.ys, '-', color='C0')

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
        k, d = np.polyfit(self.config.xs_fit_data, self.config.ys_fit_data, 1)
        self.config.ys_fit = [k * x + d for x in self.config.xs]
        self.config.ys_norm = self.config.ys / self.config.ys_fit

        # redraw everything
        self.ax2.clear()
        self.ax2.set_title('DIB Region')
        self.ax2.set_xlim(self.config.selected_dib * (1 - self.config.x_range_factor),
                          self.config.selected_dib * (1 + self.config.x_range_factor))
        self.ax2.plot(self.config.xs, self.config.ys, '-', color='C0')
        self.ax2.plot(self.config.xs, self.config.ys_fit, '-', color='k', alpha=0.5, label='k={:6.2f}'.format(k))
        # ax2.plot(thisx, thisy, '-', color='C1', linewidth=2)
        self.ax2.plot(self.config.xs_fit_data, self.config.ys_fit_data, 'o', color='C1', alpha=0.5)
        self.ax2.legend()

        self.ax3.clear()
        self.ax3.set_title('Local Norm')
        self.ax3.set_xlim(self.config.selected_dib * (1 - self.config.x_range_factor),
                          self.config.selected_dib * (1 + self.config.x_range_factor))
        self.ax3.set_ylim(1. - self.config.y_range_factor, 1.1)
        self.ax3.axhline(1, self.config.xs.min(), self.config.xs.max(), color='k', alpha=0.5)
        self.ax3.plot(self.config.xs, self.config.ys_norm)

        self.fig.canvas.draw()

    def onselect_ew_range(self, xmin, xmax):
        # get x and y values of selection
        indmin, indmax = np.searchsorted(self.config.xs, (xmin, xmax))
        indmin = max(0, indmin - 2)
        indmax = min(len(self.config.xs) - 1, indmax)

        diff = (1 - self.config.ys_norm[indmin:indmax]) * (self.config.xs[1] - self.config.xs[0])
        ew = sum(diff)
        self.measurements.results[str(self.config.selected_dib)].append(ew)

        self.ax3.clear()
        self.ax3.set_title('Local Norm')
        self.ax3.set_xlim(self.config.dibs[self.config.selection] * (1 - self.config.x_range_factor),
                          self.config.dibs[self.config.selection] * (1 + self.config.x_range_factor))
        self.ax3.set_ylim(1. - self.config.y_range_factor, 1.1)
        self.ax3.axhline(1, self.config.xs.min(), self.config.xs.max(), color='k', alpha=0.5)
        self.ax3.plot(self.config.xs, self.config.ys_norm)
        self.ax3.fill_between(self.config.xs, self.config.ys_norm, 1,
                              where=(self.config.xs > self.config.xs[indmin]) & (self.config.xs <= self.config.xs[indmax]),
                              color='green', alpha=0.5, label='EW={:6.6f}'.format(ew))
        self.ax3.legend()
        self.fig.canvas.draw()

    def onpress(self, event):
        print(event.key)
        if event.key == 'r':
            self.reset_plot()
        if event.key == 'left':
            self.config.previous_dib()
            self.reset_plot()
        if event.key == 'right':
            self.config.next_dib()
            self.reset_plot()
        if event.key == 'up':
            self.config.increase_y_range()
            self.reset_plot()
        if event.key == 'down':
            self.config.decrease_y_range()
            self.reset_plot()
        if event.key == '+':
            self.config.decrease_x_range()
            self.reset_plot()
        if event.key == '-':
            self.config.increase_x_range()
            self.reset_plot()
        if event.key == ' ':
            print(f'Saving measurements to {self.output_file}')
            save_results(self.measurements.results, self.output_file)
            for k, v in self.measurements.results.items():
                print(k, v)
        if event.key == 'escape':
            plt.close('all')


class PlotConfig:
    def __init__(self, xs=None, ys=None, dibs=None, xs_ref=None, ys_ref=None):
        # parameter for full spectrum
        # TODO: distinguish between missing xs/ys and missing dibs
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

        # parameter for norm
        self.xs_fit_data = np.array([])
        self.ys_fit_data = np.array([])
        self.ys_fit = np.array([])

        # parameter for measurement
        self.ys_norm = np.array([])

        # additional parameters
        self.selection = 0
        self.selected_dib = self.dibs[self.selection]
        self.x_range_factor = 0.1
        self.y_range_factor = 1.1

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
            dib_index = int(np.random.rand() * number_of_values) - 1
            self.dibs.append(self.xs[number_of_values - dib_index])
            self.ys = self.ys - strength * gaussian[dib_index:dib_index + number_of_values]
        self.dibs.sort()

    def reset_fit(self):
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
        self.x_range_factor += 0.01

    def decrease_x_range(self):
        self.x_range_factor -= 0.01

    def increase_y_range(self):
        self.y_range_factor += 0.1

    def decrease_y_range(self):
        self.y_range_factor -= 0.1


class Measurements:
    def __init__(self, dibs):
        self.results = {str(dib): [] for dib in dibs}
