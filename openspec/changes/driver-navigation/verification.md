# Manual verification

Backend checks were run by the implementer; the browser steps below are for the developer (phone viewport, e.g. 390 x 844). Record the result next to each step.

## Prerequisites

1. `docker compose up`; migrations run at startup (head 0020).
2. Select a project date in the admin calendar, run the route calculation on `/admin/routes`, and wait for the truck table (see `docs/driver.md`).

## Backend (done)

| Check | Result |
|---|---|
| Migration 0020 (after 0019) up/down; level 4 accepted, 5 rejected, downgrade refuses with a level-4 row | passed |
| Route from a cached run (synthetic run for 2026-09-15, truck 1, two service stops, landfill return): 200; stops list all carrier bins at the site (3 at site 13589 for 1 due bin); `path_index` at the end of each service leg | passed |
| `GET /driver/trucks`: routed truck listed for 2026-09-14, empty for 2026-09-13, `422` for 2026-10-14 | passed |
| Other day / truck without route: 404 `no_plan`; unknown truck: 404 `truck_not_found`; missing date: 422 | passed |
| `POST /driver/service` 3 bins (0, 2, 4): 201, server Vilnius time; client `date` rejected 422 | passed |
| Level 5, -1, `"3"`, duplicate bin, empty list: 422; unknown bin: 404 with nothing stored | passed |

A real calculation run (prediction, PyVRP, OSRM) was not run by the implementer.

## Browser (to do)

| Step | Expected | Result |
|---|---|---|
| Open `/`, press `Vairuotojas` | Truck picker, no admin navbar | |
| Open `/driver/99999` | `Šiukšliavežė nerasta.` and no start button | |
| Open `/driver` before any calculation of the selected day | `Šiai dienai paruošto maršruto duomenų nėra.` | |
| Open `/driver` after the calculation | Lists the routed trucks; forecast day shown | |
| Change the date in the admin calendar, reload `/driver` | The list follows the new day | |
| Open a listed truck and press `Pradėti maršrutą` | `Ruošiamas maršrutas...`, then the navigation map starting at the truck's landfill | |
| Watch the truck | Moves along every road vertex, never cuts corners; marker faces the driving direction | |
| Watch the camera | Truck stays lower-middle, map rotates smoothly with the heading, no jitter at bends | |
| Pan the map | Following stops; the recenter button appears; pressing it resumes following | |
| Top panel | `Kitas konteineris`, address, inventory number and waste type of the stop's bins; `0 / 17 konteinerių` style progress | |
| Map stops | Next orange and larger, future white, serviced green; passed line grey | |
| Truck reaches stop 1 | Truck stops exactly at the stop; first bin view `1 / N` for all carrier bins of the site | |
| Multi-trip truck | Truck drives back to the landfill between trips without stopping | |
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
