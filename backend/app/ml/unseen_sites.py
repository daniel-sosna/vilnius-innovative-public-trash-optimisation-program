"""Evaluate the selected configuration on independently held-out sites."""
from .common import run_cli


if __name__ == '__main__':
    from .evaluation import unseen_sites
    run_cli("Evaluate the selected configuration on independently held-out sites.", unseen_sites)
