import numpy as np
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector, Button


class PlotConfig:
    def __init__(self, xs, ys, dibs):
        # parameter for full spectrum
        self.xs = xs
        self.ys = ys
        self.dibs = dibs

        # parameter for norm
        self.xs_fit_data = None
        self.ys_fit_data = None
        self.ys_fit = None

        # parameter for measurement
        self.ys_norm = None

        # additional parameters
        self.selection = None


def create_spectrum_single():
    xs = np.linspace(-2, 2, 100)

    gaussian = signal.gaussian(100, 4)
    noise = np.random.rand(100)
    sn = 10
    shift = [x / 3 for x in xs]

    ys = 1 - gaussian + noise / sn + shift
    return xs, ys, [0.]


def create_spectrum(x_range=(100, 200), sigma_range=(1, 5), strength_range=(0, 1), number_of_values=300, number_of_dibs=3, sn=10):
    if x_range is None:
        x_range_min, x_range_max = (100, 500)
    else:
        x_range_min, x_range_max = x_range

    xs = np.linspace(x_range_min, x_range_max, number_of_values)
    noise = np.random.rand(xs.size)
    ys = 1 + noise / sn - np.mean(noise / sn)

    sigma_min, sigma_max = sigma_range
    strength_min, strength_max = strength_range
    dibs = []
    for i in range(number_of_dibs):
        sigma = sigma_min + np.random.rand() * sigma_max
        strength = strength_min + np.random.rand() * strength_max
        gaussian = signal.gaussian(number_of_values * 2, sigma)
        dib_index = int(np.random.rand() * number_of_values)
        dibs.append(xs[number_of_values-dib_index])
        ys = ys - strength * gaussian[dib_index:dib_index+number_of_values]
    return xs, ys, sorted(dibs)

def reset_plot():
    global xs_fit_data
    global ys_fit_data
    global ys_fit
    global ys_norm
    global selection

    selection_indmin, selection_indmax = find_selection_range()

    ax1.clear()
    ax1.plot(xs, ys, '-', color="C0")
    ax1.plot(dibs, [1.1] * len(dibs), "k|")
    ax1.plot(dibs[selection], [1.1], "rv")
    ax1.set_title('Full Spectrum')

    ax2.clear()
    ax2.plot(xs, ys, '-', color="C0")
    ax2.set_xlim(dibs[selection] * 0.9, dibs[selection] * 1.1)
    ax2.set_title('DIB Region')

    ax3.clear()
    ax3.plot(xs, ys, '-', color="C0")
    ax3.set_xlim(dibs[selection] * 0.9, dibs[selection] * 1.1)
    ax3.set_title('Local Norm')

    fig.canvas.draw()

    xs_fit_data = np.array([])
    ys_fit_data = np.array([])
    ys_fit = np.array([])
    ys_norm = np.array([])


def onselect_fit_range(xmin, xmax):
    # uff, maybe there is a better solution then this
    global xs_fit_data
    global ys_fit_data
    global ys_fit
    global ys_norm

    # get x and y values of selection
    indmin, indmax = np.searchsorted(xs, (xmin, xmax))
    indmin = max(0, indmin - 2)
    indmax = min(len(xs) - 1, indmax)

    thisx = xs[indmin:indmax]
    thisy = ys[indmin:indmax]

    # reset plot for empty selection
    if thisx.size <= 1:
        ax2.clear()
        ax2.plot(xs, ys, '-', color="C0")

        xs_fit_data = np.array([])
        ys_fit_data = np.array([])
        return

    # append to fit region and attempt to fit
    xs_fit_data = np.append(thisx, xs_fit_data)
    ys_fit_data = np.append(thisy, ys_fit_data)
    k, d = np.polyfit(xs_fit_data, ys_fit_data, 1)
    ys_fit = [k * x + d for x in xs]
    ys_norm = ys / ys_fit

    # redraw everything
    ax2.clear()
    ax2.set_title('DIB Region')
    ax2.set_xlim(dibs[selection] * 0.9, dibs[selection] * 1.1)
    ax2.plot(xs, ys, '-', color="C0")
    ax2.plot(xs, ys_fit, '-', color="k", alpha=0.5, label="k={:6.2f}".format(k))   # '{:06.2f}'.format(3.141592653589793)
    # ax2.plot(thisx, thisy, '-', color="C1", linewidth=2)
    ax2.plot(xs_fit_data, ys_fit_data, 'o', color="C1", alpha=0.5)
    ax2.legend()

    ax3.clear()
    ax3.set_title('Local Norm')
    ax3.set_xlim(dibs[selection] * 0.9, dibs[selection] * 1.1)
    ax3.axhline(1, xs.min(), xs.max(), color="k", alpha=0.5)
    ax3.plot(xs, ys_norm)

    fig.canvas.draw()


def onselect_ew_range(xmin, xmax):
    global ys_norm
    # get x and y values of selection
    indmin, indmax = np.searchsorted(xs, (xmin, xmax))
    indmin = max(0, indmin - 2)
    indmax = min(len(xs) - 1, indmax)
    diff = ys_norm[indmin:indmax] * (xs[1] - xs[0])
    ew = sum(diff)

    ax3.clear()
    ax3.set_title('Local Norm')
    ax3.set_xlim(dibs[selection] * 0.9, dibs[selection] * 1.1)
    ax3.axhline(1, xs.min(), xs.max(), color="k", alpha=0.5)
    ax3.plot(xs, ys_norm)
    ax3.fill_between(xs, ys_norm, 1, where=(xs > xs[indmin]) & (xs <= xs[indmax]),
                     color="green", alpha=0.5, label="EW={:6.2f}".format(ew))
    ax3.legend()
    fig.canvas.draw()


def next_dib():
    global selection
    selection = (selection + 1) % len(dibs)
    reset_plot()


def previous_dib():
    global selection
    selection = (selection - 1) % len(dibs)
    reset_plot()


def find_selection_range():
    global selection
    xmin = dibs[selection] * (1. - 0.1)
    xmax = dibs[selection] * (1. + 0.1)
    indmin, indmax = np.searchsorted(xs, (xmin, xmax))
    indmin = max(0, indmin - 2)
    indmax = min(len(xs) - 1, indmax)
    return indmin, indmax


def onpress(event):
    print(event.key)
    if event.key == 'r':
        reset_plot()
    if event.key == 'left':
        previous_dib()
    if event.key == 'right':
        next_dib()
    if event.key == 'up':
        pass
    if event.key == 'down':
        pass
    if event.key == '+':
        pass
    if event.key == '-':
        pass
    if event.key == 'escape':
        plt.close()


if __name__ == "__main__":
    # xs, ys, dibs = create_spectrum_single()
    xs, ys, dibs = create_spectrum(x_range=(100, 300), sigma_range=(1, 5), strength_range=(0, 1), number_of_values=300,
                                   number_of_dibs=5, sn=10)

    plot_config = PlotConfig(xs, ys, dibs)

    fig, (ax1, ax2, ax3) = plt.subplots(3, figsize=(8, 6), constrained_layout=True)
    fig.canvas.set_window_title('NIFTY')

    selection = 0
    reset_plot()

    cid = fig.canvas.mpl_connect('key_press_event', onpress)

    # Set useblit=True on most backends for enhanced performance.
    span_fit = SpanSelector(ax2, onselect_fit_range, 'horizontal', useblit=True,
                            rectprops=dict(alpha=0.5, facecolor='yellow'))

    span_ew = SpanSelector(ax3, onselect_ew_range, 'horizontal', useblit=True,
                           rectprops=dict(alpha=0.5, facecolor='yellow'))

    plt.show()
