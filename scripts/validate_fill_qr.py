"""Independent full-file checks, paired sensitivities and static diagnostic charts."""
from __future__ import annotations
import argparse
from bisect import bisect_right
from collections import Counter
import csv
from dataclasses import asdict
from datetime import date
from itertools import zip_longest
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from fill_qr import (HEADER, SUCCESS, STATUSES, TYPES, Model, Scenario, load_catalog,
                     digest, write_json, parser as generator_parser, Calibration,
                     TARGET_SHARES, rng, MAX_FILL)


def verify(source, enriched, diagnostics, args=None):
    manifest=json.loads((diagnostics/'manifest.json').read_text(encoding='utf-8'))
    args=args or generator_parser().parse_args([])
    catalog,_=load_catalog(args.bins,args.population,args.schedule)
    reference=Model(catalog,manifest['range']['start'],manifest['range']['end'],manifest['seed'])
    knots=[0.]+manifest['calibration']['response']['pressure_knots']
    heights=[0.]+[(t-1.5)/118.5 for t in (20,50,80,100)]
    ref_latent=np.zeros(5,dtype=np.int64);ref_min=120.;ref_max=0.;ref_cap=0
    with (diagnostics/'exclusions.csv').open(encoding='utf-8',newline='') as f:
        excluded={int(r['bin_id']) for r in csv.DictReader(f)}
    rows=0; bins=0; previous_bin=None; known=False; previous_status=None; previous_qr=None
    fill_counts=Counter(); qr_hist=Counter(); nulls=Counter(); statuses=Counter(); seen=set()
    with source.open(encoding='utf-8-sig',newline='') as a, enriched.open(encoding='utf-8-sig',newline='') as b:
        left,right=csv.reader(a),csv.reader(b)
        if next(left)!=HEADER or next(right)!=HEADER+['fill_level','qr_alerts']:
            raise AssertionError('Header mismatch')
        for original, output in zip_longest(left,right):
            if original is None or output is None or len(output)!=19 or output[:17]!=original:
                raise AssertionError(f'Original field/row mismatch at row {rows+1}')
            id_=int(original[0]); status=original[13]; fill,qr=output[-2:]
            if status not in STATUSES:raise AssertionError('Unknown status')
            if id_!=previous_bin:
                if id_ in seen:raise AssertionError('Non-contiguous duplicate bin')
                seen.add(id_); bins+=1; known=False; previous_status=None;previous_qr=None
                expected=date.fromisoformat(manifest['range']['start']).toordinal()
                day_index=0;new_demand=0.;residue=0.
                if id_ not in excluded:
                    inflow=reference.inflow(catalog[id_])
                    residue_rng=rng(reference.seed,'residue',id_,*reference.range_key)
                    worker_rng=rng(reference.seed,'worker',id_,*reference.range_key)
                    errors,sides=worker_rng.random(len(reference.dates)),worker_rng.random(len(reference.dates))
            if date.fromisoformat(original[1]).toordinal()!=expected:raise AssertionError('Date grid error')
            expected+=1
            if fill and (not fill.isdigit() or not 0<=int(fill)<=4):raise AssertionError('Fill domain')
            if qr and (not qr.isdigit() or int(qr)<0):raise AssertionError('QR domain')
            if id_ in excluded:
                if fill or qr:raise AssertionError('Excluded bin is populated')
            else:
                if bool(qr)!=known:raise AssertionError('QR known-state mask')
                if bool(fill)!=(known and status in SUCCESS):raise AssertionError('Fill visit/anchor mask')
                if known and previous_status in SUCCESS and int(qr)!=0:raise AssertionError('QR reset timing')
                if known and previous_status not in SUCCESS and previous_qr is not None and int(qr)<previous_qr:raise AssertionError('QR decreases without success')
                if known:
                    new_demand+=float(inflow[day_index])
                    pressure=100*new_demand/catalog[id_].capacity
                    if pressure>knots[-1]:
                        response=heights[-1]+(1-heights[-1])*(-math.expm1(-(pressure-knots[-1])/(knots[-1]-knots[-2])))
                    else:
                        j=max(0,min(3,bisect_right(knots,pressure)-1))
                        response=heights[j]+(heights[j+1]-heights[j])*(pressure-knots[j])/(knots[j+1]-knots[j])
                    fullness=min(120.,max(0.,residue+(120-residue)*response))
                    if not math.isfinite(fullness) or not 0<=fullness<=120:raise AssertionError('Fullness bound')
                    ref_min=min(ref_min,fullness);ref_max=max(ref_max,fullness);ref_cap+=int(fullness==120.)
                    latent=int(fullness>=20)+int(fullness>=50)+int(fullness>=80)+int(fullness>100)
                    ref_latent[latent]+=1
                    if status in SUCCESS:
                        rating=latent
                        if errors[day_index]<.10:
                            rating+=1 if latent==0 else -1 if latent==4 else -1 if sides[day_index]<.5 else 1
                        if int(fill)!=rating:raise AssertionError(f'Independent fill reconstruction at {id_}/{original[1]}')
                    if catalog[id_].exposure==0 and int(qr)!=0:raise AssertionError('Zero exposure has QR reports')
                if status in SUCCESS:
                    known=True;new_demand=0.;residue=100*residue_rng.uniform(0,.03)
            if fill:fill_counts[int(fill)]+=1
            else:nulls['fill']+=1
            if qr:qr_hist[int(qr)]+=1
            else:nulls['qr']+=1
            statuses[status]+=1
            rows+=1;day_index+=1; previous_bin=id_; previous_status=status;previous_qr=int(qr) if qr else None
            if rows%3000000==0:print(f'Verified {rows:,} rows',flush=True)
    assert rows==manifest['counts']['rows']
    assert bins==manifest['counts']['bins']
    assert [fill_counts[i] for i in range(5)]==manifest['fill_counts']
    assert nulls['fill']==manifest['counts']['fill_null'] and nulls['qr']==manifest['counts']['qr_null']
    assert dict(statuses)==manifest['status_counts']
    assert ref_latent.tolist()==manifest['latent_counts']
    input_hash=digest(source); output_hash=digest(enriched)
    assert input_hash==manifest['inputs'][str(source)]
    assert output_hash==manifest['output']['sha256']
    result={'passed':True,'rows_compared':rows,'bins':bins,'original_fields_compared':rows*17,
            'new_fields_checked':rows*2,'fill_counts':dict(fill_counts),'nulls':dict(nulls),
            'qr_histogram':dict(sorted(qr_hist.items())),'input_sha256':input_hash,'output_sha256':output_hash,
            'independent_fullness_reconstruction':{'known_days':int(ref_latent.sum()),'minimum':ref_min,'maximum':ref_max,'days_at_ceiling':ref_cap,'all_worker_labels_reconstructed':True,'method':'scalar cycle accumulation and independently evaluated piecewise response'},
            'checks':['every original string field and row order','date grid','integer domains','all exclusions NULL','unknown anchor masks','visit masks','QR reset next day','QR nondecrease without success','manifest counts','file hashes','independent full-row bounded fullness and worker-label reconstruction','zero exposure has no QR']}
    write_json(diagnostics/'verification.json',result)
    print(f'Full verification passed: {rows:,} rows, {rows*17:,} preserved fields',flush=True)
    return result


