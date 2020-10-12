import argparse
import glob
import logging
import os
import sys

from nifty.ui import PlotUI, PlotConfig
from nifty.io import INPUT_TYPES, load_spectrum, load_features, load_results, \
    trim_spectrum, trim_features, match_spectrum_unit_to_features


LOGGER = logging.getLogger(__name__)
FEATURE_PATH = os.path.join('resources', 'dibs')
DEFAULT_NIFTY_OUTPUT_EXTENSION = '_nifty.json'


def main():
    if len(sys.argv) == 1:
        print_demo_message()
        config = PlotConfig()
        results = None
        output_file = "demo_measurements.json"
        PlotUI(config, output_file, results)

    else:
        args = parse_input()

        args = validate_input_path(args)
        # args = validate_output_path(args)  # TODO: need to be reworked for multi file input

        validate_parameters(args)
        summarize_input_parameters(args)

        dibs = load_features(args.features)

        for selected_input in args.input:
            xs, ys = load_spectrum(selected_input, args.type, args.xkey, args.ykey)
            if args.matching:
                xs = match_spectrum_unit_to_features(xs, dibs)

            xs_trimmed, ys_trimmed = trim_spectrum(xs, ys)
            dibs_trimmed = trim_features(dibs, xs_trimmed.min(), xs_trimmed.max())

            if args.ref is not None:
                xs_ref, ys_ref = load_spectrum(args.ref, args.type, args.xkey, args.ykey)
                xs_ref_trimmed, ys_ref_trimmed = trim_spectrum(xs_ref, ys_ref)
                config = PlotConfig(xs_trimmed, ys_trimmed, dibs_trimmed, xs_ref_trimmed, ys_ref_trimmed)
            else:
                config = PlotConfig(xs_trimmed, ys_trimmed, dibs_trimmed)

            output_file = create_output_path(selected_input)
            if os.path.isfile(output_file):
                results = load_results(output_file)
            else:
                results = None

            PlotUI(config, output_file, results)
            # TODO:  plt.close() somehow breaks the programm, maybe something wrong with matplotlib installation


def parse_input():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Specify spectrum input file.')
    parser.add_argument('-t', '--type', required=True, type=str.upper, help='Specify type of input file.')
    # parser.add_argument('-o', '--output', default=None, help='Specify the output file.')
    # TODO: need to be reworked for multi file input
    parser.add_argument('--xkey', required=False, default=None, help='Specify key of x values in input file.')
    parser.add_argument('--ykey', required=False, default=None, help='Specify key of y values in input file.')
    parser.add_argument('-f', '--features', default=None, help='Specify absorption feature input file.')
    parser.add_argument('-m', '--matching', help='Match unit of measurement of spectrum to absorption features.',
                        action='store_true')
    parser.add_argument('--ref', required=False, default=None, help='Specify reference spectrum.')
    return parser.parse_args()


def validate_input_path(args):
    if "*" not in args.input:
        args.input = [args.input]
    else:
        args.input = glob.glob(args.input)
    return args


def validate_output_path(args):
    if args.output is not None:
        return args
    args.output = create_output_path(args.input)
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

    # if not os.access(os.path.dirname(args.output), os.W_OK):
    #     raise ValueError(f'Directory of output "{args.output}" is not writable.')
    # if os.path.exists(args.output):
    #     LOGGER.warning(f'Output {args.output} already exists - will get overwritten.')

    if args.features is None:
        args.features = FEATURE_PATH
    if not os.path.isfile(args.features):
        raise ValueError(f'Input "{args.features}" is not a file.')
    if not os.access(args.features, os.R_OK):
        raise ValueError(f'Input "{args.features}" is not readable.')


def summarize_input_parameters(args):
    # TODO: args.output has been (temporarily) removed
    s = f'''
    {'-'*40}
    # NIFTY INPUT PARAMETERS
    # Input: {args.input}
    #\tType: {args.type}
    #\tX-Key: {args.xkey}
    #\tY-Key: {args.ykey}
    #\tMatching: {args.matching}
    # Features: {args.features}
    {'-'*40}
    '''
    print(s)


def print_demo_message():
    s = f'''
    {'-'*40}
    # NIFTY DEMO MODE
    # Working with synthetic spectrum.
    # Start with "-h" to get available options.
    {'-'*40}
    '''
    print(s)


if __name__ == '__main__':
    main()
