import json
import logging

from astropy.io import fits


LOGGER = logging.getLogger(__name__)
INPUT_TYPES = ['FITS']


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


def load_features(input_file, feature_min=None, feature_max=None):
    with open(input_file) as f:
        data_raw = f.read().splitlines()
    data_final = []
    data_excluded = []
    data_errors = []
    for entry in data_raw:
        try:
            fentry = float(entry)
        except ValueError:
            data_errors.append(entry)
            continue
        if feature_min is not None and fentry < feature_min:
            data_excluded.append(fentry)
            continue
        if feature_max is not None and fentry > feature_max:
            data_excluded.append(fentry)
            continue
        data_final.append(fentry)
    if data_errors:
        LOGGER.warning(f'The following entries in feature input {input_file} could not be loaded: '
                       f'{data_errors}')
    if data_excluded:
        LOGGER.info(f'')
    return data_final


def load_measurements(input_file):
    return json.load(input_file)


def save_measurements(measurements, output_file):
    with open(output_file, 'w') as f:
        json.dump(measurements, f)