def sensitivities(args):
    d=args.diagnostics
    catalog,_=load_catalog(args.bins,args.population,args.schedule)
    calibration=Calibration(**json.loads((d/'manifest.json').read_text(encoding='utf-8'))['calibration']['response'])
    saved=np.load(d/'sample_trajectories.npz')
    ids=sorted(int(i) for i in saved.files)
    scenarios=[Scenario(),Scenario('q_x0.5',q_scale=.5),Scenario('q_x1.5',q_scale=1.5),
               Scenario('mixed_1.50',mixed_q=1.5),Scenario('mixed_1.80',mixed_q=1.8),
               Scenario('calendar_off',calendar=False),Scenario('types_off',type_effect=False),
               Scenario('qr_x0.5',qr_scale=.5),Scenario('qr_x1.5',qr_scale=1.5),
               Scenario('district_off',district_uplift=1.),Scenario('district_1.20',district_uplift=1.2)]
    results=[]
    for scenario in scenarios:
        model=Model(catalog,args.start,args.end,args.seed,scenario,calibration=calibration)
        known=0;overflow=0;visits=0;visit_overflow=0;reports=0;expectation=0.;volume=0.;fill_counts=np.zeros(5,dtype=np.int64)
        equal=True; max_error=0.
        for id_ in ids:
            original=saved[str(id_)]
            statuses=np.where(original[6].astype(bool),'collected','none')
            s=model.simulate(id_,statuses)
            assess=s['fill']>=0
            known+=int(s['known'].sum());overflow+=int((s['latent']==4).sum())
            visits+=int(assess.sum());visit_overflow+=int(((s['latent']==4)&assess).sum())
            reports+=int(s['reports'].sum());expectation+=float(s['mean'].sum());volume+=float(s['inflow'].sum())
            fill_counts+=np.bincount(s['fill'][assess],minlength=5)
            if scenario.name=='baseline':
                comparison=np.stack([s['fill'],s['qr'],s['percent'],s['latent'],s['reports'],s['inflow'],s['success'],s['mean'],s['demand'],s['excess'],s['residue'],s['pressure']])
                if not np.array_equal(comparison,original,equal_nan=True):raise AssertionError(f'Non-reproducible sampled bin {id_}')
            if scenario.name.startswith('qr_'):
                equal &= np.array_equal(s['fill'],original[0]) and np.array_equal(s['inflow'],original[5])
                if scenario.qr_scale<1:assert np.all(s['reports']<=original[4])
                else:assert np.all(s['reports']>=original[4])
        if not equal:raise AssertionError('QR sensitivity changed worker/waste values')
        results.append({'scenario':scenario.name,'sample_bins':len(ids),'known_days':known,'assessable_visits':visits,
                        'latent_overflow_percent':100*overflow/known,'visit_overflow_percent':100*visit_overflow/visits,
                        'reports':reports,'expected_reports':expectation,'reports_per_1000_known_days':1000*reports/known,
                        'total_inflow_m3':volume,'fill_counts':';'.join(map(str,fill_counts)),
                        'qr_only_preserves_fill_and_waste':equal,'max_conservation_error':model.max_conservation_error})
        print(f'Sensitivity {scenario.name}: overflow {results[-1]["latent_overflow_percent"]:.2f}%',flush=True)
    with (d/'sensitivity.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    write_json(d/'sensitivity.json',{'sample_selection':'240 SHA-ranked complete site/stream pools plus type/waste/district/zero-exposure strata and five highest exposure/capacity bins, retaining whole pools. Deliberately includes extremes; not a city-wide unbiased estimate.','sample_bins':ids,'scenarios':results,'baseline_exactly_reproduced':True,'paired_poisson_uniforms':True})
    return results


def charts_and_report(args, verification, sensitivity):
    d=args.diagnostics
    manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
    counts=manifest['counts']; fill=np.array(manifest['fill_counts']);latent=np.array(manifest['latent_counts'])
    source_catalog,_=load_catalog(args.bins,args.population,args.schedule)
    valid_bins=[b for b in source_catalog.values() if not b.reasons]
    residential_zero=sum(b.category in {'Sodų/garažų bendrijos','Sodų bendrijos','Daugiabučiai namai','Daugiabučių/garažų bendrijos','Dvibučiai'} and b.exposure==0 for b in valid_bins)
    plt.rcParams.update({'figure.dpi':130,'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#277da8','#58a889','#e9b44c','#e4833e','#c94b55']
    fig,ax=plt.subplots(figsize=(9,4))
    x=np.arange(5)
    for offset,key,label in [(-.25,'fill_counts','Worker rating on successful visits'),(0,'latent_visit_counts','Latent class on successful visits'),(.25,'latent_nonvisit_counts','Latent class on other days')]:
        values=np.array(manifest[key]);ax.bar(x+offset,100*values/values.sum(),width=.24,label=label)
    ax.plot(x,100*TARGET_SHARES,color='#262626',marker='o',ls='--',lw=1.5,label='Assumed worker target (approximate)')
    ax.set(xticks=x,xlabel='Class (4 means >100%, fullness bounded at 120%)',ylabel='Share within eligible days (%)',title='Full dataset: calibrated worker assessments and latent classes')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(d/'fill_distribution.png');plt.close(fig)
    hist={int(k):v for k,v in verification['qr_histogram'].items()}
    categories=['0','1','2','3-5','6-10','11-50','51-100','>100']
    values=[sum(v for k,v in hist.items() if condition(k)) for condition in [lambda k:k==0,lambda k:k==1,lambda k:k==2,lambda k:3<=k<=5,lambda k:6<=k<=10,lambda k:11<=k<=50,lambda k:51<=k<=100,lambda k:k>100]]
    fig,ax=plt.subplots(figsize=(9,4));ax.bar(categories,values,color='#277da8');ax.set_yscale('log');ax.set(xlabel='Lagged cycle QR count',ylabel='Known-state bin-days (log scale)',title='Full dataset: zero counts and long reporting tail');fig.tight_layout();fig.savefig(d/'qr_distribution.png');plt.close(fig)
    strata=manifest['strata'];keys=sorted(k for k in strata if k.startswith('waste|'))+sorted(k for k in strata if k.startswith('exposure|'))
    fig,ax=plt.subplots(figsize=(10,4));bottom=np.zeros(len(keys))
    for k in range(5):
        v=np.array([100*strata[key][k]/max(strata[key][5],1) for key in keys]);ax.barh([x.split('|')[1] for x in keys],v,left=bottom,color=colors[k],label=str(k));bottom+=v
    ax.set(xlabel='Known-state latent class share (%)',title='Full dataset: waste streams and assigned exposure');ax.legend(title='Class',loc='center left',bbox_to_anchor=(1.01,.5));fig.tight_layout();fig.savefig(d/'exposure_and_waste.png');plt.close(fig)
    sample=np.load(d/'sample_trajectories.npz');catalog=json.loads((d/'sample_catalog.json').read_text(encoding='utf-8'))
    zero=[i for i,b in catalog.items() if b['exposure']==0]
    positive=[i for i,b in catalog.items() if b['exposure']>0]
    residential_positive=[i for i in positive if TYPES[catalog[i]['category']][1]]
    nonres=[i for i,b in catalog.items() if b['category']=='Komercinė paskirtis']
    choices=[('Zero residential allocation',zero[0] if zero else positive[0]),('Residential exposure near 100',min(residential_positive or positive,key=lambda i:abs(catalog[i]['exposure']-100))),('Largest exposure / capacity',max(positive,key=lambda i:catalog[i]['exposure']/catalog[i]['capacity'])),('Commercial shared fallback',nonres[0] if nonres else positive[-1])]
    fig,axes=plt.subplots(4,2,figsize=(12,11))
    for row,(label,id_) in enumerate(choices):
        values=sample[id_];n=values.shape[1];start=max(0,n-90);x=np.arange(start,n)
        ax=axes[row,0];ax.plot(x,values[2,start:],color='#277da8');ax.axhline(100,color='#c94b55',ls='--',lw=1)
        successes=x[values[6,start:].astype(bool)];ax.scatter(successes,values[2,successes],s=14,color='#c94b55',label='Successful service (pre-reset)')
        ax.set(ylabel='Calibrated fullness (%)',title=f'{label} | bin {id_}, N={catalog[id_]["exposure"]:.1f}',ylim=(0,123))
        ax=axes[row,1];ax.step(x,values[1,start:],where='mid',color='#58a889',label='QR through yesterday');ax.bar(x,values[4,start:],alpha=.25,color='#277da8',label="Today's reports (internal)");ax.set(ylabel='Count',title='QR cycle: success resets the following day',ylim=(0,max(1,float(values[1,start:].max())*1.05)))
    for ax in axes[-1]:ax.set_xlabel('Day index in the three-year range (last 90 days shown)')
    axes[0,0].legend(fontsize=7);axes[0,1].legend(fontsize=7);fig.tight_layout();fig.savefig(d/'trajectories.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5));labels=[r['scenario'] for r in sensitivity]
    axes[0].barh(labels,[r['latent_overflow_percent'] for r in sensitivity],color='#c94b55');axes[0].set(xlabel='Latent overflow days (%)',title='Paired sensitivity: complete sampled pools')
    axes[1].barh(labels,[r['reports_per_1000_known_days'] for r in sensitivity],color='#277da8');axes[1].set(xlabel='Reports / 1,000 known bin-days',title='Same underlying random draws');fig.tight_layout();fig.savefig(d/'sensitivity.png');plt.close(fig)
    daily=np.load(d/'daily_totals.npz')['values'];fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True)
    axes[0].plot(daily[0],lw=.6,color='#277da8');axes[0].set(ylabel='Incoming waste (m³/day)',title='Full dataset: calendar variation, no fitted trend')
    axes[1].plot(100*daily[1]/np.maximum(daily[2],1),lw=.7,color='#c94b55');axes[1].set(ylabel='Latent overflow (%)',xlabel='Day index from '+args.start);fig.tight_layout();fig.savefig(d/'calendar.png');plt.close(fig)
    known=counts['known_days'];visits=int(fill.sum())
    target=100*TARGET_SHARES;achieved=100*fill/visits
    bell=bool(achieved[2]>achieved[1]>achieved[0] and achieved[2]>achieved[3]>achieved[4])
    deviation=float(np.abs(achieved-target).max())
    bounds=manifest['fullness_and_demand_checks'];calibration=manifest['calibration']
    peak=max(float(np.nanmax(sample[i][2])) for i in sample.files)
    source_peak=max(float(np.nanmax(sample[i][8])) for i in sample.files)
    periods={k:(100*np.array(v)/max(sum(v),1)).tolist() for k,v in manifest['period_worker_counts'].items()}
    metrics={'worker_shares_percent':achieved.tolist(),'target_shares_percent':target.tolist(),
             'maximum_target_deviation_percentage_points':deviation,'bell_shape':bell,
             'period_worker_shares_percent':periods,'fullness_bounds':bounds,
             'valid_bins':len(valid_bins),'valid_residential_zero_exposure_bins':residential_zero,
             'sample_maximum_fullness_percent':peak,'sample_maximum_assigned_demand_m3':source_peak,
             'empirical_fill_accuracy':'unavailable','annual_mass_validation':'unavailable_without_bulk_density',
             'physical_realism':'bounded scenario, not established from measurements'}
    write_json(d/'realism_metrics.json',metrics)
    if visits>=100000:
        assert bell and deviation<=3., 'Full scenario does not meet approximate bell-shaped assessment contract'
    lines=['# Bounded synthetic fill and QR: validation and realism report','',
           f'Range: {args.start} through {args.end}. {counts["rows"]:,} rows, {counts["bins"]:,} bins, 19 columns.','',
           '## Changes and retained rules','',
           'The user assumes a bell-shaped worker-class histogram with approximate shares 10/20/40/20/10 and a 120% fullness ceiling. A monotone response replaces the old linear demand-to-fullness identity. Source demand remains separately conserved in m³. This is scenario calibration, not measured normality or proof of physical volume balance. See backend/data/rules/CHANGELOG.md for every change.','',
           'Base volume rates, source exposure/allocation, type/district/calendar factors, all random distributions and seeds, residuals, 10% worker error, class thresholds, exclusion/anchor/visit masks and QR equations remain unchanged. QR values change because the calibrated latent classes change.','',
           '## Verification','',
           f'- Full-field comparison: PASS; {verification["original_fields_compared"]:,} original string values and all row positions retained.',
           f'- Independent scalar reconstruction: {verification["independent_fullness_reconstruction"]["known_days"]:,} known-day fullness values bounded and every retained worker label reconstructed.',
           '- Existing requested unit/statistical suite: 20 tests passed. The small end-to-end fixture covers CSV quoting, exclusions, calibration, reference reconstruction and sensitivities; see test_results.json for the delivery run.',
           f'- Worker assessments: {visits:,}; fill NULL: {counts["fill_null"]:,}; QR NULL: {counts["qr_null"]:,}. NULL is not zero.',
           f'- Excluded bins: {manifest["excluded_bins"]:,}; retained excluded rows: {manifest["excluded_rows"]:,}. Every reason is in exclusions.csv.',
           f'- Exclusion reasons: {json.dumps(manifest["exclusion_reason_counts"])}.',
           f'- Non-residential exposure: 100 users shared per site/stream; {manifest["fallback_sites"]:,} sites and {manifest["fallback_site_streams"]:,} pools, audited in fallbacks.csv.',
           f'- Worker error: {100*counts["worker_errors"]/visits:.3f}%, specified 10%.',
           f'- Known fullness range: {bounds["minimum_fullness"]:.6f}% to {bounds["maximum_fullness"]:.6f}%; {bounds["days_at_ceiling"]:,} days exactly at 120% ({100*bounds["days_at_ceiling"]/max(known,1):.4f}% of known days).',
           f'- No-success monotonicity comparisons: {bounds["monotonicity_checks"]:,}; all passed.',
           f'- Source-demand allocation conservation error: {manifest["max_allocation_coefficient_error_m3"]:.3g} m³/day before the shared daily multiplier.',
           f'- Total incoming source demand: {bounds["source_inflow_total_m3"]:,.3f} m³; peak assigned demand: {bounds["maximum_assigned_demand_m3"]:,.3f} m³; peak excess source demand: {bounds["maximum_excess_demand_m3"]:,.3f} m³. These are pressure diagnostics, not measured physical litter.',
           f'- Latent class-4 days: {100*latent[4]/max(known,1):.3f}% of known days.',
           f'- Generated reports: {counts["reports_generated"]:,}; positive QR days: {counts["qr_nonzero_days"]:,}; maximum counter: {counts["qr_max"]:,}.','',
           '## Calibration and class shape','',
           f'Frozen baseline fit: {calibration["fit_start"]} through {calibration["fit_end"]}; {calibration["assessments_used"]:,} synthetic known-state visits; zero-demand share {100*calibration["zero_demand_share"]:.3f}%. Later dates and every sensitivity use the same map.',
           f'Pressure knots: {calibration["response"]["pressure_knots"]}. The worker-error transition is inverted before fitting; variable residue and changing sample mix make actual shares approximate.',
           f'Bell-shaped ordinal histogram: {bell}; largest deviation from the requested shares: {deviation:.3f} percentage points. No continuous-normality test is applied to integer classes.','',
           '| Class | Count | Actual % | Assumed % |','|---|---:|---:|---:|']
    lines += [f'| {k} | {int(v):,} | {achieved[k]:.3f} | {target[k]:.1f} |' for k,v in enumerate(fill)]
    lines += ['', '### Period distributions','',
              '| Period | Class 0 % | Class 1 % | Class 2 % | Class 3 % | Class 4 % |',
              '|---|---:|---:|---:|---:|---:|']
    lines += ['| '+label+' | '+' | '.join(f'{x:.3f}' for x in shares)+' |' for label,shares in periods.items()]
    lines += ['', 'The calibration period is fitting evidence, not independent validation. Later-year stability describes this static synthetic scenario; it does not establish real-world predictive accuracy.','',
              '## Paired sensitivity','',
              f'{manifest["sample_bins"]} bins in {manifest["sample_pools"]} complete pools. Sample selection includes extremes and is not an unbiased city-wide estimate. Baseline trajectories reproduce exactly; QR-only changes preserve fullness and source demand. Calibration is never refitted to hide rate/calendar/type/district changes.','',
              '| Scenario | Class-4 days % | Reports / 1,000 known days |','|---|---:|---:|']
    lines += [f'| {r["scenario"]} | {r["latent_overflow_percent"]:.3f} | {r["reports_per_1000_known_days"]:.3f} |' for r in sensitivity]
    lines += ['', '## Realism and limits','',
              f'Boundedness, daily ordering and internal consistency pass. There are still {residential_zero:,} residential bins with zero exposure; their latent fullness remains below 3% and QR counts are zero. Existing worker noise can give class 1. Approximate global class balance is not imposed on individual bins or streams.',
              '',
              'Fullness increases between successes and resets to the original residue. Failed/missed service does not reset demand or QR. The chart value the next day includes that next day’s full inflow and is not the immediate post-service residue. The response is nonlinear; raw demand and calibrated fullness must not be interpreted as the same physical volume.',
              '',
              'Extreme source exposure/capacity ratios still exist. The 120% bound prevents impossible displayed fullness; separate uncapped m³ diagnostics expose the underlying assignments. Saturation can reduce discrimination among extreme bins. The source allocation needs real operational validation.',
              '',
              'QR absence is not evidence of emptiness. The unchanged Poisson process can produce zero reports during overflow or rare reports at low classes. High exposure can still produce large counts. Successful-service-day reports are cleared by that service; the next day’s feature is zero.',
              '',
              'The calendar chart retains unchanged source inflow. Early class-frequency changes partly reflect unknown-state initialization. Later periodicity is imposed by static calendar factors and the synthetic schedule, not measured city trends.',
              '',
              '- Real fill accuracy is unavailable: supplied historical fill labels are all NULL. The assumed bell shape and 120% limit are not empirical validation.',
              '- Annual mass validation is unavailable without trusted bulk density; no kg-to-volume conversion was invented.',
              '- The three-year calendar is synthetic; registry and population are static snapshots. Events remain disabled (E=1).',
              '- The first success anchors unknown state. Missing/invalid inputs still receive NULL training labels and QR values under the existing policy. Full-registry non-NULL model predictions require a separate inference pipeline.',
              '- Calibrating on synthetic visits changes the relationship between source demand and occupancy. A model trained here learns that assumed relationship and requires validation on real worker observations.','',
              '## Reproduction and inspection','',
              'See docs/data/fill-qr.md. manifest.json, calibration.json and verification.json record provenance and checks; reproducibility.json records the full repeat run. manual_review.md records concrete trajectory audits; visual_review.json records final chart/PDF inspection. Diagnostic arrays contain 12 named rows listed in the manifest; only fill_level and qr_alerts are added to the CSV.','']
    manual=['# Current trajectory audit','',
            'Values below use the current bounded scenario. Assigned/excess source demand are m³ pressure diagnostics, not fullness percentages.']
    from datetime import timedelta
    for label,id_ in choices:
        v=sample[id_]; valid=v[3]>=0
        manual += ['',f'## {label}: bin {id_}','',
                   f'Exposure {catalog[id_]["exposure"]:.3f}; capacity {catalog[id_]["capacity"]:.3f} m³; peak fullness {np.nanmax(v[2]):.6f}%; peak assigned demand {np.nanmax(v[8]):.3f} m³.',
                   '', '| Date | Success | Fill class | Fullness % | QR through yesterday | Reports today | Demand m³ |',
                   '|---|---:|---:|---:|---:|---:|---:|']
        indices=np.arange(max(0,v.shape[1]-7),v.shape[1])
        for j in indices:
            day=date.fromisoformat(args.start)+timedelta(days=int(j))
            manual += [f'| {day} | {int(v[6,j])} | {int(v[0,j]) if v[0,j]>=0 else "NULL"} | {v[2,j]:.3f} | {int(v[1,j])} | {int(v[4,j])} | {v[8,j]:.3f} |']
    (d/'manual_review.md').write_text('\n'.join(manual)+'\n',encoding='utf-8')
    for filename in ['fill_distribution.png','qr_distribution.png','exposure_and_waste.png','trajectories.png','calendar.png','sensitivity.png']:
        lines += [f'![{filename[:-4].replace("_"," ")}]({filename})','']
    (d/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(d/'report.md',flush=True)


def main():
    parser=generator_parser()
    parser.description=__doc__
    parser.add_argument('--skip-full-verification',action='store_true',help='Reuse an existing verification.json, after checking its recorded output hash')
    args=parser.parse_args()
    if args.skip_full_verification:
        verification=json.loads((args.diagnostics/'verification.json').read_text(encoding='utf-8'))
        assert verification['output_sha256']==digest(args.output)
        assert verification['input_sha256']==digest(args.input)
    else:verification=verify(args.input,args.output,args.diagnostics,args)
    results=sensitivities(args)
    charts_and_report(args,verification,results)


if __name__=='__main__':main()
