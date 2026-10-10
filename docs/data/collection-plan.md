# Collection plan

For one date, the plan lists the sites each waste carrier must serve, so that routing starts from one consistent input. Behaviour is specified in [`collection-plan`](../../openspec/specs/collection-plan/spec.md).

```bash
docker compose exec backend uv run python -m app.interfaces.collection_plan [--date YYYY-MM-DD] [--threshold N]
```

| Option | Default |
|---|---|
| `--date` | Today, in the container's local date. Only this date's plan is replaced, in one transaction. |
| `--threshold` | 2 (integer 0..4). A bin is due when its predicted fill level is **strictly greater**, so levels 3 and 4 by default. |

The command prints counts and exits 0. It exits 1 on invalid arguments, on a database failure, or when no bins are stored.

## Tables

- `collection_stops` has one row per date, carrier and site that has at least one due bin. A site served by two carriers gives two stops. Bins without a carrier form **unassigned** stops, with carrier `NULL`.
- `stop_bins` holds every bin of that carrier at the site, because the truck empties them all. `due` marks the bins above the threshold.
- `overall_volume_m3` is the sum of capacities. `overall_predicted_fill_m3` is the sum of each capacity times its fill share. Both cover all the stop's bins and are only recalculated on the next rebuild. A missing capacity counts as 0 and is reported in the summary.

## Assumptions

- **Mock prediction.** Fill levels (0 empty .. 4 full) come from `predict_fill_levels` in [`backend/app/ml/fill_prediction.py`](../../backend/app/ml/fill_prediction.py). They are synthetic: uniform per bin and seeded from the date, so a given date always gives the same plan. They are neither observed data nor a model. A real model replaces only that function, keeping the same `{bin_id: level}` contract.
- **Fill shares.** Each level stands for a share of capacity: 0 = 20%, 1 = 50%, 2 = 80%, 3 = 100%, 4 = 150%. Above 100% means over-full. For example, 0.6 m³ at level 2 gives 0.48 m³.

## Reading the plan for routing

```python
from app.services.collection_plan import get_plan
get_plan(session, date, carriers=None)  # {carrier: [stop, ...]}, None = unassigned
```

- With `carriers` given (use `None` in the list for unassigned stops), every requested group is present, even when it has no stops.
- A stop is a dict with `stop_id`, `site_id`, `address`, `latitude`, `longitude`, `overall_volume_m3`, `overall_predicted_fill_m3` and `bins`. Each bin has `bin_id`, `waste_type`, `capacity_m3`, `predicted_fill` and `due`.

Deleting a bin or site removes it from the plan. An [import](import.md) of `bins` empties the plan.
