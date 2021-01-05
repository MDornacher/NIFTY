import json
import logging

import numpy as np
from astropy.io import fits

LOGGER = logging.getLogger(__name__)
INPUT_TYPES = ['FITS', 'NORM', 'SPEC']
UNIT_CONVERSION = {'A': 1., 'NM': 10., 'MUM': 10.**4, 'MM': 10.**7}


def load_spectrum(input_file, input_type, unit='A', xkey='lambda', ykey='flux'):
    # TODO: UNITS SHOULD BE IN ANGSTROM! OTHERWISE DOPPLERSHIFT DOES _NOT_ WORK...
    if input_type == 'FITS':
        # TODO: setting y-/x-keys might be redundant / there is probably a cleaner solution
        xkey_filtered = 'lambda'
        ykey_filtered = 'flux'
        if xkey is not None:
            xkey_filtered = xkey
        if ykey is not None:
            ykey_filtered = ykey
        xs, ys = read_2d_fits_spectrum(input_file, xkey_filtered, ykey_filtered)

    elif input_type == 'NORM':
        xs, ys = read_2d_norm_spectrum(input_file)

    elif input_type == 'SPEC':
        xs, ys = read_2d_norm_spectrum(input_file)

    else:
        raise ValueError(f'Type "{input_type}" is not in list of valid input types {INPUT_TYPES}.')
        # TODO: add import for other input types, e.g.: 'ASCII'(?)
    if unit not in UNIT_CONVERSION:
        raise ValueError()  # TODO: write error message
    return xs * UNIT_CONVERSION[unit], ys


def read_2d_fits_spectrum(input_file, xkey='lambda', ykey='flux'):
    xs = None
    ys = None
    # Search FITS data for data keys
    data_keys = [xkey, ykey]
    fits_file = fits.open(input_file)
    with fits.open(input_file) as fits_file:
        for hdu in fits_file:
            if hdu.data is None:
                continue
            if not hasattr(hdu.data, 'names'):
                continue

            if xkey in hdu.data.names:
                xs = hdu.data[xkey]
            if ykey in hdu.data.names:
                ys = hdu.data[ykey]

            if xs is not None and ys is not None:
                break

    if xs is None or ys is None:
        raise ValueError(f'The FITS file {input_file} has no data with the key {xkey} or {ykey}')
    return xs, ys


def read_2d_norm_spectrum(input_file):
    with open(input_file) as f:
        data_raw = f.read().splitlines()
    xs = []
    ys = []
    data_errors = []
    for line in data_raw:
        if len(line.split()) == 2:
            try:
                x, y = [float(i) for i in line.split()]
                xs.append(x)
                ys.append(y)
            except ValueError:
                data_errors.append(line)
        else:
            if line:
                data_errors.append(line)

    if data_errors:
        LOGGER.warning(f'The following entries in input "{input_file}" could not be loaded: '
                       f'{data_errors}')
    return np.array(xs), np.array(ys)


def trim_spectrum(xs, ys):
    ys_trimmed = np.trim_zeros(np.nan_to_num(ys))
    i_start = np.where(ys == ys_trimmed[0])[0][0]
    i_end = i_start + len(ys_trimmed)
    xs_trimmed = xs[i_start:i_end]
    if len(xs_trimmed) == len(ys_trimmed):
        LOGGER.info('The size of the (x, y) values in the spectrum changed from '
                    f'{(len(xs), len(ys))} to {(len(xs_trimmed), len(ys_trimmed))}.')
        return xs_trimmed[1:-1], ys_trimmed[1:-1]  # Trim first and last entry to avoid silly outliers
    raise ValueError('The trimmed size of the (x, y) values no longer matches: '
                     f'{len(xs_trimmed)} != {len(ys_trimmed)}')


def load_features(input_file, unit='A'):
    with open(input_file) as f:
        data_raw = f.read().splitlines()
    data_final = []
    data_errors = []
    for entry in data_raw:
        try:
            data_final.append(float(entry))
        except ValueError:
            data_errors.append(entry)

    if data_errors:
        LOGGER.warning(f'The following entries in feature input "{input_file}" could not be loaded: '
                       f'{data_errors}')

    if unit not in UNIT_CONVERSION:
        raise ValueError()  # TODO: write error message
    return np.sort(np.array(data_final)) * UNIT_CONVERSION[unit]


def trim_features(features, feature_min=None, feature_max=None):
    # TODO maybe this should be done when plotting
    features_trimmed = []
    features_excluded = []
    for feature in features:
        if feature_min is not None and feature < feature_min:
            features_excluded.append(feature)
            continue
        if feature_max is not None and feature > feature_max:
            features_excluded.append(feature)
            continue
        features_trimmed.append(feature)
    if features_excluded:
        LOGGER.info(f'The number of features changed from {len(features)} to {len(features_trimmed)}. '
                    f'The following features have been excluded: {features_excluded}')
    return np.array(features_trimmed)


def match_spectrum_unit_to_features(xs, features):
    features_min = min(features)
    features_max = max(features)

    f_unit_range = range(9, -10, -3)
    for f_unit_power in f_unit_range:
        f_unit = 10**f_unit_power
        xs_matched_min = xs.min() * f_unit
        xs_matched_max = xs.max() * f_unit
        if features_min < xs_matched_min < features_max or features_min < xs_matched_max < features_max:
            LOGGER.info(f'The spectrum could be matched with the factor {f_unit}')
            return xs * f_unit
    raise ValueError(f'The spectrum could not be matched with the following factors: '
                     f'10**{list(f_unit_range)}')


def load_data(input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    return data


def save_data(data, output_file):
    # TODO: include doppler shifts
    with open(output_file, 'w') as f:
        json.dump(data, f)


def load_stellar_lines(input_files, unit='A'):
    stellar_lines = np.array([])
    for input_file in input_files:
        stellar_lines = np.append(stellar_lines, load_features(input_file))
    if unit not in UNIT_CONVERSION:
        raise ValueError(f'{unit} is not {UNIT_CONVERSION.keys()}')  # TODO: write error message
    return np.sort(stellar_lines * UNIT_CONVERSION[unit])
