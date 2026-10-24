from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd


@dataclass
class Pack:
    stations: pd.DataFrame
    weather: dict[str, pd.DataFrame]
    gps_lines: dict[str, list[str]]
    maintenance_text: str
    input_hashes: dict[str, str]
    diagnostics: list[dict] = field(default_factory=list)


@dataclass
class Candidate:
    station_id: str
    channel: str
    issue: str
    subtype: str
    start: datetime | None
    end: datetime | None
    row_refs: tuple[str, ...] = ()
    evidence: dict = field(default_factory=dict)


@dataclass
class Flag:
    station_id: str
    channel: str
    start_utc: str
    end_utc: str
    issue: str
    action: str
    note: str


@dataclass
class RunResult:
    flags: list[Flag]
    reviews: list[dict]
    evidence: dict
    summary: dict
