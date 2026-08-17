"""Precios DeepSeek V4 peak / off-peak (oficial desde 2026-08-16 16:00 UTC).

Fuente: https://api-docs.deepseek.com/quick_start/pricing/
Peak UTC: 01:00–04:00 y 06:00–10:00. Peak = 2 × off-peak.
Los precios guardados en BD son off-peak (cache miss / cache hit / output).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

# Off-peak oficiales (USD / 1M tokens)
DEEPSEEK_OFF_PEAK: dict[str, dict[str, Decimal]] = {
    "deepseek-v4-pro": {
        "input": Decimal("0.660000"),
        "cached_input": Decimal("0.022000"),
        "output": Decimal("1.980000"),
    },
    "deepseek-v4-flash": {
        "input": Decimal("0.220000"),
        "cached_input": Decimal("0.007000"),
        "output": Decimal("0.660000"),
    },
}

PEAK_MULTIPLIER = Decimal("2")
_CHILE_TZ = ZoneInfo("America/Santiago")


def is_deepseek_peak(now_utc: datetime | None = None) -> bool:
    """True si la hora UTC cae en franja peak de DeepSeek."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    hour = now.hour
    # [01:00, 04:00) y [06:00, 10:00)
    return (1 <= hour < 4) or (6 <= hour < 10)


def pricing_period_snapshot(now_utc: datetime | None = None) -> dict[str, Any]:
    """Estado horario actual para la UI / estimación de costo."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    chile = now.astimezone(_CHILE_TZ)
    peak = is_deepseek_peak(now)
    return {
        "is_peak": peak,
        "period": "peak" if peak else "off_peak",
        "period_label": "Hora punta (peak)" if peak else "Hora valle (off-peak)",
        "utc_now": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "chile_now": chile.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "chile_tz": "America/Santiago",
        "peak_windows_utc": ["01:00–04:00 UTC", "06:00–10:00 UTC"],
        "peak_windows_chile_note": (
            "En Chile (UTC-4 estandar): approx. 21:00-00:00 y 02:00-06:00; "
            "con horario de verano UTC-3: approx. 22:00-01:00 y 03:00-07:00."
        ),
        "peak_multiplier": float(PEAK_MULTIPLIER),
        "effective_from_utc": "2026-08-16T16:00:00Z",
    }


def rates_for_model(
    *,
    model_code: str,
    off_peak_input: Decimal | float | None,
    off_peak_output: Decimal | float | None,
    off_peak_cached: Decimal | float | None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Devuelve precios off-peak, peak y el activo ahora."""
    code = (model_code or "").strip()
    catalog = DEEPSEEK_OFF_PEAK.get(code)
    inp = Decimal(str(off_peak_input if off_peak_input is not None else (catalog or {}).get("input") or 0))
    out = Decimal(str(off_peak_output if off_peak_output is not None else (catalog or {}).get("output") or 0))
    cached = (
        Decimal(str(off_peak_cached))
        if off_peak_cached is not None
        else (catalog or {}).get("cached_input")
    )
    peak = is_deepseek_peak(now_utc)
    mult = PEAK_MULTIPLIER if peak else Decimal("1")

    def _pack(i: Decimal, o: Decimal, c: Decimal | None) -> dict[str, float | None]:
        return {
            "input_per_1m_usd": float(i),
            "output_per_1m_usd": float(o),
            "cached_input_per_1m_usd": float(c) if c is not None else None,
        }

    off = _pack(inp, out, cached)
    peak_rates = _pack(
        inp * PEAK_MULTIPLIER,
        out * PEAK_MULTIPLIER,
        (cached * PEAK_MULTIPLIER) if cached is not None else None,
    )
    active = peak_rates if peak else off
    return {
        "off_peak": off,
        "peak": peak_rates,
        "active": active,
        "active_period": "peak" if peak else "off_peak",
        "active_multiplier": float(mult),
    }


def apply_period_multiplier(
    amount: Decimal,
    *,
    now_utc: datetime | None = None,
) -> Decimal:
    if is_deepseek_peak(now_utc):
        return (amount * PEAK_MULTIPLIER).quantize(Decimal("0.000001"))
    return amount
