"""Run a small pilot or an explicitly approved chronological model search."""
from .common import run_cli


def arguments(parser):
    parser.add_argument('--pilot', action='store_true', help='Measure small fits and write the search proposal; does not tune on test')
    parser.add_argument('--approval-json', help='User confirmation record bound to search_proposal.json')


if __name__ == '__main__':
    from .search import tune
    run_cli("Run a small pilot or an explicitly approved chronological model search.", tune, extra=arguments)

