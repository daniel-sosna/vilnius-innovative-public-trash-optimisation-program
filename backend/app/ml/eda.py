"""Generate concise synthetic-data EDA charts with underlying tables."""
from .common import run_cli


if __name__ == '__main__':
    from .validation import create_eda
    run_cli("Generate concise synthetic-data EDA charts with underlying tables.", create_eda)
