"""
Verification: Liquidation Price calculator (isolated margin)
============================================================
Tool: https://quantcalcs.com/liquidation-price-calculator/

The page uses a closed-form liquidation price. This script checks it against a
direct simulation of a margin account: mark the position to market, subtract
the loss from the posted margin, and find the price at which remaining equity
falls to the maintenance requirement. Every assertion below must pass.

Run:  python liquidation_price.py
"""

import math

TOL = 1e-9


# ---------------------------------------------------------------- the formula
# Exactly what the calculator's JavaScript implements.

def liquidation_price(entry: float, leverage: float, mmr: float,
                      is_long: bool, fee: float = 0.0):
    """Isolated-margin liquidation price. Returns None if price alone cannot
    liquidate the position.

    Maintenance margin is charged on the CURRENT notional (qty * price), which
    is how exchanges compute it. Setting equity == maintenance and solving:
        long  liq = entry * (1 - 1/L + fee) / (1 - mmr)
        short liq = entry * (1 + 1/L - fee) / (1 + mmr)
    """
    if is_long:
        num = 1 - 1 / leverage + fee
        if num <= 0 or mmr >= 1:
            return None                   # margin covers a total loss
        return entry * num / (1 - mmr)
    return entry * (1 + 1 / leverage - fee) / (1 + mmr)


def adverse_move_fraction(entry: float, leverage: float, mmr: float,
                          is_long: bool, fee: float = 0.0):
    """Fraction the price must move against you before liquidation."""
    liq = liquidation_price(entry, leverage, mmr, is_long, fee)
    return None if liq is None else abs(liq / entry - 1)


def naive_liquidation_price(entry: float, leverage: float, mmr: float,
                            is_long: bool) -> float:
    """The common shortcut, kept only so the test below can show it is wrong.
    It charges maintenance on the ENTRY notional instead of the current one."""
    f = 1 / leverage - mmr
    return entry * (1 - f) if is_long else entry * (1 + f)


# ------------------------------------------------ independent ground truth
# No liquidation formula here — simulate the margin account directly.

def simulate_liquidation(entry: float, leverage: float, mmr: float,
                         is_long: bool, notional: float = 10_000.0,
                         fee: float = 0.0):
    """Walk the price until equity drops to the maintenance requirement.

    initial margin  = notional / leverage
    qty             = notional / entry
    at price p:
        pnl         = qty * (p - entry)          for a long
        equity      = initial_margin + pnl - fee_cost
        maintenance = mmr * (qty * p)            (on current notional)
    Liquidation is the p where equity == maintenance.
    Solved by bisection so no closed form is assumed.
    """
    im = notional / leverage
    qty = notional / entry
    fee_cost = notional * fee

    def equity_minus_maintenance(p):
        pnl = qty * (p - entry) if is_long else qty * (entry - p)
        equity = im + pnl - fee_cost
        maintenance = mmr * (qty * p)
        return equity - maintenance

    if equity_minus_maintenance(entry) <= 0:
        return None                       # already below maintenance at entry

    if is_long:
        lo, hi = 0.0, entry               # liquidation is below entry
    else:
        lo, hi = entry, entry * 100.0     # liquidation is above entry
        if equity_minus_maintenance(hi) > 0:
            return None                   # never liquidates in range

    for _ in range(300):
        mid = (lo + hi) / 2
        healthy = equity_minus_maintenance(mid) > 0
        if is_long:
            if healthy:
                hi = mid
            else:
                lo = mid
        else:
            if healthy:
                lo = mid
            else:
                hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------- checks

def check_formula_matches_simulation():
    """The closed form must reproduce the simulated margin account.

    Note the simulation applies maintenance margin to the CURRENT notional
    (qty * p), which is how exchanges compute it. The closed form is the
    algebraic solution of exactly that condition.
    """
    entry = 60_000.0
    for leverage in [2, 5, 10, 20, 50]:
        for mmr in [0.004, 0.005, 0.01]:
            for is_long in [True, False]:
                closed = liquidation_price(entry, leverage, mmr, is_long)
                sim = simulate_liquidation(entry, leverage, mmr, is_long)
                if closed is None or sim is None:
                    continue
                # agree to within a cent on a $60k asset
                assert abs(closed - sim) < 0.01, (
                    f"L={leverage} mmr={mmr} long={is_long}: "
                    f"closed {closed:.6f} vs sim {sim:.6f}")
    print("PASS  closed-form liquidation price matches a direct margin-account simulation")


def check_worked_example():
    """The default inputs shown on the page."""
    entry, leverage, mmr = 60_000.0, 10, 0.005
    liq = liquidation_price(entry, leverage, mmr, is_long=True)
    move = adverse_move_fraction(entry, leverage, mmr, True)

    assert abs(liq - 54_271.3568) < 1e-3, f"got ${liq:,.4f}"
    assert abs(move - 0.0954774) < 1e-6, f"got {move:.6%}"
    print(f"PASS  10x long @ $60,000, 0.5% maintenance -> ${liq:,.2f} "
          f"({move:.2%} adverse move)")


