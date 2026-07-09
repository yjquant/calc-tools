"""
Verification: Funding Rate / Basis Carry calculator
==================================================
Tool: https://quantcalcs.com/funding-rate-calculator/

Perpetual futures settle funding every few hours. The closed forms on the page
are checked here against a period-by-period simulation of those settlements.

Run:  python funding_rate.py
"""

import math

TOL = 1e-9


# ---------------------------------------------------------------- the formulas
# Exactly what the calculator's JavaScript implements.

def periods_per_year(interval_hours: float) -> float:
    return 365.0 * 24.0 / interval_hours


def apr(rate: float, interval_hours: float) -> float:
    """Simple annualisation: rate per interval times intervals per year."""
    return rate * periods_per_year(interval_hours)


def apy(rate: float, interval_hours: float) -> float:
    """Annualisation with the payments reinvested each interval."""
    return (1 + rate) ** periods_per_year(interval_hours) - 1


def funding_simple(notional: float, rate: float, periods: float) -> float:
    """Funding over N periods with the position size held constant."""
    return notional * rate * periods


def funding_compounded(notional: float, rate: float, periods: float) -> float:
    """Funding over N periods with each payment folded back into the position."""
    return notional * ((1 + rate) ** periods - 1)


def breakeven_periods(rate: float, total_fee: float):
    """Periods of funding needed to repay the round-trip fees of the trade.

    A carry trade pays fees once (in and out) and collects funding repeatedly,
    so the position must be held long enough for the drip to cover the toll.
    Returns None when funding runs the wrong way and never repays anything.
    """
    if rate <= 0:
        return None
    return total_fee / rate


# ------------------------------------------------- independent ground truth

def simulate_funding(notional, rate, periods, reinvest):
    """Settle funding one period at a time. No closed form used."""
    size = notional
    collected = 0.0
    for _ in range(int(periods)):
        payment = size * rate
        collected += payment
        if reinvest:
            size += payment
    return collected


def simulate_breakeven(notional, rate, total_fee):
    """Step through settlements until cumulative funding covers the fees."""
    if rate <= 0:
        return None
    fees = notional * total_fee
    collected = 0.0
    n = 0
    while collected < fees and n < 10_000_000:
        collected += notional * rate
        n += 1
    return n


# ------------------------------------------------------------------- checks

def check_apr_apy_relationship():
    """APY must exceed APR for positive rates, and the gap widens with the rate."""
    gaps = []
    for r in [0.0001, 0.0003, 0.0005, 0.001]:
        a, y = apr(r, 8), apy(r, 8)
        assert y > a, f"APY {y} should exceed APR {a}"
        gaps.append(y - a)
    assert all(gaps[i] < gaps[i + 1] for i in range(len(gaps) - 1)), \
        "the compounding gap should widen as the rate rises"

    # For negative rates the compounded loss is *smaller* in magnitude than the
    # simple one, because each loss shrinks the base that the next one hits.
    r = -0.0003
    assert apy(r, 8) > apr(r, 8), "compounded loss should be less severe than simple"
    print("PASS  APY exceeds APR, the gap widens with the rate, and losses compound less harshly")


def check_periods_per_year():
    assert abs(periods_per_year(8) - 1095.0) < TOL
    assert abs(periods_per_year(1) - 8760.0) < TOL
    assert abs(periods_per_year(4) - 2190.0) < TOL
    print("PASS  8-hour funding settles 1095 times a year")


def check_funding_matches_simulation():
    """Both closed forms must reproduce a period-by-period settlement."""
    for notional in [1_000.0, 10_000.0, 500_000.0]:
        for rate in [0.0001, 0.0005, -0.0002]:
            for periods in [1, 3, 90, 365]:
                simple = funding_simple(notional, rate, periods)
                sim_simple = simulate_funding(notional, rate, periods, reinvest=False)
                assert abs(simple - sim_simple) < 1e-6

                comp = funding_compounded(notional, rate, periods)
                sim_comp = simulate_funding(notional, rate, periods, reinvest=True)
                assert abs(comp - sim_comp) < 1e-6, (
                    f"{comp} vs {sim_comp} at n={notional} r={rate} p={periods}")
    print("PASS  closed-form funding matches a period-by-period settlement simulation")


