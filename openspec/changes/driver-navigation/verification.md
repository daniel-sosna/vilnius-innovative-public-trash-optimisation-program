# Manual verification

Backend checks were run by the implementer; the browser steps below are for the developer (phone viewport, e.g. 390 x 844). Record the result next to each step.

## Prerequisites

1. `docker compose up`, then apply migrations (`alembic upgrade head` runs at startup; revision 0019).
2. Build the plans (see `docs/driver.md`): collection plan 2026-09-15, demo fleet, route plan Ecoservice 2026-09-16.
3. `docker compose exec backend uv run python -m app.interfaces.driver.check --truck-id 1` exits 0.

## Backend (done)

| Check | Result |
|---|---|
| Migration 0019 up/down; level 4 accepted, 5 rejected, downgrade refuses with a level-4 row | passed |
| `POST /driver/route` truck 1: 9 stops (bins per stop 3,2,1,1,1,1,6,1,1), 1266-point path | passed |
| Unknown truck 99999: 404 `truck_not_found`; truck 103 (Ekonovus): 404 `no_plan`; `422` for truck_id 0 | passed |
| Forced invalid navigation result: 502 `navigation_failed` | passed |
| Collection plan removed (rolled back): empty stops and path | passed |
| `POST /driver/service` 3 bins (0, 2, 4): 201, server Vilnius time; client `date` rejected 422 | passed |
| Level 5, -1, `"3"`, duplicate bin, empty list: 422; unknown bin: 404 with nothing stored | passed |
| `check --truck-id 99999` and `103`: exit 1 | passed |

## Browser (to do)

| Step | Expected | Result |
|---|---|---|
| Open `/`, press `Vairuotojas` | Truck picker, no admin navbar | |
| Open `/driver/99999` | `Šiukšliavežė nerasta.` and no start button | |
| Open `/driver/103` and press `Pradėti maršrutą` | `Šiai dienai paruošto maršruto duomenų nėra.` | |
| Open `/driver/1` and press `Pradėti maršrutą` | `Ruošiamas maršrutas...`, then the navigation map | |
| Watch the truck | Moves along every road vertex, never cuts corners; marker faces the driving direction | |
| Watch the camera | Truck stays lower-middle, map rotates smoothly with the heading, no jitter at bends | |
| Pan the map | Following stops; the recenter button appears; pressing it resumes following | |
| Top panel | `Kitas konteineris`, address, inventory number and waste type of the stop's bins; `0 / 17 konteinerių` style progress | |
| Map stops | Next orange and larger, future white, serviced green; passed line grey | |
| Truck reaches stop 1 (3 bins) | Truck stops exactly at the stop; first bin view `1 / 3` | |
| Choose a level | Moves to bin `2 / 3` at once; no back on the first bin | |
| Back from bin 2 | Bin 1 shows its choice highlighted; choosing another replaces it | |
| Choose the last bin | `Visi konteineriai pažymėti` lists each bin with its label; nothing stored yet (check `bin_hist`) | |
| Level `Tuščias` (0) and `Perpildytas` (4) | Both save; rows in `bin_hist` with `was_serviced` true | |
| Stop the backend, press `Patvirtinti` | Toast `Nepavyko išsaugoti duomenų. Bandykite dar kartą.`; view and choices kept; progress unchanged | |
| Restart the backend, press `Patvirtinti` again | Saved once; truck resumes to stop 2; progress increases by the stop's bin count | |
| Double-tap `Patvirtinti` | One request, each bin stored once | |
| Last stop saved | `Maršrutas baigtas`, `Aptarnauta: N konteinerių`; truck does not move | |
| Layout | No horizontal scroll at 390 px; controls at least 48 px | |

## Cleanup

Rows created by browser testing can be removed with `delete from bin_hist where date > <test start> and was_serviced and fill_level is not null`.
