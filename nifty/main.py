import argparse
import logging
import os
import sys

from nifty.ui import PlotUI
from nifty.io import load_spectrum


LOGGER = logging.getLogger(__name__)
INPUT_TYPES = ['FITS']
FEATURE_PATH = os.path.join('resources', 'dibs')


def summarize_input_parameters(args):
    s = f'''
    {'-'*40}
    # NIFTY INPUT PARAMETERS
    # Input: {args.input}
    #\tType: {args.type}
    #\tX-Key: {args.xkey}
    #\tY-Key: {args.ykey}
    # Output: {args.output}
    # Features: {args.features}
    {'-'*40}
    '''
    print(s)


def print_demo_message():
    s = f'''
    {'-'*40}
    # NIFTY DEMO MODE
    # Working with synthetic spectrum
    {'-'*40}
    '''
    print(s)


def input_validation(args):

    if not os.path.isfile(args.input):
        raise ValueError(f'Input "{args.input}" is not a file.')
    if not os.access(args.input, os.R_OK):
        raise ValueError(f'Input "{args.input}" is not readable.')

    if args.type not in INPUT_TYPES:
        raise ValueError(f'Type "{args.type}" is not in list of valid input types {INPUT_TYPES}.')

    if not os.access(os.path.dirname(args.output), os.W_OK):
        raise ValueError(f'Directory of output "{args.input}" is not writable.')
    if os.path.exists(args.output):
        LOGGER.warning(f'Output {args.output} already exists - will get overwritten.')

    if args.features is None:
        args.features = FEATURE_PATH
    if not os.path.isfile(args.features):
        raise ValueError(f'Input "{args.features}" is not a file.')
    if not os.access(args.features, os.R_OK):
        raise ValueError(f'Input "{args.features}" is not readable.')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--input', required=True, help='Specify spectrum input file.')
        parser.add_argument('-t', '--type', required=True, type=str.upper, help='Specify type of input file.')
        parser.add_argument('-o', '--output', required=True, help='Specify the output file.')
        parser.add_argument('--xkey', required=True, help='Specify key of x values in input file.')
        parser.add_argument('--ykey', required=True, help='Specify key of y values in input file.')
        parser.add_argument('-f', '--features', default=None, help='Specify absorption feature input file.')
        parser.add_argument('-d', '--demo', required=False, help='Start NIFTY in demo mode.')  # TODO: implement demo
        args = parser.parse_args()

        input_validation(args)
        summarize_input_parameters(args)

        # TODO: parse / load input parameters

    else:
        print_demo_message()

    PlotUI()
