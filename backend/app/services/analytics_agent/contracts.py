from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from time import monotonic
from typing import Annotated, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class ToolQueryError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Bbox(Closed):
    min_latitude: float = Field(strict=True, ge=-90, le=90)
    min_longitude: float = Field(strict=True, ge=-180, le=180)
    max_latitude: float = Field(strict=True, ge=-90, le=90)
    max_longitude: float = Field(strict=True, ge=-180, le=180)

    @model_validator(mode='after')
    def positive_spans(self):
        if self.min_latitude >= self.max_latitude or self.min_longitude >= self.max_longitude:
            raise ValueError('Bounds must have positive geographic spans')
        return self


ID = Annotated[int, Field(strict=True, ge=1, le=9223372036854775807)]
Group = Literal['none', 'waste_type', 'waste_carrier', 'object_group', 'site_id']


class Period(Closed):
    mode: Literal['recent', 'explicit', 'all_history']
    start: date | None
    end: date | None

    @model_validator(mode='after')
    def consistent(self):
        if self.mode == 'explicit':
            if self.start is None or self.end is None or self.start >= self.end:
                raise ValueError('Explicit periods require start < end (exclusive end)')
        elif self.start is not None or self.end is not None:
            raise ValueError('Only explicit periods accept dates')
        return self


class Empty(Closed):
    pass


class Page(Closed):
    limit: int | None = Field(default=None, strict=True, ge=1, le=100, description='NULL uses 50; maximum 100.')
    offset: int | None = Field(default=None, strict=True, ge=0, le=10000000, description='NULL uses zero; deterministic pagination.')


class BinId(Closed):
    bin_id: ID


class BinIds(Closed):
    bin_ids: list[ID] = Field(min_length=1, max_length=100)


class SiteId(Closed):
    site_id: ID


class Summary(Page):
    scope: Literal['area', 'global'] | None = None
    grouping: Group | None = None


class Activity(Summary):
    period: Period | None = None
    bin_id: ID | None = None


class History(Page, BinId):
    period: Period | None = None


class Events(Page):
    period: Period | None = None


class Schedule(Events):
    bin_id: ID | None = None
    scope: Literal['area', 'global'] | None = None


class RequestTrend(Events):
    scope: Literal['area', 'global'] | None = None
    interval: Literal['day', 'week', 'month'] | None = None


class Compare(Summary):
    period: Period | None = None


class Trend(RequestTrend):
    interval: Literal['day', 'week', 'month'] | None = None
    metric: Literal['service', 'failure', 'fill'] | None = None


class BinList(Page):
    waste_type: str | None = Field(default=None, max_length=200)
    waste_carrier: str | None = Field(default=None, max_length=200)
    object_group: str | None = Field(default=None, max_length=200)
    sort: Literal['id', 'largest_capacity', 'missing_history', 'recently_serviced', 'not_serviced_since'] | None = None
    cutoff: date | None = None

    @model_validator(mode='after')
    def cutoff_needed(self):
        if (self.sort == 'not_serviced_since') != (self.cutoff is not None):
            raise ValueError('Only not_serviced_since requires a cutoff')
        return self


class Sites(Page):
    site_id: ID | None = None
    grouping: Group | None = None
    sort: Literal['id', 'count', 'capacity'] | None = None


class SiteActivity(Events):
    site_id: ID | None = None


class Ranking(Events):
    rank: Literal['high_requests_low_successes', 'high_failures'] | None = None


class Geography(Page):
    kind: Literal['district', 'service_zone']


class GeographicSummary(Geography):
    geographic_id: ID
    period: Period | None = None


class Population(Page):
    grouping: Literal['polygon', 'density_band', 'waste_type'] | None = None


class Synthetic(Events):
    grouping: Literal['none', 'waste_type', 'collection_status'] | None = None


class SyntheticTrend(Events):
    interval: Literal['day', 'week', 'month'] | None = None


class PlanSummary(Events):
    grouping: Literal['none', 'waste_carrier'] | None = None


class FacilityId(Closed):
    facility_id: ID


class Proximity(Closed):
    latitude: float | None = Field(default=None, strict=True, ge=-90, le=90)
    longitude: float | None = Field(default=None, strict=True, ge=-180, le=180)
    limit: int | None = Field(default=None, strict=True, ge=1, le=10)

    @model_validator(mode='after')
    def pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Provide both coordinates or neither')
        return self


class Fleet(Closed):
    waste_carrier: str | None = Field(default=None, max_length=200)


class EffectivePeriod(Closed):
    start: str | None
    end: str
    date_end_exclusive: str
    timezone: str = 'Europe/Vilnius'
    partial_today: bool
    timestamp_semantics: str = 'Stored naive timestamps are local wall-clock values; no UTC conversion.'


class Result(Closed):
    status: Literal['ok', 'error']
    code: str | None = None
    message: str | None = None
    scope: str
    period: EffectivePeriod | None = None
    evidence_type: str
    queried_at: str
    read_only: bool = True
    data: dict[str, JsonValue] = Field(default_factory=dict)
    units: dict[str, str] = Field(default_factory=lambda: {'capacity': 'source capacity, assumed m³ (unverified)', 'observed_fill': 'ordinal category 0–3', 'predicted_fill': 'model-predicted category 0–4 (synthetic history)'})
    limitations: list[str] = Field(default_factory=lambda: [
        'Current bin registry coordinates/categories/carrier qualify event aggregation; servicing carrier is not observed.',
        'Separate short snapshots may see changes between tool calls.',
        'Missing evidence does not establish overdue or missed service; submissions are not unique residents.',
    ])


class AnalyzeRequest(Closed):
    bbox: Bbox


class AnalysisResponse(Closed):
    status: Literal['complete', 'incomplete']
    bbox: Bbox
    default_period: EffectivePeriod
    answer: str | None
    incomplete_reason: Literal['deadline', 'model_response_incomplete', 'no_final_answer', 'refused'] | None
    model_requests: int = Field(ge=0, le=5)
    elapsed_seconds: float = Field(ge=0)


@dataclass
class RunContext:
    bbox: Bbox
    started_at: datetime = field(default_factory=lambda: datetime.now(ZoneInfo('Europe/Vilnius')))
    started: float = field(default_factory=monotonic)
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    selection_ids: list[int] | None = None
    tool_calls: int = 0
    result_bytes: int = 0

    def remaining(self, exploration=False):
        return max(0.0, self.started + (45 if exploration else 60) - monotonic())

    def period(self, period=None, future=False):
        today = self.started_at.date()
        local_now = self.started_at.replace(tzinfo=None)
        if period is None or period.mode == 'recent':
            start = datetime.combine(today - timedelta(days=29), time.min)
            end = local_now
            date_end = today + timedelta(days=1)
        elif period.mode == 'all_history':
            start, end, date_end = None, local_now, today + timedelta(days=1)
        else:
            if not future and (period.start > today or period.end > today + timedelta(days=1)):
                raise ValueError('Future dates are only supported for stored schedules/plans')
            start = datetime.combine(period.start, time.min)
            date_end = period.end
            end = datetime.combine(date_end, time.min)
            if not future: end = min(end, local_now)
        return EffectivePeriod(start=start.isoformat() if start else None, end=end.isoformat(), date_end_exclusive=date_end.isoformat(), partial_today=date_end > today and (start is None or start.date() <= today))
