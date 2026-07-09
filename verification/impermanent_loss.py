"""
Verification: Impermanent Loss + Fee Breakeven calculator
=========================================================
Tool: https://quantcalcs.com/impermanent-loss-calculator/

The page uses closed-form formulas. This script checks them against a direct
simulation of a constant-product (x*y=k) pool, so the formulas are never
trusted on their own. Every assertion below must pass.

Run:  python impermanent_loss.py
"""

import math

TOL = 1e-9


# ---------------------------------------------------------------- the formulas
# These are exactly what the calculator's JavaScript implements.

def impermanent_loss(r: float) -> float:
    """IL as a fraction (<= 0). r = (A price change) / (B price change)."""
    return 2 * math.sqrt(r) / (1 + r) - 1


def lp_value(deposit: float, r: float) -> float:
    """Value of the 50/50 LP position after the price ratio moves to r."""
    return deposit * math.sqrt(r)


def hodl_value(deposit: float, r: float) -> float:
    """Value if you had simply held the two assets instead."""
    return deposit * (r + 1) / 2


def breakeven_apr(r: float, days: float) -> float:
    """Fee APR at which LP + fees exactly equals holding.

    Note the subtlety the calculator is careful about: fees accrue on the LP
    POSITION VALUE, not on the original deposit. Since the position is worth
    less than the deposit once prices diverge, using the deposit would
    overstate the fees actually collected.
    """
    il = impermanent_loss(r)
    required_yield = 1 / (1 + il) - 1          # over the holding period
    return required_yield * 365.0 / days       # annualised


# ------------------------------------------------- independent ground truth
# No formulas here — we simulate the pool mechanics directly.

def simulate_pool(deposit: float, r: float):
    """Simulate a constant-product pool from first principles.

    Start 50/50 by value at price P0 = 1 (asset A priced in B).
    The invariant a*b = k holds; the pool price is b/a. Solving b/a = P1 with
    a*b = k gives a1 = sqrt(k/P1), b1 = sqrt(k*P1).
    Returns (lp_value, hodl_value).
    """
    p0 = 1.0
    a0 = (deposit / 2) / p0     # units of asset A
    b0 = deposit / 2            # units of asset B
    k = a0 * b0

    p1 = p0 * r
    a1 = math.sqrt(k / p1)
    b1 = math.sqrt(k * p1)

    return a1 * p1 + b1, a0 * p1 + b0


