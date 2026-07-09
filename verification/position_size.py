"""
Verification: Position Size & Max Safe Leverage calculator
==========================================================
Tool: https://quantcalcs.com/position-size-calculator/

Risk-based sizing is simple arithmetic, so the interesting claim this page makes
is the other one: the maximum leverage at which your stop still triggers *before*
liquidation. That has a closed form, and this script proves it by simulation.

Run:  python position_size.py
"""

import math

TOL = 1e-9


# ---------------------------------------------------------------- the formulas
# Exactly what the calculator's JavaScript implements.

def position_size(balance: float, risk_pct: float, entry: float, stop: float,
                  fee: float = 0.0):
    """Size so that being stopped out costs exactly `risk_pct` of the balance,
    fees included. Returns (qty, notional, risk_amount)."""
    risk_amount = balance * risk_pct
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return None
    loss_per_unit = stop_dist + fee * entry     # price loss + round-trip fees
    qty = risk_amount / loss_per_unit
    return qty, qty * entry, risk_amount


def liquidation_price(entry: float, leverage: float, mmr: float,
                      is_long: bool, fee: float = 0.0):
    """Isolated margin, maintenance charged on the current notional.
    Same formula as the liquidation-price calculator."""
    if is_long:
        num = 1 - 1 / leverage + fee
        if num <= 0 or mmr >= 1:
            return None
        return entry * num / (1 - mmr)
    return entry * (1 + 1 / leverage - fee) / (1 + mmr)


def max_safe_leverage(entry: float, stop: float, mmr: float, is_long: bool,
                      fee: float = 0.0):
    """Highest leverage at which liquidation is still beyond the stop.

    Long: need liq <= stop.
        entry*(1 - 1/L + fee)/(1 - mmr) <= stop
        1/L >= 1 + fee - (stop/entry)*(1 - mmr)
        L   <= 1 / (1 + fee - (stop/entry)*(1 - mmr))

    Short: need liq >= stop.
        entry*(1 + 1/L - fee)/(1 + mmr) >= stop
        L <= 1 / ((stop/entry)*(1 + mmr) - 1 + fee)

    Returns None when the denominator is <= 0, meaning any leverage is safe.
    """
    if is_long:
        denom = 1 + fee - (stop / entry) * (1 - mmr)
    else:
        denom = (stop / entry) * (1 + mmr) - 1 + fee
    if denom <= 0:
        return None                     # stop is so tight that liquidation never precedes it
    return 1 / denom


# ------------------------------------------------- independent ground truth

def simulate_stop_before_liquidation(entry, stop, leverage, mmr, is_long, fee=0.0,
                                     notional=10_000.0):
    """Walk the price from entry toward the stop. Report which triggers first by
    checking, at every step, whether equity has fallen to the maintenance
    requirement. No liquidation formula is used."""
    im = notional / leverage
    qty = notional / entry
    fee_cost = notional * fee

    steps = 200_000
    for i in range(1, steps + 1):
        t = i / steps
        p = entry + (stop - entry) * t          # sweeps toward the stop
        pnl = qty * (p - entry) if is_long else qty * (entry - p)
        equity = im + pnl - fee_cost
        maintenance = mmr * (qty * p)
        if equity <= maintenance:
            return "liquidation", p
    return "stop", stop


# ------------------------------------------------------------------- checks

def check_sizing_loses_exactly_the_risk():
    """Being stopped out must cost precisely the intended risk amount."""
    for balance in [1_000.0, 10_000.0, 250_000.0]:
        for risk_pct in [0.0025, 0.01, 0.02]:
            for entry, stop in [(60_000.0, 57_000.0), (60_000.0, 63_000.0),
                                (2.5, 2.35), (1800.0, 1750.0)]:
                for fee in [0.0, 0.0005, 0.001]:
                    qty, notional, risk_amt = position_size(balance, risk_pct, entry, stop, fee)
                    realised = qty * abs(entry - stop) + qty * entry * fee
                    assert abs(realised - risk_amt) < 1e-6, (
                        f"lost {realised:.6f}, intended {risk_amt:.6f}")
    print("PASS  a stop-out costs exactly the intended risk, fees included")


def check_sizing_scales_correctly():
    """Halving the stop distance doubles the position; the risk stays put."""
    b, rp, entry = 10_000.0, 0.01, 60_000.0
    wide = position_size(b, rp, entry, 57_000.0)[1]      # 5% away
    tight = position_size(b, rp, entry, 58_500.0)[1]     # 2.5% away
    assert abs(tight - 2 * wide) < 1e-6, "half the distance should double the size"
    print("PASS  halving the stop distance doubles the position size")


def check_max_leverage_is_the_boundary():
    """At max_safe_leverage the liquidation price sits exactly on the stop;
    a hair above it, liquidation comes first."""
    cases = [
        (60_000.0, 57_000.0, 0.005, True,  0.001),
        (60_000.0, 57_000.0, 0.004, True,  0.0),
        (60_000.0, 63_000.0, 0.005, False, 0.001),
        (2.5,      2.35,     0.01,  True,  0.0005),
        (1800.0,   1850.0,   0.005, False, 0.0),
    ]
    for entry, stop, mmr, is_long, fee in cases:
        lmax = max_safe_leverage(entry, stop, mmr, is_long, fee)
        assert lmax is not None

        at = liquidation_price(entry, lmax, mmr, is_long, fee)
        assert abs(at - stop) < 1e-6, f"at L_max liq {at} should equal stop {stop}"

        safe = liquidation_price(entry, lmax * 0.999, mmr, is_long, fee)
        risky = liquidation_price(entry, lmax * 1.001, mmr, is_long, fee)
        if is_long:
            assert safe < stop and risky > stop
        else:
            assert safe > stop and risky < stop
    print("PASS  at max safe leverage the liquidation price lands exactly on the stop")


