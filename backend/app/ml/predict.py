"""Explicit today -> tomorrow CSV demonstration of the portable product."""
import argparse
import pandas as pd
from .common import load_config, output_path, source_path
from viptop_fill.csv_demo import predict_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/ml.yaml')
    parser.add_argument('--today', required=True, help='End-of-day YYYY-MM-DD; forecast is the following day')
    parser.add_argument('--output', help='Explicitly export bin_id and fill_level')
    args = parser.parse_args()
    config = load_config(args.config)
    read = lambda name: pd.read_csv(source_path(config, name), keep_default_na=False, na_values=['', 'NULL'])
    result = predict_csv(output_path(config, 'product'), source_path(config, 'daily'), read('registry'), args.today, read('population'))
    if args.output:
        result.to_csv(args.output, index=False)
    print(result.head().to_string(index=False))
    print(f'{len(result)} predictions for {(pd.Timestamp(args.today) + pd.Timedelta(days=1)).date()}')


if __name__ == '__main__':
    main()
