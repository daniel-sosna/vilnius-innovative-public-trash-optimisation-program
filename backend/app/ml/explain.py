"""Produce native, permutation and feasible SHAP explanations."""
from .common import run_cli


if __name__ == '__main__':
    from .explanations import explain
    run_cli("Produce native, permutation and feasible SHAP explanations.", explain)
