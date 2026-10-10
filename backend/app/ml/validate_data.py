"""Validate full daily/registry inputs without changing source data."""
from .common import run_cli


if __name__ == '__main__':
    from .validation import validate_data
    run_cli("Validate full daily/registry inputs without changing source data.", validate_data)
