"""Select on validation, freeze selection, then evaluate test once."""
from .common import run_cli


if __name__ == '__main__':
    from .evaluation import evaluate
    run_cli("Select on validation, freeze selection, then evaluate test once.", evaluate)