def check_compounding_direction():
    """Reinvesting gains beats not reinvesting; reinvesting losses hurts less."""
    n, p = 10_000.0, 90
    assert funding_compounded(n, 0.0001, p) > funding_simple(n, 0.0001, p)
    assert funding_compounded(n, -0.0001, p) > funding_simple(n, -0.0001, p)
    print("PASS  compounding helps a receiver and cushions a payer")


def check_breakeven_is_actually_breakeven():
    """At the breakeven period count, funding collected equals fees paid."""
    notional = 10_000.0
    for rate in [0.0001, 0.0003, 0.001]:
        for fee in [0.0005, 0.001, 0.002, 0.004]:
            bp = breakeven_periods(rate, fee)
            collected = funding_simple(notional, rate, bp)
            paid = notional * fee
            assert abs(collected - paid) < 1e-6, f"{collected} vs {paid}"
    print("PASS  at the breakeven period, funding collected equals the fees paid")


def check_breakeven_matches_simulation():
    """The closed form must agree with stepping through settlements."""
    notional = 10_000.0
    for rate in [0.0001, 0.0005]:
        for fee in [0.001, 0.002]:
            closed = breakeven_periods(rate, fee)
            stepped = simulate_breakeven(notional, rate, fee)
            # stepping lands on the first period at or past breakeven
            assert math.ceil(closed - 1e-9) == stepped, f"{closed} vs {stepped}"
    print("PASS  closed-form breakeven agrees with a stepped settlement count")


def check_negative_rate_never_breaks_even():
    """If funding runs against you it never repays the fees."""
    assert breakeven_periods(-0.0001, 0.002) is None
    assert breakeven_periods(0.0, 0.002) is None
    print("PASS  a negative or zero funding rate reports no breakeven")


def check_higher_fees_need_longer_holds():
    prev = None
    for fee in [0.0005, 0.001, 0.002, 0.004]:
        bp = breakeven_periods(0.0001, fee)
        if prev is not None:
            assert bp > prev
        prev = bp
    print("PASS  higher fees push the breakeven further out")


def worked_example():
    notional, rate, interval = 10_000.0, 0.0001, 8
    days, fee = 30, 0.002
    periods = days * 24 / interval

    print("\nWorked example (the calculator's default inputs)")
    print(f"  notional               {notional:>12,.2f}")
    print(f"  rate per 8h            {rate * 100:>11.4f}%")
    print(f"  APR                    {apr(rate, interval) * 100:>11.2f}%")
    print(f"  APY (compounded)       {apy(rate, interval) * 100:>11.2f}%")
    print(f"  periods in {days}d        {periods:>12.0f}")
    print(f"  funding, simple        {funding_simple(notional, rate, periods):>12,.2f}")
    print(f"  funding, compounded    {funding_compounded(notional, rate, periods):>12,.2f}")
    bp = breakeven_periods(rate, fee)
    print(f"  round-trip fees {fee:.2%}  {notional * fee:>12,.2f}")
    print(f"  breakeven              {bp:>12.1f} periods = {bp * interval / 24:.1f} days")

    assert abs(apr(rate, interval) - 0.1095) < 1e-6
    assert abs(apy(rate, interval) - 0.115718) < 1e-5
    assert abs(funding_simple(notional, rate, periods) - 90.0) < 1e-6
    assert abs(bp - 20.0) < 1e-9


if __name__ == "__main__":
    check_periods_per_year()
    check_apr_apy_relationship()
    check_funding_matches_simulation()
    check_compounding_direction()
    check_breakeven_is_actually_breakeven()
    check_breakeven_matches_simulation()
    check_negative_rate_never_breaks_even()
    check_higher_fees_need_longer_holds()
    worked_example()
    print("\nAll checks passed.")
