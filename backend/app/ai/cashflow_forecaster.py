import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

SEASON_LENGTH = 7  # weekly seasonality (days)
MIN_DAYS_FOR_HOLT_WINTERS = 2 * SEASON_LENGTH  # need >= 2 full seasonal cycles to fit


def _parse_timestamp(raw) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return pd.to_datetime(raw).to_pydatetime()
    except Exception:
        return None


def _build_daily_series(transactions: List[dict]) -> Optional[pd.Series]:
    """
    Aggregates raw transaction records into a REAL daily revenue time
    series (summed per calendar day), which is what an actual Holt-Winters
    fit needs as input. Returns None if there isn't enough timestamped
    history to build a meaningful series.
    """
    rows = []
    for t in transactions:
        ts = _parse_timestamp(t.get("timestamp"))
        amt = t.get("amount", 0.0)
        if ts is not None:
            rows.append((ts.date(), amt))

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=["date", "amount"])
    daily = df.groupby("date")["amount"].sum()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()

    # Fill any missing calendar days within the observed range with 0 so the
    # seasonal index (day-of-week) lines up correctly.
    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full_range, fill_value=0.0)
    return daily


def _holt_winters_additive_fit(series: pd.Series, season_length: int = SEASON_LENGTH,
                                alpha: float = 0.3, beta: float = 0.1, gamma: float = 0.2):
    """
    A genuine (from-scratch) additive Holt-Winters exponential smoothing
    fit: level + trend + seasonal components, each updated recursively
    across the historical series - not a single static day-of-week
    multiplier applied uniformly to every future day, which is what this
    forecaster previously did while still calling itself "Holt-Winters".

    Returns (level, trend, seasonal_indices, fitted_residual_std) so the
    caller can project forward and build residual-based confidence bounds.
    """
    values = series.values.astype(float)
    n = len(values)

    # Initialize level as the mean of the first season, trend as the
    # average day-over-day change across the first two seasons, and
    # seasonal indices as each day's deviation from its season's mean.
    first_season = values[:season_length]
    second_season = values[season_length:2 * season_length]
    level = float(np.mean(first_season))
    trend = float((np.mean(second_season) - np.mean(first_season)) / season_length)
    seasonal = [values[i] - level for i in range(season_length)]

    fitted = []
    for t in range(n):
        s_idx = t % season_length
        if t < season_length:
            fitted.append(level + seasonal[s_idx])
            continue
        forecast_t = level + trend + seasonal[s_idx]
        fitted.append(forecast_t)

        actual = values[t]
        prev_level = level
        level = alpha * (actual - seasonal[s_idx]) + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        seasonal[s_idx] = gamma * (actual - level) + (1 - gamma) * seasonal[s_idx]

    residuals = values[season_length:] - np.array(fitted[season_length:])
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else float(np.std(values)) * 0.2

    return level, trend, seasonal, residual_std


def forecast_cashflow(transactions: List[dict], expenses: List[dict], period_days: int = 30) -> Dict[str, Any]:
    """
    Cashflow forecast. Uses a genuine additive Holt-Winters exponential
    smoothing fit (level + trend + weekly-seasonal components, recursively
    updated across the vendor's actual daily transaction history) whenever
    there is enough timestamped history (>= 2 full weekly cycles).

    When there isn't enough history to fit a seasonal model, this falls
    back to a simple deterministic day-of-week baseline projection - and
    says so explicitly in `forecast_method`, instead of calling that
    fallback "Holt-Winters" too.
    """
    today = datetime.utcnow()
    daily_series = _build_daily_series(transactions) if transactions else None

    if daily_series is not None and len(daily_series) >= MIN_DAYS_FOR_HOLT_WINTERS:
        forecast_method = "HOLT_WINTERS_ADDITIVE"
        level, trend, seasonal, residual_std = _holt_winters_additive_fit(daily_series)

        ex_amounts = [e.get("amount", 0.0) for e in expenses] if expenses else []
        avg_daily_exp = float(np.mean(ex_amounts)) if ex_amounts else float(daily_series.mean()) * 0.45

        n_observed = len(daily_series)
        daily_forecasts = []
        total_rev = 0.0
        total_exp = 0.0

        for day_i in range(1, period_days + 1):
            target_date = today + timedelta(days=day_i)
            season_idx = (n_observed + day_i - 1) % SEASON_LENGTH
            rev_expected = max(200.0, level + (trend * day_i) + seasonal[season_idx])
            exp_expected = max(150.0, avg_daily_exp)
            net_expected = rev_expected - exp_expected

            # 95% CI widens with the forecast horizon (standard for
            # recursive smoothing forecasts, where each step compounds
            # uncertainty) rather than using a single fixed-width band.
            horizon_std = residual_std * np.sqrt(day_i)
            rev_lower = max(0.0, rev_expected - 1.96 * horizon_std)
            rev_upper = rev_expected + 1.96 * horizon_std

            total_rev += rev_expected
            total_exp += exp_expected

            daily_forecasts.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "expected_revenue": round(rev_expected, 2),
                "revenue_lower_bound": round(rev_lower, 2),
                "revenue_upper_bound": round(rev_upper, 2),
                "expected_expenses": round(exp_expected, 2),
                "expected_cashflow": round(net_expected, 2)
            })

    else:
        forecast_method = "DETERMINISTIC_BASELINE_PROJECTION"
        if not transactions or len(transactions) < 3:
            avg_daily_rev = 3500.0
            avg_daily_exp = 1600.0
            rev_std = 400.0
        else:
            tx_amounts = [t.get("amount", 0.0) for t in transactions]
            avg_daily_rev = float(np.mean(tx_amounts)) * 1.5
            rev_std = float(np.std(tx_amounts)) if len(tx_amounts) > 1 else avg_daily_rev * 0.15
            ex_amounts = [e.get("amount", 0.0) for e in expenses] if expenses else [avg_daily_rev * 0.45]
            avg_daily_exp = float(np.mean(ex_amounts)) if ex_amounts else avg_daily_rev * 0.45

        daily_forecasts = []
        total_rev = 0.0
        total_exp = 0.0
        alpha = 0.05

        for day_i in range(1, period_days + 1):
            target_date = today + timedelta(days=day_i)
            day_mult = 1.15 if target_date.weekday() in [5, 6] else 0.96
            trend_factor = 1.0 + (day_i * alpha * 0.01)

            rev_expected = max(600.0, avg_daily_rev * day_mult * trend_factor)
            exp_expected = max(250.0, avg_daily_exp * day_mult)
            net_expected = rev_expected - exp_expected

            rev_lower = max(200.0, rev_expected - (1.96 * rev_std))
            rev_upper = rev_expected + (1.96 * rev_std)

            total_rev += rev_expected
            total_exp += exp_expected

            daily_forecasts.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "expected_revenue": round(rev_expected, 2),
                "revenue_lower_bound": round(rev_lower, 2),
                "revenue_upper_bound": round(rev_upper, 2),
                "expected_expenses": round(exp_expected, 2),
                "expected_cashflow": round(net_expected, 2)
            })

    return {
        "period_days": period_days,
        "forecast_method": forecast_method,
        "total_expected_revenue": round(total_rev, 2),
        "total_expected_expenses": round(total_exp, 2),
        "total_expected_cashflow": round(total_rev - total_exp, 2),
        # NOT "empirical" - these bounds come from a Gaussian/normality
        # assumption on the residuals (± 1.96 standard deviations), not
        # from a resampled/bootstrapped empirical distribution.
        "confidence_level": "95% Parametric Confidence Interval (Gaussian assumption, ±1.96σ)",
        "daily_forecast": daily_forecasts
    }
