# Verification

Every calculator on [quantcalcs.com](https://quantcalcs.com) publishes the
formula it uses. That is only half of a promise — a formula on a page can still
be wrong. These scripts are the other half: each one checks a calculator's
closed-form maths against an **independent simulation** of the thing being
modelled, plus the invariants that must hold if the maths is right.

No dependencies. Python 3 only.

```bash
python impermanent_loss.py
python liquidation_price.py
```

Each prints a line per check and exits non-zero if anything fails.

## What is checked

**`liquidation_price.py`** — [Liquidation price calculator](https://quantcalcs.com/liquidation-price-calculator/)

Simulates a margin account directly: mark the position to market, deduct fees,
step the price until equity falls to the maintenance requirement. The closed
form must land on the same price across 126 combinations of leverage,
maintenance rate, fee and direction. It also checks that more leverage
liquidates sooner, that fees move liquidation closer, and that a 1× long with
no fees reports *no liquidation* rather than a wrong number.

One finding worth stating plainly, because it is the difference between this
calculator and most others: exchanges charge maintenance margin on the
position's **current** notional, not its notional at entry. Solving that
condition gives

```
long  liq = entry × (1 − 1/L + fee) ÷ (1 − mmr)
short liq = entry × (1 + 1/L − fee) ÷ (1 + mmr)
```

The widespread shortcut `entry × (1 ∓ (1/L − mmr))` charges maintenance at
entry instead. It is off by about 0.5% at 2× leverage and 0.05% at 10×. The
simulation agrees with the exact form, not the shortcut, and the test suite
asserts that it does.

**`impermanent_loss.py`** — [Impermanent loss calculator](https://quantcalcs.com/impermanent-loss-calculator/)

Simulates a constant-product pool from first principles, tracking both token
balances through the price move under `x·y = k`, and checks the closed forms
reproduce it exactly. The breakeven fee APR is verified twice: once in closed
form, once by bisection, and the two must agree.

The subtlety here is that trading fees accrue on the **LP position value**, not
on the original deposit. The position is not always smaller than the deposit —
when prices rise it is larger — so charging fees against the deposit gets the
breakeven verdict wrong in either direction. A test pins this.

## Why bother

The site is written under a pen name. That means asking anyone to trust a
credential would be worth nothing, so the calculators are built to be checked
instead: the formula is on the page, the source is in this repository, and the
maths is verified against a simulation you can run yourself.

If you find an error, please open an issue or email `hello@quantcalcs.com`.
Corrections are welcome and will be fixed.
