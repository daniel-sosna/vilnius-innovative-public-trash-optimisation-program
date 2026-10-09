"""Seed the supplied landfill catalog and add explicit Truck assignment.

Revision ID: 0006
Revises: 0005
Source: vilnius_waste_facilities.geojson
SHA256: 1e588cb980c105d287497f202fc4e342d9fee3940d2e37fda7a586d68185e42b

Source descriptions are retained data, not independently verified route facts.
"""

import json
from datetime import date

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Self-contained snapshot: migration never reads Downloads or requests URLs.
SEED_ROWS = json.loads(r"""
[
  {
    "source_id": "ecoservice-gariunu-71",
    "dataset_name": "vilnius_waste_facilities",
    "dataset_description": "Publicly documented waste reception and treatment locations relevant to Vilnius. These are facility points, not truck depots or confirmed route assignments. Coordinates may represent an address point rather than a facility entrance.",
    "latitude": 54.6567,
    "longitude": 25.1563,
    "name": "Ecoservice Gariūnų waste reception and sorting site",
    "operator": "UAB Ecoservice",
    "address": "Gariūnų g. 71, Vilnius, Lithuania",
    "facility_role": "waste_reception_and_sorting",
    "waste_streams": [
      "sorted bulky and other accepted wastes",
      "mixed municipal waste sorting reported from 2026-08-31"
    ],
    "status": "publicly_listed_receiving_site; municipal mixed-waste arrangement should be rechecked before operational use",
    "coordinate_quality": "approximate address coordinate",
    "coordinate_source": "https://www.adresoistorija.com/LT/gari%C5%ABn%C5%B3-g-71-vilnius-02300-lithuania",
    "facility_source": "https://ecoservice.lt/paslaugos/atlieku-aikstele/",
    "municipal_arrangement_source": "https://www.lrt.lt/naujienos/verslas/4/3033327/vilnius-atliekos-nebus-vezamos-i-ekonovus-aikstele-jas-tvarkys-ecoservice-ecobaze",
    "verified_at": "2026-10-10"
  },
  {
    "source_id": "ekobaze-lentvario-13a",
    "dataset_name": "vilnius_waste_facilities",
    "dataset_description": "Publicly documented waste reception and treatment locations relevant to Vilnius. These are facility points, not truck depots or confirmed route assignments. Coordinates may represent an address point rather than a facility entrance.",
    "latitude": 54.652436,
    "longitude": 25.135007,
    "name": "Ekobazė Lentvario waste treatment site",
    "operator": "UAB Ekobazė",
    "address": "Lentvario g. 13A, Vilnius, Lithuania",
    "facility_role": "waste_reception_and_recycling",
    "waste_streams": [
      "construction waste",
      "industrial waste",
      "other accepted wastes",
      "mixed municipal waste sorting reported from 2026-08-31"
    ],
    "status": "publicly_listed_operating_site; municipal mixed-waste arrangement should be rechecked before operational use",
    "coordinate_quality": "published coordinates",
    "coordinate_source": "https://www.ekobaze.eu/kontaktai-vilnius-lentvario-g/",
    "facility_source": "https://www.ekobaze.eu/kontaktai-vilnius-lentvario-g/",
    "municipal_arrangement_source": "https://www.lrt.lt/naujienos/verslas/4/3033327/vilnius-atliekos-nebus-vezamos-i-ekonovus-aikstele-jas-tvarkys-ecoservice-ecobaze",
    "verified_at": "2026-10-10"
  },
  {
    "source_id": "vaatc-mba-jocioniu-13",
    "dataset_name": "vilnius_waste_facilities",
    "dataset_description": "Publicly documented waste reception and treatment locations relevant to Vilnius. These are facility points, not truck depots or confirmed route assignments. Coordinates may represent an address point rather than a facility entrance.",
    "latitude": 54.6669658,
    "longitude": 25.1583394,
    "name": "Vilnius regional mechanical-biological treatment facility (MBA)",
    "operator": "VAATC facility; current operating arrangements require confirmation",
    "address": "Jočionių g. 13, Vilnius, Lithuania",
    "facility_role": "mechanical_biological_treatment",
    "waste_streams": [
      "mixed municipal waste processing"
    ],
    "status": "facility address confirmed; do not assume normal full-capacity intake",
    "coordinate_quality": "approximate address coordinate; facility occupies a larger industrial parcel",
    "coordinate_source": "https://vilnius21.lt/jocioniu13-n24664.html",
    "facility_source": "https://energesman.lt/apie-mus/",
    "current_status_source": "https://www.lrt.lt/naujienos/verslas/4/3034261/vilniuje-ekobazes-teritorijoje-gaisras-galejo-kilti-del-licio-baterijos-jis-uzgesintas",
    "verified_at": "2026-10-10"
  }
]
""")


def upgrade() -> None:
    table = op.create_table(
        "landfills",
        sa.Column(
            "id", sa.Integer(), sa.Identity(always=True, start=1), primary_key=True
        ),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("dataset_name", sa.Text(), nullable=False),
        sa.Column("dataset_description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("operator", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("facility_role", sa.Text(), nullable=False),
        sa.Column("waste_streams", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("coordinate_quality", sa.Text(), nullable=False),
        sa.Column("coordinate_source", sa.Text(), nullable=False),
        sa.Column("facility_source", sa.Text(), nullable=False),
        sa.Column("municipal_arrangement_source", sa.Text(), nullable=True),
        sa.Column("current_status_source", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.Date(), nullable=False),
        sa.UniqueConstraint("source_id", name="uq_landfills_source_id"),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90", name="ck_landfills_latitude_range"
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_landfills_longitude_range"
        ),
    )
    rows = [
        {
            **row,
            "verified_at": date.fromisoformat(row["verified_at"]),
            "municipal_arrangement_source": row.get("municipal_arrangement_source"),
            "current_status_source": row.get("current_status_source"),
        }
        for row in SEED_ROWS
    ]
    # Individual ordered inserts generate 1, 2, 3 without overriding identity.
    op.bulk_insert(table, rows, multiinsert=False)
    op.add_column("trucks", sa.Column("landfill_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_trucks_landfill_id",
        "trucks",
        "landfills",
        ["landfill_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE trucks IN ACCESS EXCLUSIVE MODE"))
    ids = connection.scalars(
        sa.text("SELECT id FROM trucks WHERE landfill_id IS NOT NULL ORDER BY id")
    ).all()
    if ids:
        raise RuntimeError(
            "Landfill downgrade would discard assignments, including retired trucks; "
            f"found Truck IDs: {', '.join(map(str, ids))}. "
            "Records and schema have not been changed. Resolve assignments deliberately "
            "before retrying."
        )
    op.drop_constraint("fk_trucks_landfill_id", "trucks", type_="foreignkey")
    op.drop_column("trucks", "landfill_id")
    op.drop_table("landfills")
