"""Reproduce the September experiment with ephemeral feature frames."""
from argparse import Namespace
import logging
from .common import run_cli,output_path,read_json,write_json

def run(config,args):
    from .validation import validate_data,create_eda
    from .features import build_features
    from .search import run_pilot,tune
    from .evaluation import train,evaluate,predict,unseen_sites
    from .explanations import explain
    if not output_path(config,'validation','report.json').exists(): validate_data(config,args)
    build_features(config,args)
    create_eda(config,args)
    approval=output_path(config,'approval.json')
    if not output_path(config,'search','complete.json').exists():
        run_pilot(config,args)
        proposal=read_json(output_path(config,'search_proposal.json'))
        write_json(approval,{'approved':True,'proposal_sha256':proposal['proposal_sha256'],
            'user_confirmation':'Train both models as before, strictly before 2026-09-01. Apply package-september-fill-predictor.',
            'scope':'20,000 tuning rows; 100,000 selection/final rows; 32 search fits; existing resource limits',
            'authorization_source':'Direct user instructions and explicit apply request in this conversation'})
        tune(config,Namespace(pilot=False,approval_json=str(approval)))
    if not output_path(config,'models','selected.joblib').exists(): train(config,Namespace(approval_json=str(approval)))
    if not output_path(config,'test_evaluation_complete.json').exists(): evaluate(config,args)
    if not output_path(config,'predictions','daily_comparison.csv').exists(): predict(config,args)
    if not output_path(config,'unseen_sites','metrics.json').exists(): unseen_sites(config,args)
    if not output_path(config,'importance','diagnostics.json').exists(): explain(config,args)
    from .reporting import report
    report(config,args)
    from .package import export_product
    from .verify import verify
    export_product(config); verify(config,args)
    logging.info('Current run and standalone package verified; cleanup is a separate step.')

if __name__=='__main__': run_cli('Train, compare and package the September next-day predictor.',run)
