import argparse
import glob
import logging
import os
import sys

from nifty.config import PlotConfig
from nifty.io import (INPUT_TYPES, load_features, load_measurements,
                      load_spectrum, load_stellar_lines,
                      match_spectrum_unit_to_features, trim_features,
                      trim_spectrum)
from nifty.prints import (print_banner, print_demo_message,
                          print_summary_of_input_parameters)
from nifty.ui import PlotUI

LOGGER = logging.getLogger(__name__)
FEATURE_PATH = os.path.join('resources', 'dibs')
DEFAULT_NIFTY_OUTPUT_EXTENSION = '_nifty.json'


def main():
    print_banner()
    if len(sys.argv) == 1:
        demo_mode()
    else:
        measurement_mode()


def demo_mode():
    print_demo_message()
    config = PlotConfig()
    results = None
    output_file = "demo_measurements.json"
    PlotUI(config, output_file, results, title="Demo Mode of NIFTY")


def measurement_mode():
    args = parse_input()
    args = resolve_input_paths(args)
    validate_parameters(args)
    print_summary_of_input_parameters(args)

    # initialize static parameters
    dibs = load_features(args.features)
    if args.stellar is not None:
        stellar_lines = load_stellar_lines(args.stellar)
    else:
        stellar_lines = None

    for i, selected_input in enumerate(args.input):
        if args.output is None:
            args.output = create_output_path(selected_input)
        if os.path.isfile(args.output):
            print(args.output)
            if args.skip:
                print("Processing skipped, because output file already exists")
                LOGGER.info("Processing skipped, because output file already exists")
                args.output = None  # TODO: this is a bad fix for multifile input
                continue
            measurements = load_measurements(args.output)
        else:
            measurements = None

        xs, ys = load_spectrum(selected_input, args.type, args.xkey, args.ykey)
        if args.matching:
            xs = match_spectrum_unit_to_features(xs, dibs)

        # remove leading and trailing zeros from spectrum and use new min/max to trim features
        xs_trimmed, ys_trimmed = trim_spectrum(xs, ys)
        dibs_trimmed = trim_features(dibs, xs_trimmed.min(), xs_trimmed.max())

        # matching procedure for the reference spectrum (if available)
        if args.ref is not None:
            xs_ref, ys_ref = load_spectrum(args.ref, args.type, args.xkey, args.ykey)
            if args.matching:
                xs_ref = match_spectrum_unit_to_features(xs_ref, dibs)
            xs_ref_trimmed, ys_ref_trimmed = trim_spectrum(xs_ref, ys_ref)
        else:
            xs_ref_trimmed, ys_ref_trimmed = None, None

        config = PlotConfig(xs=xs_trimmed, ys=ys_trimmed, dibs=dibs_trimmed,
                            xs_ref=xs_ref_trimmed, ys_ref=ys_ref_trimmed,
                            stellar_lines=stellar_lines)

        title = f"[ {i} / {len(args.input)}] {os.path.basename(selected_input)}"
        PlotUI(config, args.output, measurements, title)
        # TODO: plt.close() somehow breaks the programm, maybe something wrong with matplotlib installation
        # TODO: additional console for LOGGER
        args.output = None  # TODO: this is a bad fix for multifile input


def parse_input():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Specify spectrum input file.')
    parser.add_argument('-t', '--type', required=True, type=str.upper, help='Specify type of input file.')
    parser.add_argument('-o', '--output', default=None, help='Specify the output file.')
    parser.add_argument('--xkey', required=False, default=None, help='Specify key of x values in input file.')
    parser.add_argument('--ykey', required=False, default=None, help='Specify key of y values in input file.')
    parser.add_argument('-f', '--features', default=None, help='Specify absorption feature input file.')
    parser.add_argument('-m', '--matching', help='Match unit of measurement of spectrum to absorption features.',
                        action='store_true')
    parser.add_argument('--ref', required=False, default=None, help='Specify reference spectrum.')
    parser.add_argument('--stellar', required=False, default=None, nargs="+",
                        help='Specify input file(s) of stellar reference lines')
    parser.add_argument('--skip', help='Skip processing if output file already exists.', action='store_true')
    # TODO: force overwrite parameter like '-F'
    return parser.parse_args()


def resolve_input_paths(args):
    if "*" not in args.input:
        args.input = [args.input]
    else:
        args.input = glob.glob(args.input)
        if not args.input:
            raise ValueError(f'No files found while resolving input {args.input}')
    return args


def create_output_path(input_path):
    reusable_input_name, _ = os.path.splitext(input_path)
    return reusable_input_name + DEFAULT_NIFTY_OUTPUT_EXTENSION


def validate_parameters(args):
    for selected_input in args.input:
        if not os.path.isfile(selected_input):
            raise ValueError(f'Input "{selected_input}" is not a file.')
        if not os.access(selected_input, os.R_OK):
            raise ValueError(f'Input "{selected_input}" is not readable.')

    if args.type not in INPUT_TYPES:
        raise ValueError(f'Type "{args.type}" is not in list of valid input types {INPUT_TYPES}.')

    if args.output is not None:
        if len(args.input) > 1:
            LOGGER.warning('Output file can not be specified when input is multiple files. '
                           'Defaulting to automated name for output files.')
            args.output = None
        if not os.access(os.path.dirname(args.output), os.W_OK):
            raise ValueError(f'Directory of output "{args.output}" is not writable.')
        if os.path.exists(args.output):
            LOGGER.warning(f'Output {args.output} already exists - will get overwritten.')

    if args.features is None:
        args.features = FEATURE_PATH
    if not os.path.isfile(args.features):
        raise ValueError(f'Input "{args.features}" is not a file.')
    if not os.access(args.features, os.R_OK):
        raise ValueError(f'Input "{args.features}" is not readable.')


if __name__ == '__main__':
    main()
