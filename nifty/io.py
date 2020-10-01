import json
import logging

from astropy.io import fits
import numpy as np


LOGGER = logging.getLogger(__name__)
INPUT_TYPES = ['FITS', 'NORM']


def load_spectrum(input_file, input_type, xkey=None, ykey=None):
    if input_type == 'FITS':
        # TODO: setting y-/x-keys might be redundant / there is probably a cleaner solution
        xkey_filtered = 'lambda'
        ykey_filtered = 'flux'
        if xkey is not None:
            xkey_filtered = xkey
        if ykey is not None:
            ykey_filtered = ykey
        return read_2d_fits_spectrum(input_file, xkey_filtered, ykey_filtered)

    if input_type == 'NORM':
        return read_2d_norm_spectrum(input_file)

    # TODO: add import for other input types, e.g.: 'NORM', 'ASCII'(?)
    raise ValueError(f'Type "{input_type}" is not in list of valid input types {INPUT_TYPES}.')


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
        LOGGER.warning(f'The following entries in input {input_file} could not be loaded: '
                       f'{data_errors}')
    return np.array(xs), np.array(ys)


def trim_spectrum(xs, ys):
    ys_trimmed = np.trim_zeros(ys)
    i_start = np.where(ys == ys_trimmed[0])[0][0]
    i_end = i_start + len(ys_trimmed)
    xs_trimmed = xs[i_start:i_end]
    if len(xs_trimmed) == len(ys_trimmed):
        LOGGER.info('The size of the (x, y) values in the spectrum changed from '
                    f'{(len(xs), len(ys))} to {(len(xs_trimmed), len(ys_trimmed))}.')
        return xs_trimmed, ys_trimmed
    raise ValueError('The trimmed size of the (x, y) values no longer matches: '
                     f'{len(xs_trimmed)} != {len(ys_trimmed)}')


def load_features(input_file):
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
        LOGGER.warning(f'The following entries in feature input {input_file} could not be loaded: '
                       f'{data_errors}')
    return data_final


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
    return features_trimmed


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
    # TODO: mismatched xs will be returned if the values get to small
    raise ValueError(f'The spectrum could not be matched with the following factors: '
                     f'10**{list(f_unit_range)}')


def load_results(input_file):
    with open(input_file, 'r') as f:
        measurements = json.load(f)
    return measurements


def save_results(results, output_file):
    with open(output_file, 'w') as f:
        json.dump(results, f)
