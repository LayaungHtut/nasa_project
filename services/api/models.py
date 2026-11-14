"""Pydantic schemas mirroring docs/api/api-contract.md.

Keep this file and the contract doc in sync -- if you change a field here,
update the doc (and vice versa). The frontend is built against the doc,
not against this file directly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Provenance(BaseModel):
    mission: Literal["NISAR"]
    product: Literal["GCOV", "GUNW"]
    granule_id: str
    daac: Literal["ASF"]
    acquisition_date: str


class Location(BaseModel):
    name: str
    bbox: list[float]
    center: list[float]


class ObservationDates(BaseModel):
    baseline: str
    post_event: str


class Processing(BaseModel):
    method: str
    version: str
    threshold_db: float
    min_cluster_pixels: int
    speckle_filter_size: int | None = None  # e.g. 3 for a 3x3 Lee filter -- see real-data-validation.md for why this may differ from the methodology default
    limitations: list[str]


class Results(BaseModel):
    change_area_km2: float
    confidence: float  # kept for API/frontend compatibility
    confidence_type: str | None = None  # "heuristic_detection_score" -- NOT a statistical probability, see docs/science/real-data-validation.md
    changed_pixels: int
    valid_fraction: float


class Tiles(BaseModel):
    preview_url: str  # 3-panel strip, kept for backward compatibility
    baseline_preview_url: str | None = None
    post_event_preview_url: str | None = None
    change_preview_url: str | None = None
    corner_coordinates: list[list[float]]


class ChangeEvent(BaseModel):
    id: str
    title: str
    phenomenon: Literal["flood_extent_change", "surface_deformation"]
    data_status: Literal["REAL", "SYNTHETIC_PLACEHOLDER"]
    location: Location
    observation_dates: ObservationDates
    source_products: list[Provenance]
    processing: Processing
    results: Results
    tiles: Tiles
    change_geometry_url: str
    statistics_url: str | None = None  # full audit-trail JSON: raw pixel counts, AOI area, filter/threshold used -- see real-data-validation.md
    ai_explanation: str | None = None
    generated_at: str


class ExplainResponse(BaseModel):
    ai_explanation: str
    generated_at: str
    cached: bool


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: dict = {}
