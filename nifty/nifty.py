import argparse

from nifty.ui import PlotUI
from nifty.io import load_spectrum


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Specify spectrum input file.')
    parser.add_argument('-t', '--type', required=True, help='WRITE ME')
    parser.add_argument('-o', '--output', required=True, help='Specify the output file.')
    parser.add_argument('--xkey', required=True, help='WRITE ME')
    parser.add_argument('--ykey', required=True, help='WRITE ME')
    parser.add_argument('-f', '--features', required=True, help='Specify absorption feature input file.')
    args = parser.parse_args()

    if args.a == 'magic.name':
        print('You nailed it!')

    PlotUI()
