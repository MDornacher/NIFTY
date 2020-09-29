import json

from astropy.io import fits


def read_2d_fits_spectrum(self, input_file, xkey="lambda", ykey="flux"):
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
        raise ValueError()
    return xs, ys


def write_measurements_json(measurements, output_file):
    with open(output_file, 'w') as f:
        json.dump(measurements, f)


def read_measurements_json(input_file):
    return json.load(input_file)
