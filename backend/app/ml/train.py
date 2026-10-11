"""Fit configured models using approved search parameters and train-only preprocessing."""
from .common import run_cli


def arguments(parser):
    parser.add_argument('--approval-json', help='User confirmation record bound to search_proposal.json')


if __name__ == '__main__':
    from .evaluation import train
    run_cli("Fit configured models using approved search parameters and train-only preprocessing.", train, extra=arguments)
