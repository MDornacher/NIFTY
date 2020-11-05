import numpy as np
from scipy import signal


def create_spectrum(x_range=(100, 200), sigma_range=(1, 5), strength_range=(0, 1), number_of_values=300,
    number_of_dibs=3, sn=10):

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
        dibs.append(xs[dib_index])
        ys = ys - strength * gaussian[number_of_values - dib_index:2*number_of_values - dib_index]

    dibs = np.array(sorted(dibs))
    return xs, ys, dibs

