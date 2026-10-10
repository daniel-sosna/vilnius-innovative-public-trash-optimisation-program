"""Generate model-comparison charts and the final reproducibility report."""
from .common import run_cli


if __name__ == '__main__':
    from .reporting import report
    run_cli("Generate model-comparison charts and the final reproducibility report.", report)

