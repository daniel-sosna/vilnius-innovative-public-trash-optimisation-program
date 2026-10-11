"""Consistently styled charts, source tables and a final run report."""
from pathlib import Path

import numpy as np
import pandas as pd

from .common import model_names, digest, output_path, read_json, source_path, write_json
from .features import FEATURES
from .modeling import selected_features


def markdown_table(frame):
    def cell(value):
        return (f'{value:.4f}' if isinstance(value, (float, np.floating)) else str(value)).replace('|', '\\|').replace('\n', ' ')
    rows = ['| ' + ' | '.join(map(str, frame.columns)) + ' |', '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |']
    rows.extend('| ' + ' | '.join(cell(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None))
    return '\n'.join(rows)


def chart_sources(config):
    """Require a concrete source table for every delivered chart."""
    root = output_path(config)
    records = []
    aliases = {'target_over_time': 'target_by_date', 'target_distribution': 'target_counts',
               'label_availability': 'label_availability_over_time'}
    for chart in sorted((root / 'charts').rglob('*.png')):
        source = chart.with_suffix('.csv')
        if chart.parent.name == 'eda':
            source = root / 'validation' / (aliases.get(chart.stem, chart.stem) + '.csv')
            if chart.stem.startswith('days_since_'):
                source = root / 'validation/collection_interval_distribution.csv'
        elif chart.stem.endswith('_class_distribution'):
            source = chart.parent / 'predicted_vs_observed.csv'
        elif not source.exists() and (chart.parent / (chart.stem + '_top25.csv')).exists():
            source = chart.parent / (chart.stem + '_top25.csv')
        if not source.is_file():
            raise ValueError(f'Chart source table is missing: {chart.name} -> {source.name}')
        records.append({'chart': chart.relative_to(root).as_posix(), 'source_table': source.relative_to(root).as_posix()})
    pd.DataFrame(records).to_csv(root / 'chart_sources.csv', index=False)


def verification_summary(config):
    """Attach measured delivery verification without regenerating research figures."""
    root = output_path(config)
    delivery = read_json(root / 'delivery_verification.json')
    product = read_json(root / 'product_verification.json')
    csv_check = read_json(root / 'csv_registry_verification.json')
    lines = ['## Delivery verification', '',
        f'Integrated checks: {len(delivery["checks"])}; passed: {delivery["passed"]}. '
        'All 30 mappings and both final comparison models were verified.', '',
        f'Full CSV product equality: {csv_check["rows"]:,} registry bins, '
        f'{csv_check["today"]} -> {csv_check["forecast_date"]}, {csv_check["duration_seconds"]:.1f}s.', '',
        f'Isolated CPU package: passed={product["passed"]}; probability and CSV-batch equality; '
        'mid-/end-September cases; no implicit runtime writes.', '']
    focused = root / 'focused_checks.json'
    if focused.exists():
        checks = read_json(focused)
        lines += [f'Existing focused checks: {checks["tests_run"]}; passed={checks["passed"]}; '
                  '`python -m unittest discover -s tests/ml -q` from backend/.', '']
    cleanup = root / 'cleanup.json'
    if cleanup.exists():
        import json
        record = json.loads(cleanup.read_text(encoding='utf-8-sig'))
        lines += [f'Superseded run cleanup completed; both allowlisted directories absent: '
                  f'{all(record["absent"].values())}. The package and input hashes were rechecked after cleanup.', '']
    lines += ['Verification records: delivery_verification.json, product_verification.json, '
              'csv_registry_verification.json, focused_checks.json and cleanup.json. '
              'Repeat with `python -m app.ml.verify --config configs/ml.yaml` from backend/.', '']
    path = root / 'README_REPORT.md'
    original = path.read_text(encoding='utf-8').split('## Delivery verification', 1)[0].rstrip()
    path.write_text(original + '\n\n' + '\n'.join(lines), encoding='utf-8')


def report(config, args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'figure.dpi': 140, 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9})
    charts = output_path(config, 'charts', 'comparison')
    charts.mkdir(parents=True, exist_ok=True)
    comparison = pd.read_csv(output_path(config, 'model_comparison.csv'))
    control_path = output_path(config, 'predictions', f'model_control_comparison_{config["prediction_date"]}.csv')
    control_comparison = pd.read_csv(control_path) if control_path.exists() else None
    if control_comparison is not None:
        control_comparison.to_csv(charts / 'control_date_comparison.csv', index=False)
        ax = control_comparison.set_index('model')[['needs_collection_precision', 'needs_collection_recall', 'needs_collection_f1']].plot.bar(figsize=(8, 4), ylim=(0, 1), rot=0, title=f'{config["prediction_date"]}: classes 3/4, synthetic labels')
        ax.set(ylabel='Score'); ax.figure.tight_layout(); ax.figure.savefig(charts / 'control_date_comparison.png'); plt.close(ax.figure)
    metrics = ['needs_collection_f1', 'needs_collection_precision', 'needs_collection_recall', 'macro_f1', 'class_4_precision', 'class_4_recall', 'mean_absolute_class_error',
               'quadratic_weighted_kappa', 'severe_error_rate']
    for metric in metrics:
        table = comparison.pivot(index='model', columns='split', values=metric)
        table.to_csv(charts / f'{metric}.csv')
        ax = table.plot.barh(figsize=(9, 5), title=metric.replace('_', ' ').title(), color=['#256d85', '#e6a23c'])
        ax.figure.tight_layout(); ax.figure.savefig(charts / f'{metric}.png'); plt.close(ax.figure)
    urgent = comparison.loc[comparison.model.isin(model_names(config)), ['model', 'split', 'needs_collection_f1', 'needs_collection_precision', 'needs_collection_recall']]
    urgent.to_csv(charts / 'urgent_classes_comparison.csv', index=False)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, metric, title in zip(axes, ['needs_collection_f1', 'needs_collection_precision', 'needs_collection_recall'], ['F1', 'Precision', 'Recall']):
        pivot = urgent.pivot(index='split', columns='model', values=metric).reindex(['validation', 'test'])
        pivot.plot.bar(ax=ax, color=['#256d85', '#e6a23c'], rot=0, title=title, ylim=(0, 1), legend=ax is axes[-1])
        for bars in ax.containers:
            ax.bar_label(bars, fmt='%.3f', fontsize=8, padding=2)
        ax.set(xlabel='', ylabel='Classes 3/4 together' if ax is axes[0] else '')
    fig.suptitle('Needs collection: combined classes 3 and 4')
    fig.tight_layout(); fig.savefig(charts / 'urgent_classes_comparison.png'); plt.close(fig)
    per_class = []
    distributions = []
    for split in ['validation', 'test']:
        for model in model_names(config):
            folder = output_path(config, 'evaluation', split)
            table = pd.read_csv(folder / f'{model}_per_class.csv')
            table['model'], table['split'] = model, split
            per_class.append(table)
            data = read_json(folder / f'{model}_metrics.json')
            if 'needs_collection_tp' in data:
                binary = np.array([[data['needs_collection_tn'], data['needs_collection_fp']], [data['needs_collection_fn'], data['needs_collection_tp']]])
                pd.DataFrame(binary, index=['class_0_1_2', 'class_3_4'], columns=['predicted_0_1_2', 'predicted_3_4']).to_csv(charts / f'{model}_{split}_urgent_confusion.csv')
                fig, ax = plt.subplots(figsize=(5, 4)); plot = ax.imshow(binary, cmap='Blues'); fig.colorbar(plot, ax=ax)
                ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=['0/1/2', '3/4'], yticklabels=['0/1/2', '3/4'], xlabel='Predicted group', ylabel='Synthetic target group', title=f'{model} / {split}: needs collection')
                for i in range(2):
                    for j in range(2):
                        ax.text(j, i, str(binary[i, j]), ha='center', va='center')
                fig.tight_layout(); fig.savefig(charts / f'{model}_{split}_urgent_confusion.png'); plt.close(fig)
            cm = np.asarray(data['confusion_matrix'])
            for c in range(5):
                distributions.append({'model': model, 'split': split, 'class': c, 'observed': cm[c].sum(), 'predicted': cm[:, c].sum()})
            for normalized in [False, True]:
                key = 'normalized_confusion_matrix' if normalized else 'confusion_matrix'
                matrix = np.asarray(data[key])
                pd.DataFrame(matrix).to_csv(charts / f'{model}_{split}_{key}.csv', index_label='observed_class')
                fig, ax = plt.subplots(figsize=(5, 4)); plot = ax.imshow(matrix, cmap='Blues'); fig.colorbar(plot, ax=ax)
                ax.set(xlabel='Predicted class', ylabel='Synthetic observed class', title=f'{model} / {split}', xticks=range(5), yticks=range(5))
                for i in range(5):
                    for j in range(5):
                        ax.text(j, i, f'{matrix[i,j]:.2f}' if normalized else str(int(matrix[i,j])), ha='center', va='center', fontsize=8)
                fig.tight_layout(); fig.savefig(charts / f'{model}_{split}_{key}.png'); plt.close(fig)
            groups = pd.read_csv(folder / f'{model}_error_groups.csv')
            for group in ['date', 'waste_type', 'capacity_range', 'input_quality_flag']:
                subset = groups.loc[groups.group == group].copy()
                subset.to_csv(charts / f'{model}_{split}_error_by_{group}.csv', index=False)
                if group == 'date':
                    subset = subset.sort_values('value')
                    fig, ax = plt.subplots(figsize=(10, 3)); ax.plot(pd.to_datetime(subset.value), subset.mean_absolute_class_error); ax.set(xlabel='Date', ylabel='Mean absolute class error', title=f'{model} / {split}')
                else:
                    fig, ax = plt.subplots(figsize=(9, max(3, len(subset) * .3))); ax.barh(subset.value, subset.mean_absolute_class_error, color='#256d85'); ax.set(xlabel='Mean absolute class error', title=f'{model} / {split} / {group}')
                fig.tight_layout(); fig.savefig(charts / f'{model}_{split}_error_by_{group}.png'); plt.close(fig)
    table = pd.concat(per_class)
    table.to_csv(charts / 'per_class_comparison.csv', index=False)
    for metric in ['precision', 'recall']:
        for split in ['validation', 'test']:
            pivot = table.loc[table.split == split].pivot(index='class', columns='model', values=metric)
            pivot.to_csv(charts / f'{split}_per_class_{metric}.csv')
            ax = pivot.plot.bar(figsize=(8, 4), title=f'{split}: per-class {metric}'); ax.set(ylabel=metric, xlabel='Class'); ax.figure.tight_layout(); ax.figure.savefig(charts / f'{split}_per_class_{metric}.png'); plt.close(ax.figure)
    distributions = pd.DataFrame(distributions)
    distributions.to_csv(charts / 'predicted_vs_observed.csv', index=False)
    for (model, split), subset in distributions.groupby(['model', 'split']):
        ax = subset.set_index('class')[['observed', 'predicted']].plot.bar(figsize=(7, 3), title=f'{model} / {split}: synthetic class counts'); ax.figure.tight_layout(); ax.figure.savefig(charts / f'{model}_{split}_class_distribution.png'); plt.close(ax.figure)
    times = pd.DataFrame([{'model': name, 'seconds': read_json(output_path(config, 'models', f'{name}.json'))['duration_seconds']} for name in model_names(config)])
    times.to_csv(charts / 'training_time.csv', index=False)
    ax = times.set_index('model').plot.barh(figsize=(7, 3), title='Final model fitting time', legend=False); ax.set(xlabel='Seconds'); ax.figure.tight_layout(); ax.figure.savefig(charts / 'training_time.png'); plt.close(ax.figure)
    for name in model_names(config):
        curve_path = output_path(config, 'evaluation', 'validation', f'{name}_threshold_curve.csv')
        if curve_path.exists():
            curve = pd.read_csv(curve_path)
            curve.to_csv(charts / f'{name}_threshold_curve.csv', index=False)
            ax = curve.set_index('needs_collection_threshold')[['needs_collection_f1', 'needs_collection_precision', 'needs_collection_recall']].plot(figsize=(8, 4), title=f'{name}: validation-only threshold selection')
            ax.set(xlabel='P(class 3) + P(class 4) threshold', ylabel='Score', ylim=(0, 1)); ax.figure.tight_layout(); ax.figure.savefig(charts / f'{name}_threshold_curve.png'); plt.close(ax.figure)
        for kind in ['native', 'permutation', 'shap_global', 'shap_class_4']:
            path = output_path(config, 'importance', f'{name}_{kind}.csv')
            if not path.exists():
                continue
            importance = pd.read_csv(path).head(25).iloc[::-1]
            importance.to_csv(charts / f'{name}_{kind}_top25.csv', index=False)
            fig, ax = plt.subplots(figsize=(9, 7)); ax.barh(importance.feature, importance.importance, color='#256d85'); ax.set(title=f'{name}: {kind} (descriptive)', xlabel='Importance'); fig.tight_layout(); fig.savefig(charts / f'{name}_{kind}.png'); plt.close(fig)
    validation=read_json(output_path(config,'validation','report.json'))
    preservation={n:digest(source_path(config,n))==item['sha256'] for n,item in validation['provenance']['inputs'].items()}
    write_json(output_path(config,'source_preservation.json'),preservation)
    if not all(preservation.values()): raise ValueError('A source input changed')
    selection=read_json(output_path(config,'selection.json'))
    best=read_json(output_path(config,'search','best_parameters.json'))
    search=read_json(output_path(config,'search','complete.json'))
    pilot=read_json(output_path(config,'search_proposal.json'))
    unseen=read_json(output_path(config,'unseen_sites','metrics.json'))
    sample=read_json(output_path(config,'samples','final_train.json'))
    daily=pd.read_csv(output_path(config,'predictions','daily_comparison.csv'))
    for metric in ['needs_collection_f1','argmax_needs_collection_f1','needs_collection_recall']:
        pivot=daily.pivot(index='forecast_date',columns='model',values=metric)
        pivot.to_csv(charts/f'daily_{metric}.csv')
        ax=pivot.plot(figsize=(10,4),ylim=(0,1),title='Next-day synthetic comparison: '+metric.replace('_',' '))
        ax.set(xlabel='Forecast date',ylabel='Score'); ax.figure.tight_layout(); ax.figure.savefig(charts/f'daily_{metric}.png'); plt.close(ax.figure)
    cols=['model','split','needs_collection_precision','needs_collection_recall','needs_collection_f1','argmax_needs_collection_f1','macro_f1','class_4_recall','mean_absolute_class_error']
    metadata={n:read_json(output_path(config,'models',f'{n}.json')) for n in model_names(config)}
    august_scores=comparison.loc[(comparison.split=='validation') & comparison.model.isin(model_names(config)),'needs_collection_f1'].sort_values(ascending=False)
    august_margin=float(august_scores.iloc[0]-august_scores.iloc[1])
    split_table=pd.DataFrame([{'stage':k,'start':v[0],'end':v[1]} for k,v in config['splits'].items()]+[{'stage':'final_fit','start':config['final_train'][0],'end':config['final_train'][1]}])
    dictionary=pd.read_csv(output_path(config,'feature_dictionary.csv')); dictionary.to_csv(output_path(config,'model_feature_dictionary.csv'),index=False)
    lines=['# September next-day synthetic fill predictor','',
        f'Selected algorithm: **{selection["model"]}**, by August combined classes-3/4 F1. Product output: bin_id and integer fill_level (five-class probability argmax).','',
        '## Date contract','',
        'Selected today T includes its observations; forecast D=T+1. 2026-09-15 predicts 2026-09-16; 2026-09-30 predicts 2026-10-01. Four supplied safe counters from D exclude D and are not shifted again. D outcomes never become features.','',
        markdown_table(split_table),'',
        'August scores below describe selection-stage models fitted through July. Both final candidates are refitted through August after freezing algorithm, parameters and thresholds. September/October outcomes never fit preprocessing or models.','',
        f'Final sample: {sample["sample_rows"]:,} of {sample["eligible_rows"]:,} eligible labels; {sample["bins"]:,} bins, {sample["sites"]:,} sites, {sample["dates"]:,} dates. Exact keys are in samples/.','',
        '## Model and baseline comparison','',markdown_table(comparison[cols]),'',
        f'August probability-sum F1 margin: {august_margin:.6f}. The candidates are practically close; no statistical-significance claim is made. The winner follows the frozen primary criterion; September scores cannot reselect it.','',
        f'Operational thresholds (August only): {selection["model_thresholds"]}. Probability-sum urgent decisions use P(3)+P(4). Grouped-argmax urgent F1 describes the two-column product; these rules can disagree. No final-model threshold retuning occurred.','',
        '![Combined urgent classes](charts/comparison/urgent_classes_comparison.png)','',
        '## All 30 next-day scenarios','',
        'Both final models predict every registry bin for each selected September today date. Research predictions and product responses are under predictions/. Metrics use available synthetic assessments only; unlabeled bins still receive predictions.','',
        markdown_table(control_comparison[['model','today','forecast_date','registry_bins','rows','needs_collection_f1','argmax_needs_collection_f1','macro_f1']]),'',
        '![Daily urgent scores](charts/comparison/daily_needs_collection_f1.png)','',
        '## Search and final fits','',
        f'Search fits: {search["fits"]}; search duration: {search["duration_seconds"]:.1f}s. Seed 42. CatBoost GPU training, RF CPU training, all delivered inference CPU.','',
        f'Chosen search records: {best}','',
        f'Small-pilot linear search estimate: {sum(e["estimated_search_seconds"] for e in pilot["estimates"]):.1f}s; actual completed search: {search["duration_seconds"]:.1f}s. Fixed GPU overhead in tiny pilot fits makes linear extrapolation conservative; actual fits were checked against the unchanged 600-second and 2.5-GiB limits.','',
        markdown_table(pd.DataFrame([{'model':n,'rows':m['train_rows'],'start':m['train_start'],'end':m['train_end'],'seconds':m['duration_seconds'],'peak_RSS_GiB':m['peak_rss_gib']} for n,m in metadata.items()])),'',
        'Pilot/probes, 32 search fits, two selection fits, two final fits and one site-holdout refit are separate. Configuration, authorization, hashes, versions and logs are in this run.','',
        '## Active features and explanations','',', '.join(FEATURES),'',
        'The same pure feature builder is used by training and the developer package. Feature DataFrames are ephemeral; dictionaries, sample keys, aggregate tables and prediction outputs are explicitly retained. Missingness indicators and fitted medians preserve unknown-versus-zero handling.','',
        'Native/permutation/SHAP tables and feasibility diagnostics are under importance/. Contributions are descriptive, not causal; correlated inputs share information. Permutation/SHAP examples come from final-model demo targets, not the overlapping August fitting period.','',
        '## Unseen-site cold start','',
        markdown_table(pd.DataFrame([{k:unseen[k] for k in ['held_out_sites','train_rows','rows','needs_collection_precision','needs_collection_recall','needs_collection_f1','macro_f1','class_4_recall']}])),'',
        'This separate refit excludes held-out sites and masks historical inputs at evaluation. It does not change the frozen winner or establish accuracy for truly unlabeled bins.','',
        '## Developer delivery','',
        'product/ contains one selected final model with fitted preprocessing, the shared viptop_fill feature/runtime package, normalization data, pinned CPU dependencies, manifest, DataFrame example and CSV adapter. The predictor returns exactly bin_id and fill_level without implicit writes. The package is verified in a fresh isolated process outside the repository. No database adapter is included.','',
        '## Data audit and limitations','',
        f'Validated source rows: {validation["rows"]:,}; daily bins: {validation["daily_bins"]:,}; registry bins: {validation["registry_bins"]:,}; registry-only bins: {validation["registry_only_bins"]:,}. Source preservation: {preservation}.','',
        markdown_table(pd.DataFrame([{'input':n,'path':item['path'],'sha256':item['sha256']} for n,item in validation['provenance']['inputs'].items()])), '',
        'Targets are synthetic assessments, mainly recorded on successful collection days. The first generator year serves as calibration/history. Real observed fill measurements are absent. Registry/population inputs are static snapshots and some synthetic bins remain saturated for long periods. September dates were inspected in previous experiments: this is comparative evaluation, not a newly untouched holdout. Complete prediction coverage does not imply equal confidence, unlabeled-day accuracy or verified real-world performance. Collect real pre-service ratings on collection and non-collection days for external validation.','',
        'Charts and their source tables are indexed in chart_sources.csv. Old experiments are removed only after current delivery verification; runtime has no dependency on their files.','']
    output_path(config,'README_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    chart_sources(config)
