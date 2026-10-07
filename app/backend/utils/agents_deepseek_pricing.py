"""Precios DeepSeek Flash peak / off-peak (V4.1, vigentes desde 2026-09-10 04:00 UTC).

Fuente: https://api-docs.deepseek.com/quick_start/pricing/
Modelo: deepseek-flash (DeepSeek-V4.1-Flash). deepseek-v4-flash quedó retirado.
Peak UTC, lunes a viernes: 01:00–04:00 y 06:00–10:00. Peak = 2 × off-peak.
Fines de semana y feriados oficiales de China (día completo en Asia/Shanghai) son valle.
Los precios guardados en BD son off-peak (cache miss / cache hit / output).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

# Off-peak oficiales (USD / 1M tokens)
DEEPSEEK_OFF_PEAK: dict[str, dict[str, Decimal]] = {
    "deepseek-flash": {
        "input": Decimal("0.150000"),
        "cached_input": Decimal("0.003000"),
        "output": Decimal("0.600000"),
    },
}

# Feriados 2026 (国务院办公厅, 国办发明电〔2025〕7号). Día completo en China.
_CHINA_HOLIDAY_RANGES_2026: tuple[tuple[str, str], ...] = (
    ("2026-01-01", "2026-01-03"),
    ("2026-02-15", "2026-02-23"),
    ("2026-04-04", "2026-04-06"),
    ("2026-05-01", "2026-05-05"),
    ("2026-06-19", "2026-06-21"),
    ("2026-09-25", "2026-09-27"),
    ("2026-10-01", "2026-10-07"),
)

PEAK_MULTIPLIER = Decimal("2")
_CHILE_TZ = ZoneInfo("America/Santiago")
_CHINA_TZ = ZoneInfo("Asia/Shanghai")


def _expand_dates(ranges: tuple[tuple[str, str], ...]) -> frozenset[date]:
    days: set[date] = set()
    for start_s, end_s in ranges:
        cursor = date.fromisoformat(start_s)
        end = date.fromisoformat(end_s)
        while cursor <= end:
            days.add(cursor)
            cursor += timedelta(days=1)
    return frozenset(days)


CHINA_PUBLIC_HOLIDAYS = _expand_dates(_CHINA_HOLIDAY_RANGES_2026)


def _as_utc(now_utc: datetime | None) -> datetime:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def is_china_public_holiday(now_utc: datetime | None = None) -> bool:
    """True si el día calendario en China es feriado oficial (valle todo el día)."""
    china_day = _as_utc(now_utc).astimezone(_CHINA_TZ).date()
    return china_day in CHINA_PUBLIC_HOLIDAYS


def is_deepseek_peak(now_utc: datetime | None = None) -> bool:
    """True solo en punta real: lun–vie UTC, franjas 01–04 y 06–10, fuera de feriado chino."""
    now = _as_utc(now_utc)
    if now.weekday() >= 5:
        return False
    if is_china_public_holiday(now):
        return False
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
        "peak_weekdays_utc": "lunes a viernes",
        "is_china_public_holiday": is_china_public_holiday(now),
        "china_public_holidays": sorted(d.isoformat() for d in CHINA_PUBLIC_HOLIDAYS),
        "peak_windows_chile_note": (
            "Punta solo de lunes a viernes UTC, salvo feriado oficial de China "
            "(ese día completo es valle). Sábado y domingo son siempre valle."
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


def split_prompt_cache(
    prompt_tokens: int,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
) -> tuple[int, int]:
    """Deja hit + miss = prompt. Sin desglose, todo el prompt es cache miss."""
    prompt = max(0, int(prompt_tokens or 0))
    hit = max(0, int(cache_hit_tokens or 0))
    miss = max(0, int(cache_miss_tokens or 0))
    if prompt <= 0:
        return hit, miss
    if hit + miss <= 0:
        return 0, prompt
    if hit >= prompt:
        return prompt, 0
    if hit + miss != prompt:
        miss = prompt - hit
    return hit, miss


def estimate_token_cost_usd(
    *,
    off_peak_input: Decimal,
    off_peak_output: Decimal,
    off_peak_cached: Decimal | None,
    prompt_tokens: int,
    completion_tokens: int,
    cache_hit_tokens: int = 0,
    cache_miss_tokens: int = 0,
    now_utc: datetime | None = None,
) -> Decimal:
    """Costo DeepSeek: hit×caché + miss×entrada + salida, ×2 solo en punta real."""
    hit, miss = split_prompt_cache(prompt_tokens, cache_hit_tokens, cache_miss_tokens)
    completion = max(0, int(completion_tokens or 0))
    peak = is_deepseek_peak(now_utc)
    mult = PEAK_MULTIPLIER if peak else Decimal("1")
    in_price = off_peak_input * mult
    out_price = off_peak_output * mult
    cached_price = (off_peak_cached * mult) if off_peak_cached is not None else None
    million = Decimal(1_000_000)
    if cached_price is not None and (hit > 0 or miss > 0):
        input_cost = (Decimal(hit) / million) * cached_price + (Decimal(miss) / million) * in_price
    else:
        billed_in = hit + miss if hit + miss > 0 else max(0, int(prompt_tokens or 0))
        input_cost = (Decimal(billed_in) / million) * in_price
    cost = input_cost + (Decimal(completion) / million) * out_price
    return cost.quantize(Decimal("0.000001"))