def check_naive_shortcut_is_wrong():
    """Guard the subtlety: charging maintenance on the entry notional is the
    common shortcut, and it misprices liquidation — badly at low leverage."""
    entry, mmr = 60_000.0, 0.005
    for leverage, min_err in [(2, 100.0), (5, 40.0), (10, 20.0)]:
        exact = liquidation_price(entry, leverage, mmr, True)
        naive = naive_liquidation_price(entry, leverage, mmr, True)
        sim = simulate_liquidation(entry, leverage, mmr, True)
        assert abs(exact - sim) < 0.01, "exact must match the simulation"
        assert abs(naive - exact) > min_err, (
            f"at {leverage}x the shortcut should be off by more than ${min_err}")
    err2 = naive_liquidation_price(entry, 2, mmr, True) - liquidation_price(entry, 2, mmr, True)
    print(f"PASS  the entry-notional shortcut is wrong: at 2x it misses by "
          f"${err2:,.2f} (the simulation agrees with the exact form, not the shortcut)")


def check_long_short_are_close_but_not_identical():
    """Because maintenance scales with the current notional, a short's distance
    to liquidation is slightly different from a long's — a detail the naive
    formula hides by making them exactly symmetric."""
    entry = 60_000.0
    for leverage in [3, 10, 25]:
        dl = adverse_move_fraction(entry, leverage, 0.005, True)
        ds = adverse_move_fraction(entry, leverage, 0.005, False)
        assert abs(dl - ds) < 0.02, "distances should still be close"
        assert dl != ds, "and not exactly equal under the exchange convention"
    print("PASS  long/short distances are close but not exactly symmetric (as expected)")


def check_higher_leverage_is_closer():
    """More leverage must move liquidation nearer to entry."""
    entry = 60_000.0
    prev = None
    for leverage in [2, 5, 10, 25, 50, 100]:
        liq = liquidation_price(entry, leverage, 0.005, is_long=True)
        if prev is not None:
            assert liq > prev, "higher leverage should liquidate sooner"
        prev = liq
    print("PASS  liquidation price rises toward entry as leverage increases")


def check_fees_move_liquidation_closer():
    """Paying fees eats margin, so liquidation arrives earlier."""
    entry, leverage, mmr = 60_000.0, 10, 0.005
    no_fee = liquidation_price(entry, leverage, mmr, True, fee=0.0)
    with_fee = liquidation_price(entry, leverage, mmr, True, fee=0.001)
    assert with_fee > no_fee, "fees should raise a long's liquidation price"

    sim = simulate_liquidation(entry, leverage, mmr, True, fee=0.001)
    assert abs(with_fee - sim) < 0.01, f"closed {with_fee:.2f} vs sim {sim:.2f}"
    print(f"PASS  a 0.10% round-trip fee moves liquidation "
          f"${no_fee:,.2f} -> ${with_fee:,.2f} (closer to entry)")


def check_no_liquidation_edge_case():
    """At 1x with no fees the posted margin covers a total loss, so price alone
    cannot liquidate a long: the tool must say so rather than print a number.

    With fees it is different — fees eat margin, so a liquidation price does
    exist, just very near zero. Both behaviours are checked here.
    """
    assert liquidation_price(60_000.0, 1.0, 0.005, True) is None

    with_fee = liquidation_price(60_000.0, 1.0, 0.005, True, fee=0.001)
    assert with_fee is not None, "fees erode margin, so liquidation exists"
    assert with_fee < 100.0, f"and it should sit near zero, got ${with_fee:,.2f}"
    sim = simulate_liquidation(60_000.0, 1.0, 0.005, True, fee=0.001)
    assert abs(with_fee - sim) < 0.01

    assert liquidation_price(60_000.0, 1.01, 0.005, True) is not None
    print(f"PASS  1x long: no liquidation without fees; with a 0.1% fee it exists "
          f"at ${with_fee:,.2f}, matching the simulation")


def check_maintenance_margin_effect():
    """A higher maintenance requirement liquidates you sooner."""
    entry, leverage = 60_000.0, 10
    a = liquidation_price(entry, leverage, 0.004, True)
    b = liquidation_price(entry, leverage, 0.01, True)
    assert b > a, "higher maintenance margin should liquidate sooner"
    print("PASS  raising the maintenance margin moves liquidation closer to entry")


def worked_table():
    entry = 60_000.0
    print("\nLiquidation price, long, entry $60,000, 0.5% maintenance")
    print("  leverage    adverse move    liquidation")
    for leverage in [2, 3, 5, 10, 20, 50, 100]:
        f = adverse_move_fraction(entry, leverage, 0.005, True)
        liq = liquidation_price(entry, leverage, 0.005, True)
        print(f"  {leverage:>5}x       {f:>8.2%}      {liq:>12,.2f}")


if __name__ == "__main__":
    check_formula_matches_simulation()
    check_worked_example()
    check_naive_shortcut_is_wrong()
    check_long_short_are_close_but_not_identical()
    check_higher_leverage_is_closer()
    check_fees_move_liquidation_closer()
    check_no_liquidation_edge_case()
    check_maintenance_margin_effect()
    worked_table()
    print("\nAll checks passed.")
