import argparse

from nifty.ui import PlotUI
from nifty.io import load_spectrum


def summarize_input_parameters(args):
    s = f"""
    {'-'*40}
    # NIFTY INPUT PARAMETERS
    # Input: {args.input}
    #\tType: {args.type}
    #\tX-Key: {args.xkey}
    #\tY-Key: {args.ykey}
    # Output: {args.output}
    # Features: {args.features}
    {'-'*40}
    """
    print(s)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Specify spectrum input file.')
    parser.add_argument('-t', '--type', required=True, help='WRITE ME')
    parser.add_argument('-o', '--output', required=True, help='Specify the output file.')
    parser.add_argument('--xkey', required=True, help='WRITE ME')
    parser.add_argument('--ykey', required=True, help='WRITE ME')
    parser.add_argument('-f', '--features', required=True, help='Specify absorption feature input file.')
    args = parser.parse_args()

    summarize_input_parameters(args)

    # TODO: parse / load input parameters

    PlotUI()
