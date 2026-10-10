"""Publish current rules from the supplied source with narrow, audited edits."""
from pathlib import Path
import argparse
import difflib
import re
import shutil
from xml.sax.saxutils import escape


def adapt_schema(source: str) -> str:
    text = source.replace('Version 2.1 | 9 October 2026 | Specification, not an implemented generator',
                          'Version 3.0 | 10 October 2026 | Adapted to the existing three-year bin-day export')
    text = text.replace('`uzpildymo_lygis`', '`fill_level`').replace('`qr_perpildymo_pranesimu`', '`qr_alerts`')
    text = text.replace('`(konteinerio_id, data)`', '`(bin_id, date)`')
    text = text.replace('assessable historical visit dates', 'assessable synthetic successful collection dates in this export')
    text = text.replace('Multiple raw rows may describe a duplicate record or different actions within one visit. Resolve them to one reviewed service outcome; remove exact duplicates. Conflicting outcomes or distinct visits on the same date fail validation instead of inventing a second visit.',
        'The input already has one resolved `collection_status` per `(bin_id, date)`. Reject all duplicate daily rows, including exact duplicates, to preserve the input-row contract. Do not join the one-month raw history onto the three-year synthetic calendar or invent a second visit.')
    start = text.index('Let a be a site, w a waste stream')
    end = text.index('### Use all ten supplied site categories', start)
    text = text[:start] + r'''Let a be `site_id`, w `waste_type`, i `bin_id`, and d `date`. `capacity_m3` is positive capacity $V_{i,d}$. Let $J_{a,w,d}$ contain valid bins at the same physical site and waste stream, including different object categories. The roster, capacities, districts and population allocation are constant snapshots over 2023-10-10..2026-10-09, not historical measurements.

For residential categories, use the existing nonnegative `resident_factor` directly as $N_{i,d}$. It is already a per-bin exposure allocated by the existing population algorithm; do not allocate it again, sum it across waste streams as unique people, or divide by capacity twice. A valid zero remains zero.

For non-residential categories no verified equivalent-user count exists in these inputs. Share the approved 100-user fallback once per physical site and stream, across all valid non-residential categories at that site, in proportion to capacity:

$$
N_{i,d}=100\,\frac{V_{i,d}}{\sum_{j\in J^{\mathrm{nonres}}_{a,w,d}}V_{j,d}}
$$

The same equivalent users can use different waste streams; 100 is not multiplied by the number of categories. Record every fallback and all exclusions from its allocation pool. Invalid bins receive no generated load; their unknown exposure is not imputed into residential bins.

''' + text[end:]
    text = text.replace('Use the existing site/object-type field;', 'Use the existing `object_group` field;')
    text = text.replace('Let $\\tau_a$ denote the category; use $H_{\\tau_a}$ from the table.', 'Let $\\tau_i$ denote each bin\'s category; use $H_{\\tau_i}$ from the table, including at mixed-category sites.')
    start = text.index('Residential categories use valid nonnegative')
    end = text.index('### Base volume rates', start)
    text = text[:start] + '''Residential exposure comes from `resident_factor`, not a new site population. No equivalent-user column is supplied for non-residential categories, so the shared fallback above applies. An irrelevant zero in `resident_factor` does not prove a non-residential site has zero users. Future verified equivalent-user counts require an explicit reviewed input contract; none are inferred here.

**[USER-APPROVED INPUT EXCLUSION]** Keep every original row, but set both new columns to NULL for bins with missing/unsupported `object_group`, unknown waste stream, non-positive/non-finite capacity, missing/negative/non-finite residential exposure, or unresolved district. Also exclude all bins at sites with contradictory canonical districts. Audit every bin and reason; do not silently map or impute categories. Structural errors (duplicate dates, missing dates, changed static fields or unknown service statuses) still fail the run. Empty CSV fields represent NULL, not zero.

Reviewed existing waste keys are `Mixed municipal waste`, `Paper/plastic waste` and `Glass waste`. Future supported scenario keys are `Food/organic waste` and `Textiles`; they do not occur in this export and retain their original rates.

''' + text[end:]
    text = text.replace('`kiek_buvo_svenciu` or `kiek_buvo_artimu_renginiu`', '`holidays_since_last_collection` or any cumulative event counter')
    text = text.replace('Today\'s calendar may generate today\'s future target,', 'Derive official Lithuanian holidays from `date`; do not interpret `holidays_since_last_collection` as a daily flag. No event-occurrence feed exists, so E=1 throughout this run and the event effect is explicitly disabled. Today\'s calendar may generate today\'s future target,')
    start = text.index('### Site inflow and capacity-weighted allocation')
    end = text.index('### State transition', start)
    text = text[:start] + r'''### Site inflow and exposure-weighted allocation

The original homogeneous-site formula must be generalized because the export already contains per-bin resident exposure and mixed object categories. Define effective exposure:

$$
D_{i,d}=N_{i,d}H_{\tau_i}T_i
$$

$$
Q_{a,w,d}=\frac{q_w}{1000}\left(\sum_{i\in J_{a,w,d}}D_{i,d}\right)G_{a,w}S_dW_dh_dE_{a,d}Z_{a,w,d}
$$

$$
A_{i,d}=Q_{a,w,d}\,\frac{D_{i,d}B_i}{\sum_{j\in J_{a,w,d}}D_{j,d}B_j}
$$

$$
\sum_{i\in J_{a,w,d}}A_{i,d}=Q_{a,w,d}
$$

When all D are zero, set Q=A=0 instead of dividing by zero. For homogeneous H and T with N proportional to capacity, this is exactly the original Q and capacity-weighted allocation. For mixed categories it applies each approved type multiplier once and preserves the existing exposure allocation. Q and A are m³/day. Allocation does not simulate diversion to neighbouring bins once a bin fills.

''' + text[end:]
    text = text.replace('A successful emptying requires an emptying operation and successful service (reviewed mapping such as `veiksmas = Ištuštinti` plus `aptarnavimas = Aptarnautas`). `Neaptarnautas` leaves both backlog and QR cycle unchanged.',
        'In this synthetic calendar, `collection_status` values `collected` and `retry_collected` mean successful emptying (e=1). Values `none`, `failed` and `missed` mean e=0 and leave backlog and QR cycle unreset. These are simulated outcomes, not independently confirmed historical visits.')
    text = text.replace("the day's historical visit with ability to assess", "the day's synthetic successful service, assumed assessable")
    text = text.replace('A failed service gets a label only when arrival and ability to assess are confirmed. Inaccessible or ambiguous failed visits get NULL.', 'No arrival/assessment evidence is available for `failed` or `missed` rows, so both receive NULL fill labels. A future confirmed assessable failed visit would require a reviewed input contract.')
    text = text.replace('`ankstesnis_lygis` is the last retained worker rating from a date before today, not yesterday\'s latent truth. It remains the previous **pre-emptying** rating even after successful emptying.',
        'No previous-worker-rating feature exists in the current 17-column input. Do not generate `ankstesnis_lygis` or an equivalent extra column. If introduced later, it must be the last retained pre-emptying worker rating strictly before today, never yesterday\'s latent truth.')
    text = text.replace('`rajonas`', '`sub_district`').replace('`aiksteles_id`', '`site_id`')
    text = text.replace('Missing or ambiguous district values require an explicit validation error, not silent address inference.',
        'Use the reviewed alias table in the generator, including seniūnija suffixes and the explicit Pašilačiai -> Pašilaičiai spelling alias. Broad values `Vilniaus` and `Vilniaus m. sav.` are unresolved. Missing, ambiguous or contradictory canonical district values trigger the approved NULL-and-audit exclusion, not address inference.')
    text = text.replace('site/type/date', 'site/stream/date')
    text = text.replace('keyed by IDs and dates;', 'keyed by IDs and the complete ordered date range; whole-bin processing order does not change results, while a different date range is a distinct configuration;')
    text = text.replace('Changing QR draws must not change waste or worker labels.', 'Changing QR draws must not change waste or worker labels. Use separate uniform draws for inverse-CDF Poisson sampling so paired sensitivity scenarios retain identical underlying randomness. Do not reseed by CSV chunk position.')
    return text