def check_against_simulation():
    """The closed form must agree with a simulated margin account about which
    event fires first."""
    entry, stop, mmr, fee = 60_000.0, 57_000.0, 0.005, 0.001
    lmax = max_safe_leverage(entry, stop, mmr, True, fee)

    for leverage, expected in [(lmax * 0.9, "stop"), (lmax * 0.99, "stop"),
                               (lmax * 1.01, "liquidation"), (lmax * 1.2, "liquidation")]:
        event, _ = simulate_stop_before_liquidation(entry, stop, leverage, mmr, True, fee)
        assert event == expected, (
            f"L={leverage:.3f} simulated {event}, closed form expected {expected}")

    # and the same on the short side
    entry_s, stop_s = 60_000.0, 63_000.0
    lmax_s = max_safe_leverage(entry_s, stop_s, mmr, False, fee)
    for leverage, expected in [(lmax_s * 0.9, "stop"), (lmax_s * 1.1, "liquidation")]:
        event, _ = simulate_stop_before_liquidation(entry_s, stop_s, leverage, mmr, False, fee)
        assert event == expected
    print("PASS  a simulated margin account agrees on which fires first, stop or liquidation")


def check_wider_stop_allows_less_leverage():
    """A stop further from entry means liquidation is reached sooner in relative
    terms, so the safe leverage ceiling falls."""
    entry, mmr = 60_000.0, 0.005
    prev = None
    for stop in [59_400.0, 58_800.0, 57_000.0, 54_000.0, 48_000.0]:   # widening
        lmax = max_safe_leverage(entry, stop, mmr, True)
        if prev is not None:
            assert lmax < prev, "a wider stop should permit less leverage"
        prev = lmax
    print("PASS  widening the stop lowers the maximum safe leverage")


def check_fees_and_mmr_tighten_the_ceiling():
    """Both fees and a higher maintenance rate should reduce safe leverage."""
    entry, stop = 60_000.0, 57_000.0
    base = max_safe_leverage(entry, stop, 0.005, True, 0.0)
    with_fee = max_safe_leverage(entry, stop, 0.005, True, 0.001)
    with_mmr = max_safe_leverage(entry, stop, 0.01, True, 0.0)
    assert with_fee < base and with_mmr < base
    print(f"PASS  fees and maintenance both lower the ceiling "
          f"({base:.2f}x -> {with_fee:.2f}x with fees, {with_mmr:.2f}x with 1% mmr)")


def check_ceiling_always_exists_for_valid_input():
    """For any stop on the correct side of entry, a finite leverage ceiling
    exists. The None branch is a guard against invalid input, not a real case.

    Two limits worth pinning: as the stop tightens the ceiling grows without
    bound, but it is capped by the maintenance rate — with mmr = m, no leverage
    above roughly 1/m can ever be safe, because maintenance alone consumes the
    margin.
    """
    entry = 60_000.0

    # a long with a valid stop always has a ceiling
    for stop in [59_999.0, 59_940.0, 57_000.0, 30_000.0]:
        assert max_safe_leverage(entry, stop, 0.005, True) is not None

    # tighter stop -> higher ceiling, but bounded by 1/mmr
    mmr = 0.05
    ceiling_limit = 1 / mmr                      # = 20x
    for stop in [59_999.9, 59_999.99]:
        lmax = max_safe_leverage(entry, stop, mmr, True)
        assert lmax < ceiling_limit + 1e-6, f"{lmax} should not exceed {ceiling_limit}"
        assert lmax > ceiling_limit - 0.01, "and should approach it as the stop tightens"

    # invalid input: a "long" whose stop sits above entry -> no meaningful answer
    assert max_safe_leverage(entry, 63_000.0, 0.005, True) is None
    assert max_safe_leverage(entry, 57_000.0, 0.005, False) is None
    print(f"PASS  a finite ceiling always exists, approaching 1/mmr ({ceiling_limit:.0f}x "
          f"at 5% maintenance); invalid stops are rejected")


def worked_example():
    balance, risk_pct = 10_000.0, 0.01
    entry, stop, mmr, fee = 60_000.0, 57_000.0, 0.005, 0.001
    qty, notional, risk_amt = position_size(balance, risk_pct, entry, stop, fee)
    lmax = max_safe_leverage(entry, stop, mmr, True, fee)

    print("\nWorked example (the calculator's default inputs)")
    print(f"  balance                {balance:>12,.2f}")
    print(f"  risk per trade         {risk_pct:>11.1%}  = {risk_amt:,.2f}")
    print(f"  entry / stop           {entry:>12,.0f} / {stop:,.0f}")
    print(f"  position size          {qty:>12.6f} units")
    print(f"  notional               {notional:>12,.2f}")
    print(f"  max safe leverage      {lmax:>11.2f}x")
    print(f"  liq at that leverage   {liquidation_price(entry, lmax, mmr, True, fee):>12,.2f}")
    print(f"  liq at 20x             {liquidation_price(entry, 20, mmr, True, fee):>12,.2f}"
          f"   <- above the stop: liquidated first")

    assert abs(notional - 1960.7843) < 1e-3
    assert abs(lmax - 17.9372) < 1e-3


if __name__ == "__main__":
    check_sizing_loses_exactly_the_risk()
    check_sizing_scales_correctly()
    check_max_leverage_is_the_boundary()
    check_against_simulation()
    check_wider_stop_allows_less_leverage()
    check_fees_and_mmr_tighten_the_ceiling()
    check_ceiling_always_exists_for_valid_input()
    worked_example()
    print("\nAll checks passed.")
