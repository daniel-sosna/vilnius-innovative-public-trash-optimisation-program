# Collection plan

For one date, the plan lists the sites each waste carrier must serve, so that routing starts from one consistent input. Behaviour is specified in [`collection-plan`](../../openspec/specs/collection-plan/spec.md).

```bash
docker compose exec backend uv run python -m app.interfaces.collection_plan --date YYYY-MM-DD [--threshold N]
```

| Option | Default |
|---|---|
| `--date` | Required. "Today" T, from 2026-09-01 to 2026-09-30; the plan is for T+1 and only T+1 is replaced, in one transaction. Other dates are rejected: only September 2026 is available for simulation. |
| `--threshold` | 2 (integer 0..4). A bin is due when its predicted fill level is **strictly greater**, so levels 3 and 4 by default. |

The command prints counts and exits 0. It exits 1 on invalid arguments, on a database failure, when no bins are stored, or when an input listed below is missing. A run scans the full history CSV and took about 1 minute for all 21,951 bins on the development machine (see [fill prediction](fill-prediction.md#delivery-and-runtime)). It runs the delivered model and does not retrain it; the research dependencies are not needed.

## Inputs

Read from the [data directory](../development.md#data-directory):

| File | Contents |
|---|---|
| `bin_days_*_enriched.csv` | Daily history with synthetic fill labels; exactly one file. A missing file gives "Historical data is not present in the system". |
| `bins_<digits>.csv` | Bin registry; the highest number is used. |
| `bin_population.csv` | Population export. |
| `ml/september-fill-predictor/product/` | Delivered model, as written by `app.ml.run`. |

## Tables

- `collection_stops` has one row per date, carrier and site that has at least one due bin. A site served by two carriers gives two stops. Bins without a carrier form **unassigned** stops, with carrier `NULL`.
- `stop_bins` holds every bin of that carrier at the site, because the truck empties them all. `due` marks the bins above the threshold.
- `overall_volume_m3` is the sum of capacities. `overall_predicted_fill_m3` is the sum of each capacity times its fill share. Both cover all the stop's bins and are only recalculated on the next rebuild. A missing capacity counts as 0 and is reported in the summary.

## Assumptions

- **Model prediction.** Fill levels (0 empty .. 4 full) come from the trained next-day model in `viptop_fill`, called by `predict_fill_levels` in [`backend/app/ml/fill_prediction.py`](../../backend/app/ml/fill_prediction.py). The model learned from synthetic fill assessments, not measured fill, so levels are predictions on simulated data. Bins without a predicted level are left out of the plan; predictions for bins that are not stored are ignored.
- **Fill shares.** Each level stands for a share of capacity: 0 = 20%, 1 = 50%, 2 = 80%, 3 = 100%, 4 = 150%. Above 100% means over-full. For example, 0.6 m³ at level 2 gives 0.48 m³.

## Reading the plan for routing

```python
from app.services.collection_plan import get_plan
get_plan(session, date, carriers=None)  # {carrier: [stop, ...]}, None = unassigned
```

- With `carriers` given (use `None` in the list for unassigned stops), every requested group is present, even when it has no stops.
- A stop is a dict with `stop_id`, `site_id`, `address`, `latitude`, `longitude`, `overall_volume_m3`, `overall_predicted_fill_m3` and `bins`. Each bin has `bin_id`, `waste_type`, `capacity_m3`, `predicted_fill` and `due`.

Deleting a bin or site removes it from the plan. An [import](import.md) of `bins` empties the plan.
