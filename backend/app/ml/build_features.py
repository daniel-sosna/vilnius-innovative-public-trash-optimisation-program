"""Construct active inputs in memory; publish only provenance and statistics."""
from .common import run_cli
from .features import build_features
if __name__=='__main__': run_cli('Construct ephemeral features without saving derived tables.',build_features)