def adapt(source: str) -> str:
    text = source if 'Version 3.0 |' in source else adapt_schema(source)
    if 'Version 3.0 |' not in text:
        raise ValueError('Expected supplied v2.1 or adapted v3.0 rules')
    text = text.replace('Version 3.0 | 10 October 2026 | Adapted to the existing three-year bin-day export',
                        'Version 4.0 | 10 October 2026 | User-approved bounded fullness and bell-shaped assessment scenario')
    text = text.replace('Exactly 100% remains class 3. Never clip to 100. Values above 100 describe capacity-equivalent uncollected waste assigned to a bin, including overflow, not a physically measurable internal volume beyond capacity.',
        'Exactly 100% remains class 3. Never clip to 100: class 4 is retained. Version 4 bounds calibrated scenario fullness to 120%, including a modest overflow band; it does not claim physical internal storage above capacity. Uncapped assigned demand is retained separately in m³ for audit and is no longer presented as physical fullness.')
    text = text.replace(r"L^-_{i,d}=L_{i,d-1}+A_{i,d},\qquad F_{i,d}=100\,\frac{L^-_{i,d}}{V_{i,d}}",
                        r"L^-_{i,d}=L_{i,d-1}+A_{i,d}")
    marker = '### Worker error and visit masking'
    insertion = r'''### User-approved bounded fullness calibration

**[USER-APPROVED SCENARIO CHANGE]** Worker classes should have an approximate bell-shaped frequency with a peak at class 2: target shares are 0.10, 0.20, 0.40, 0.20, 0.10 for classes 0 through 4. This is an ordinal histogram assumption, not a claim that five integer codes or daily percentages follow a continuous normal distribution. Apply it to retained worker assessments, not separately to every bin, waste stream or all non-visit days. Genuine zero exposure remains zero; exact shares are not forced.

The preceding recurrence now tracks **assigned source demand in m³**, not physical occupied volume. Its source inflow, allocation and conservation equations are unchanged. Calibrated fullness is a separate nonlinear response. This replaces only the old identity F=100 L/V and prohibition on distribution calibration. Conserving source demand does not imply physical conservation of the transformed occupancy; source population/capacity mismatches remain visible in demand-volume diagnostics.

Let s be the latest successful service strictly before d; its unchanged sampled residue as a percentage is r=100 epsilon_s. Define dimensionless new-demand pressure X, excluding that residue:

$$
X_{i,d}=\frac{100}{V_{i,d}}\left(L^-_{i,d}-\frac{r_{i,d}V_{i,d}}{100}\right)
$$

$$
F_{i,d}=r_{i,d}+(120-r_{i,d})h(X_{i,d})
$$

The fixed response h is nondecreasing, starts at h(0)=0 and lies in [0,1]. Therefore F stays in [0,120], rises between successes and preserves the 0-3% post-service residue. Do not independently redraw fullness each day or relabel finished rows to meet quotas.

Fit h once using baseline new-demand pressures at known-state successful visits in the first synthetic year: 2023-10-10 through 2024-10-09 for this dataset. Freeze the result for the remaining dates and all paired sensitivity runs. No future collection date enters a row's state transition. The fit window uses synthetic visit sampling and is not independent evaluation; downstream modeling should reserve later dates for validation/test.

Let M be the existing worker-noise transition matrix, with 0.90 on the diagonal and total 0.10 over adjacent classes. Solve M-transpose times latent shares equals the target worker shares. Use the four cumulative latent shares as empirical pressure-quantile probabilities. Their four strictly increasing positive quantiles are x1 through x4. If genuine zero-demand mass exceeds the requested first latent share, preserve that mass, add a 0.005 quantile margin and proportionally rescale other shares; report the resulting feasible expectation. Reject insufficient data or tied/non-positive knots explicitly.

Interpolate linearly through pressure knots (0,x1,x2,x3,x4), with response values (0,(20-1.5)/118.5,(50-1.5)/118.5,(80-1.5)/118.5,(100-1.5)/118.5). The 1.5 is the existing uniform residue's mean, not a new residual distribution. Residue variation and visit mix make resulting shares approximate.

Above x4, use continuous exponential saturation with scale b=x4-x3 and last response y4:

$$
h(x)=y_4+(1-y_4)\left(1-\exp\left(-\frac{x-x_4}{b}\right)\right)
$$

Retain uncapped assigned demand L and excess source demand max(L-V,0) in m³ in diagnostic arrays. They describe source pressure, not measured external litter. Do not add columns to the training CSV. Save fit dates, zero mass, knots, desired/feasible shares, seed and source hashes; supplying a reused calibration requires matching provenance. Do not refit on later validation/test dates or separately within a sensitivity case.

'''
    text = text.replace(marker,insertion+marker)
    text = text.replace('calculate Q and allocate A, then calculate pre-service load F.',
                        'calculate Q and allocate A, update source demand L, then calculate bounded pre-service fullness F using the frozen response.')
    text = text.replace('- No artificial class balancing, no forced 80-100% at collection, and no rate estimated from a future collection date.',
        '- The user-approved global calibration targets approximate worker shares 10/20/40/20/10. No per-bin quotas, no forced 80-100% at collection, and no rate estimated from a future collection date. Report calibration-year and later-year shares separately.\n- Known fullness is finite and within 0-120%; the response is monotone and zero new demand preserves residue. Source-demand conservation and uncapped m³ diagnostics remain independent checks. Freeze the calibration in every sensitivity scenario.')
    return text