def solve_breakeven_apr(deposit: float, r: float, days: float) -> float:
    """Find the breakeven APR by bisection instead of the closed form."""
    hodl = simulate_pool(deposit, r)[1]

    def net(apr):
        lp = simulate_pool(deposit, r)[0]
        fees = lp * apr * days / 365.0        # fees on the position value
        return lp + fees - hodl

    lo, hi = 0.0, 100.0                        # 0% .. 10000% APR
    if net(lo) >= 0:                           # already breakeven (r == 1)
        return 0.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if net(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------- checks

def check_formula_matches_simulation():
    """The closed forms must reproduce the simulated pool exactly."""
    for r in [0.25, 0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 10.0]:
        sim_lp, sim_hodl = simulate_pool(10_000.0, r)
        assert abs(lp_value(10_000.0, r) - sim_lp) < TOL, f"LP value mismatch at r={r}"
        assert abs(hodl_value(10_000.0, r) - sim_hodl) < TOL, f"HODL value mismatch at r={r}"

        sim_il = sim_lp / sim_hodl - 1
        assert abs(impermanent_loss(r) - sim_il) < TOL, f"IL mismatch at r={r}"
    print("PASS  closed-form IL / LP / HODL match a direct x*y=k simulation")


def check_known_reference_values():
    """Textbook values for impermanent loss."""
    expected = {1.25: -0.6192, 1.5: -2.0204, 2.0: -5.7191, 3.0: -13.3975,
                4.0: -20.0000, 5.0: -25.4644}
    for r, pct in expected.items():
        got = impermanent_loss(r) * 100
        assert abs(got - pct) < 1e-3, f"IL({r}) = {got:.4f}%, expected {pct}%"
    print("PASS  IL matches published reference values (2x -> -5.72%, 5x -> -25.46%)")


def check_symmetry():
    """IL depends on the ratio, so doubling and halving cost the same."""
    for r in [1.5, 2.0, 3.0, 5.0, 10.0]:
        assert abs(impermanent_loss(r) - impermanent_loss(1 / r)) < TOL
    print("PASS  IL(r) == IL(1/r)  — direction of the move does not matter")


def check_no_divergence_no_loss():
    """If prices move together, there is no loss and nothing to break even on."""
    assert abs(impermanent_loss(1.0)) < TOL
    assert abs(breakeven_apr(1.0, 90)) < TOL
    print("PASS  r == 1  =>  IL = 0 and breakeven APR = 0")


def check_breakeven_apr_is_actually_breakeven():
    """At the breakeven APR, LP + fees must equal holding exactly."""
    for r in [1.1, 1.25, 1.5, 2.0, 3.0, 5.0]:
        for days in [1, 7, 30, 90, 365]:
            deposit = 10_000.0
            apr = breakeven_apr(r, days)
            lp = lp_value(deposit, r)
            fees = lp * apr * days / 365.0     # fees on the POSITION, not the deposit
            hodl = hodl_value(deposit, r)
            assert abs(lp + fees - hodl) < 1e-6, (
                f"not breakeven at r={r}, days={days}: {lp + fees:.6f} vs {hodl:.6f}")
    print("PASS  at the breakeven APR, LP + fees == holding (to the cent)")


def check_breakeven_matches_numerical_solve():
    """The closed-form breakeven must agree with a bisection solve."""
    for r in [1.25, 1.5, 2.0, 3.0, 5.0]:
        for days in [7, 30, 90, 365]:
            closed = breakeven_apr(r, days)
            solved = solve_breakeven_apr(10_000.0, r, days)
            assert abs(closed - solved) < 1e-6, (
                f"r={r}, days={days}: closed {closed:.8f} vs solved {solved:.8f}")
    print("PASS  closed-form breakeven APR matches an independent bisection solve")


def check_fees_on_position_not_deposit():
    """Guard the subtlety: fees accrue on the LP position value, not on the
    original deposit. Note the position is NOT always smaller than the deposit
    — when prices rise it is larger. Either way, charging fees against the
    deposit gives the wrong breakeven verdict, which is what this checks.
    """
    deposit, days = 10_000.0, 90

    for r in [0.5, 2.0]:                        # position smaller, then larger
        apr = breakeven_apr(r, days)            # by construction, exactly breakeven
        lp = lp_value(deposit, r)
        hodl = hodl_value(deposit, r)

        fees_correct = lp * apr * days / 365.0
        fees_wrong = deposit * apr * days / 365.0   # the common mistake

        # Correct method: lands exactly on breakeven.
        assert abs(lp + fees_correct - hodl) < 1e-6

        # Wrong method: misses breakeven, in whichever direction the position moved.
        assert abs((lp + fees_wrong) - hodl) > 1.0, (
            f"deposit-based fees should NOT land on breakeven at r={r}")

        direction = "understates" if lp > deposit else "overstates"
        print(f"PASS  r={r}: fees on position ${fees_correct:,.2f} hits breakeven; "
              f"fees on deposit ${fees_wrong:,.2f} {direction} the outcome "
              f"by ${abs(lp + fees_wrong - hodl):,.2f}")


def check_time_dependence():
    """A shorter hold needs a higher APR to out-earn the same loss."""
    aprs = [breakeven_apr(2.0, d) for d in [1, 7, 30, 90, 365]]
    assert all(aprs[i] > aprs[i + 1] for i in range(len(aprs) - 1))
    print("PASS  breakeven APR falls as the holding period lengthens")


def worked_example():
    """The example shown on the page, reproduced end to end."""
    deposit, r, days, apr = 10_000.0, 2.0, 90, 0.40
    il = impermanent_loss(r)
    lp = lp_value(deposit, r)
    hodl = hodl_value(deposit, r)
    fees = lp * apr * days / 365.0
    be = breakeven_apr(r, days)

    print("\nWorked example (the calculator's default inputs)")
    print(f"  deposit                {deposit:>12,.2f}")
    print(f"  A x2, B x1  ->  r =    {r:>12.4f}")
    print(f"  impermanent loss       {il * 100:>11.3f}%")
    print(f"  if simply held         {hodl:>12,.2f}")
    print(f"  LP before fees         {lp:>12,.2f}")
    print(f"  fees @ {apr:.0%} APR, {days}d   {fees:>12,.2f}")
    print(f"  LP + fees              {lp + fees:>12,.2f}")
    print(f"  breakeven fee APR      {be * 100:>11.2f}%")
    print(f"  net vs holding         {lp + fees - hodl:>+12,.2f}")

    assert abs(il * 100 - (-5.719)) < 0.001
    assert abs(be * 100 - 24.60) < 0.01
    assert abs((lp + fees) - 15_536.98) < 0.01


if __name__ == "__main__":
    check_formula_matches_simulation()
    check_known_reference_values()
    check_symmetry()
    check_no_divergence_no_loss()
    check_breakeven_apr_is_actually_breakeven()
    check_breakeven_matches_numerical_solve()
    check_fees_on_position_not_deposit()
    check_time_dependence()
    worked_example()
    print("\nAll checks passed.")
