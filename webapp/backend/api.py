from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config_registry import get_asset_config
from services import comparison as comparison_service
from services import carry as carry_service
from services import momentum as momentum_service
from services import value as value_service

router = APIRouter(prefix="/api")


def _parse_pairs(pairs: str | None) -> list[tuple[int, int]] | None:
    """'1:20,5:60,20:250' -> [(1,20),(5,60),(20,250)]."""
    if not pairs:
        return None
    out = []
    for chunk in pairs.split(","):
        f, s = chunk.split(":")
        out.append((int(f), int(s)))
    return out


def _skip_front_contract(asset_class: str, product: str) -> bool:
    return bool(get_asset_config(asset_class)["skip_front_contract"])


# ── Momentum ────────────────────────────────────────────────────────────────

@router.get("/{asset_class}/{product}/momentum")
def momentum(
    asset_class: str, product: str,
    roll_method: str = Query("ltd", pattern="^(ltd|5td)$"),
    roll_n: int = Query(5, ge=1, le=10),
    tc_bps: int = Query(5),
    shift_n: int = Query(1, ge=0, le=2),
    pairs: str | None = Query(None, description="e.g. 1:20,5:60,20:250"),
    metrics_year_start: int | None = None,
    metrics_year_end: int | None = None,
    feature_fast: int | None = None,
    feature_slow: int | None = None,
    equity_year_start: int | None = None,
    equity_year_end: int | None = None,
    focus_fast: int | None = None,
    focus_slow: int | None = None,
    rs_basis: str = Query("net", pattern="^(net|gross)$"),
):
    try:
        return momentum_service.get_momentum(
            asset_class, product,
            roll_method=roll_method, roll_n=roll_n, tc_bps=tc_bps, shift_n=shift_n,
            pairs=_parse_pairs(pairs),
            metrics_year_start=metrics_year_start, metrics_year_end=metrics_year_end,
            feature_pair=(feature_fast, feature_slow) if feature_fast and feature_slow else None,
            equity_year_start=equity_year_start, equity_year_end=equity_year_end,
            focus_pair=(focus_fast, focus_slow) if focus_fast and focus_slow else None,
            rs_basis=rs_basis,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{asset_class}/{product}/momentum/heatmap")
def momentum_heatmap_endpoint(
    asset_class: str, product: str,
    roll_method: str = Query("ltd", pattern="^(ltd|5td)$"),
    roll_n: int = Query(5, ge=1, le=10),
    tc_bps: int = Query(5),
    shift_n: int = Query(1, ge=0, le=2),
    year_start: int | None = None,
    year_end: int | None = None,
    max_window: int = Query(250, ge=10, le=500),
):
    try:
        return momentum_service.get_momentum_heatmap(
            asset_class, product,
            roll_method=roll_method, roll_n=roll_n, tc_bps=tc_bps, shift_n=shift_n,
            year_start=year_start, year_end=year_end, max_window=max_window,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Carry ───────────────────────────────────────────────────────────────────

class CarryVariant(BaseModel):
    type: str  # "V1" | "V2" | "V3"
    near: str | None = None
    far: str | None = None
    window: int | None = None
    horizon: int | None = None


class CarryRequest(BaseModel):
    roll_method: str = "ltd"
    roll_n: int = 5
    tc_bps: int = 5
    shift_n: int = 1
    variants: list[CarryVariant] | None = None
    metrics_year_start: int | None = None
    metrics_year_end: int | None = None
    feature_variant: CarryVariant | None = None
    equity_year_start: int | None = None
    equity_year_end: int | None = None
    focus_variant: CarryVariant | None = None
    rs_basis: str = "net"


@router.post("/{asset_class}/{product}/carry")
def carry(asset_class: str, product: str, body: CarryRequest):
    try:
        return carry_service.get_carry(
            asset_class, product,
            roll_method=body.roll_method, roll_n=body.roll_n, tc_bps=body.tc_bps, shift_n=body.shift_n,
            variants=[v.model_dump(exclude_none=True) for v in body.variants] if body.variants else None,
            skip_front_contract=_skip_front_contract(asset_class, product),
            metrics_year_start=body.metrics_year_start, metrics_year_end=body.metrics_year_end,
            feature_variant=body.feature_variant.model_dump(exclude_none=True) if body.feature_variant else None,
            equity_year_start=body.equity_year_start, equity_year_end=body.equity_year_end,
            focus_variant=body.focus_variant.model_dump(exclude_none=True) if body.focus_variant else None,
            rs_basis=body.rs_basis,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{asset_class}/{product}/carry/heatmap")
def carry_heatmap_endpoint(
    asset_class: str, product: str,
    roll_method: str = Query("ltd", pattern="^(ltd|5td)$"),
    roll_n: int = Query(5, ge=1, le=10),
    tc_bps: int = Query(5),
    shift_n: int = Query(1, ge=0, le=2),
    days: int | None = None,
    mode: str | None = Query(None, pattern="^(Momentum|Zscore)$"),
    year_start: int | None = None,
    year_end: int | None = None,
):
    try:
        return carry_service.get_carry_heatmap(
            asset_class, product,
            roll_method=roll_method, roll_n=roll_n, tc_bps=tc_bps, shift_n=shift_n,
            skip_front_contract=_skip_front_contract(asset_class, product),
            days=days, mode=mode, year_start=year_start, year_end=year_end,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Value ───────────────────────────────────────────────────────────────────

class ValueCombo(BaseModel):
    contract: str
    lookback: str
    threshold: float


class ValueRequest(BaseModel):
    roll_method: str = "ltd"
    roll_n: int = 5
    tc_bps: int = 5
    shift_n: int = 2
    combos: list[ValueCombo] | None = None
    metrics_year_start: int | None = None
    metrics_year_end: int | None = None
    feature_combo: ValueCombo | None = None
    equity_year_start: int | None = None
    equity_year_end: int | None = None
    focus_combo: ValueCombo | None = None
    rs_basis: str = "net"


@router.post("/{asset_class}/{product}/value")
def value(asset_class: str, product: str, body: ValueRequest):
    try:
        return value_service.get_value(
            asset_class, product,
            roll_method=body.roll_method, roll_n=body.roll_n, tc_bps=body.tc_bps, shift_n=body.shift_n,
            combos=[c.model_dump() for c in body.combos] if body.combos else None,
            skip_front_contract=_skip_front_contract(asset_class, product),
            metrics_year_start=body.metrics_year_start, metrics_year_end=body.metrics_year_end,
            feature_combo=body.feature_combo.model_dump() if body.feature_combo else None,
            equity_year_start=body.equity_year_start, equity_year_end=body.equity_year_end,
            focus_combo=body.focus_combo.model_dump() if body.focus_combo else None,
            rs_basis=body.rs_basis,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{asset_class}/{product}/value/heatmap")
def value_heatmap_endpoint(
    asset_class: str, product: str,
    roll_method: str = Query("ltd", pattern="^(ltd|5td)$"),
    roll_n: int = Query(5, ge=1, le=10),
    tc_bps: int = Query(5),
    shift_n: int = Query(2, ge=0, le=2),
    threshold: float = Query(0.10),
    year_start: int | None = None,
    year_end: int | None = None,
):
    try:
        return value_service.get_value_heatmap(
            asset_class, product,
            roll_method=roll_method, roll_n=roll_n, tc_bps=tc_bps, shift_n=shift_n,
            skip_front_contract=_skip_front_contract(asset_class, product),
            threshold=threshold, year_start=year_start, year_end=year_end,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Comparison ──────────────────────────────────────────────────────────────

class SeriesIn(BaseModel):
    dates: list[str]
    values: list[float]


class ComparisonRequest(BaseModel):
    roll_method: str = "ltd"
    roll_n: int = 5
    groups: dict[str, dict[str, SeriesIn]]
    tc_bps: int = 5
    vol_window_label: str = "63d (1qtr)"
    chosen: list[str] | None = None
    equity_year_start: int | None = None
    equity_year_end: int | None = None
    rs_basis: str = "net"
    show_vol_overlay: bool = False


@router.post("/{asset_class}/{product}/comparison")
def comparison(asset_class: str, product: str, body: ComparisonRequest):
    try:
        return comparison_service.get_comparison(
            asset_class, product,
            roll_method=body.roll_method, roll_n=body.roll_n,
            groups={g: {label: s.model_dump() for label, s in series.items()} for g, series in body.groups.items()},
            tc_bps=body.tc_bps, vol_window_label=body.vol_window_label, chosen=body.chosen,
            equity_year_start=body.equity_year_start, equity_year_end=body.equity_year_end,
            rs_basis=body.rs_basis, show_vol_overlay=body.show_vol_overlay,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