def pdf_from_markdown(path: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from matplotlib.font_manager import findfont
    regular = 'C:/Windows/Fonts/arial.ttf'
    bold = 'C:/Windows/Fonts/arialbd.ttf'
    pdfmetrics.registerFont(TTFont('Arial', regular if Path(regular).exists() else findfont('DejaVu Sans')))
    pdfmetrics.registerFont(TTFont('ArialBold', bold if Path(bold).exists() else findfont('DejaVu Sans:bold')))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'Arial'
        style.fontSize = 9
        style.leading = 13
    for name in ('Title', 'Heading1', 'Heading2', 'Heading3'):
        styles[name].fontName = 'ArialBold'
        styles[name].keepWithNext = True
    styles['Title'].fontSize = 18
    styles['Title'].leading = 23
    styles['Heading1'].fontSize = 14
    styles['Heading1'].leading = 18
    styles['Heading2'].fontSize = 11
    styles['Heading2'].leading = 15
    def para(s, style='BodyText'):
        # Long display equations are rendered; inline notation uses readable text.
        def inline(match):
            value = match.group(1)
            for old, new in [(r'\leq', '≤'), (r'\geq', '≥'), (r'\mathrm{', ''), (r'\tau', 'τ'), (r'\rho', 'ρ'), (r'\delta', 'δ'), (r'\widetilde k', 'k̃'), (r'\widehat M', 'M̂'), (r'\varepsilon', 'ε'), (r'\lambda', 'λ')]:
                value = value.replace(old, new)
            return value.replace('{', '').replace('}', '').replace('\\', '').replace('^', '').replace('~', '')
        s = re.sub(r'\$([^$]+)\$', inline, s)
        s = escape(s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'`(.+?)`', r'<font color="#185975">\1</font>', s)
        return Paragraph(s, styles[style])
    story = []
    lines = path.read_text(encoding='utf-8').splitlines()
    temp = path.parent / 'pdf_preview'
    temp.mkdir(exist_ok=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line == '$$':
            equation = []
            i += 1
            while lines[i] != '$$':
                equation.append(lines[i])
                i += 1
            eq = ''.join(equation).replace(r'\Pr', r'\mathrm{Pr}').replace(r'\text', r'\mathrm')
            fig = plt.figure(figsize=(10, .65))
            fig.text(.01, .5, '$' + eq + '$', fontsize=14, va='center')
            image = temp / f'equation_{i}.png'
            fig.savefig(image, dpi=180, bbox_inches='tight', pad_inches=.06)
            plt.close(fig)
            from PIL import Image as PILImage
            with PILImage.open(image) as im:
                width, height = im.size
            scale = min(470 / width, .43)
            story += [Image(str(image), width=width*scale, height=height*scale), Spacer(1, 8)]
        elif line.startswith('|'):
            table = []
            while i < len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[-| :]+\|$', lines[i]):
                    table.append([para(c.strip()) for c in lines[i].strip('|').split('|')])
                i += 1
            cols = len(table[0])
            widths = [180, 70, 220] if cols == 3 else [235, 235]
            t = Table(table, colWidths=widths, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4edf3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#8495a5')),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5)]))
            story += [t, Spacer(1, 10)]
            continue
        elif line.startswith('# '):
            story += [para(line[2:], 'Title')]
        elif line.startswith('## '):
            story += [para(line[3:], 'Heading1')]
        elif line.startswith('### '):
            story += [para(line[4:], 'Heading2')]
        else:
            story += [para(line), Spacer(1, 5)]
        i += 1
    def page(canvas, doc):
        canvas.setFont('Arial', 8)
        canvas.setFillColor(colors.HexColor('#5c6b78'))
        canvas.drawString(42, 24, 'Vilnius synthetic bin-day rules | v4.0 | 10 October 2026')
        canvas.drawRightString(553, 24, str(doc.page))
    SimpleDocTemplate(str(path.with_suffix('.pdf')), rightMargin=42, leftMargin=42, topMargin=40, bottomMargin=42).build(story, onFirstPage=page, onLaterPages=page)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('backend/data/rules'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = args.source.read_text(encoding='utf-8')
    updated = adapt(source)
    change_log = (Path(__file__).resolve().parents[1] /
                  'openspec/changes/archive/2026-10-11-calibrate-fill-generation/fill-qr-rule-changes.md')
    shutil.copy2(change_log, args.output_dir / 'CHANGELOG.md')
    import csv
    from fill_qr import ALIASES
    with (args.output_dir / 'district_aliases.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['input', 'canonical'])
        writer.writerows(sorted(ALIASES.items()))
    path = args.output_dir / 'vilnius_two_column_generation_rules_v4.md'
    path.write_text(updated, encoding='utf-8')
    baseline = source if 'Version 3.0 |' in source else adapt_schema(source)
    diff = ''.join(difflib.unified_diff(baseline.splitlines(True), updated.splitlines(True), fromfile='prior adapted rules v3.0', tofile=path.name))
    (args.output_dir / 'rules_changes.diff').write_text(diff, encoding='utf-8')
    from fill_qr import digest,write_json
    def section(value,start,end):return value.split(start,1)[1].split(end,1)[0]
    invariant_sections = [
        ('population_rates_and_categories','## 2. Population','## 3. Daily accumulation'),
        ('inflow_distributions_calendar_allocation','### Persistent heterogeneity','### State transition'),
        ('worker_noise_masks_and_qr','### Worker error and visit masking','## 5. Districts'),
        ('district_rules','## 5. Districts','## 6. Implementation'),
        ('sources','## 7. Sources','UNUSED_END_MARKER')]
    review={name:section(baseline,start,end)==section(updated,start,end) for name,start,end in invariant_sections}
    assert all(review.values()),review
    write_json(args.output_dir/'rules_review.json',{'source_sha256':digest(args.source),'updated_sha256':digest(path),'unchanged_sections':review,'only_changes':'version metadata, bounded fullness mapping/calibration, associated daily-order wording and checks'})
    pdf_from_markdown(path)
    print(path)


if __name__ == '__main__':
    main()
