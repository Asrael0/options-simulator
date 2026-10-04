"""English version of the guide: same anchors and order as ``SECTIONS`` in guide.py.

Each entry is (anchor, title, Markdown body). guide.py turns them into ``Section``.
"""

from __future__ import annotations

SECTIONS_EN: list[tuple[str, str, str]] = [
    (
        "option",
        "What an option is",
        """
An option is a **contract that gives a right, not an obligation**. The buyer
pays a sum — the **premium** — and in exchange gets the right to buy or sell a
stock at a fixed price until a given date.

The seller collects the premium and takes on the mirror obligation: if the
buyer decides to exercise, the seller *must* honour the deal.

This asymmetry is everything. The buyer's loss is limited to the premium paid
and the gain can be large. The seller's gain is limited to the premium collected
and the loss can be very large. There is no "better" side: the premium is
exactly the price the market puts on that imbalance.

In the simulator every row of the «Position legs» table is one contract. A
position can have as many as you like, and the chart always shows the
**combined** result.
""",
    ),
    (
        "call-put",
        "Calls and puts, long and short: the four combinations",
        """
There are two kinds of option and two sides to be on. Four combinations, and it
helps to learn them as four different bets.

| | Bought (**long**) | Sold (**short**) |
|---|---|---|
| **Call** | You bet it goes up. You pay the premium, unlimited gain. | You bet it does *not* go up. You collect the premium, **unlimited loss**. |
| **Put** | You bet it goes down. You pay the premium, large but limited gain (the price cannot go below zero). | You bet it does *not* go down. You collect the premium, large but limited loss. |

Read the two right-hand cells carefully. Selling options means collecting a
small, certain sum right away while taking on a rare, large risk. It is a
legitimate and common strategy, but the risk profile is the opposite of what the
immediate income suggests.

The simulator says so explicitly: when a position has unlimited loss, the
summary shows «UNLIMITED» and a red warning instead of a reassuring number.
""",
    ),
    (
        "strike-premium",
        "Strike, premium, expiry",
        """
The **strike** (or exercise price) is the price fixed in the contract. A call
with strike 100 gives the right to buy at 100, whatever the market does.

The **premium** is what the contract costs. The simulator computes it with the
model, but you can overwrite it by typing your own value: useful when you want
to use the real price seen on the order book instead of the theoretical one.

**Days to expiry** is how much time is left. The more time is left, the more the
option is worth: there is more room for something to happen. Time value does
not decay linearly — it speeds up as expiry gets closer, which is why theta grows
in the last few days.

Mind one convention: in the engine prices are always **per unit of
underlying**. A premium of 3.59 means 3.59 per share. A standard US contract
covers 100 of them, so the real outlay is 359 — and that is what the «Costs» tab
shows.
""",
    ),
    (
        "moneyness",
        "Moneyness: ITM, ATM, OTM",
        """
*Moneyness* tells you whether the option would be worth anything if it expired
right now.

- **ITM** (*in the money*) — it has intrinsic value. A call is ITM when spot is
  above the strike; a put when it is below.
- **ATM** (*at the money*) — spot and strike nearly coincide. The simulator uses
  a 1.5% band.
- **OTM** (*out of the money*) — no intrinsic value. It is worth something only
  because things may change before expiry.

An OTM option is not "worthless": it has a premium, and that premium is all
time value. That is also why OTM options lose value faster as expiry
approaches — they have nothing else to lose.

In the legs table the coloured tag on the right shows each contract's
moneyness, updated as you move spot.
""",
    ),
    (
        "intrinsic-time-value",
        "Intrinsic value and time value",
        """
An option's premium always splits into two parts:

**Intrinsic value** — what it would be worth if it expired now. For a call it is
`max(spot − strike, 0)`, for a put `max(strike − spot, 0)`. It cannot be
negative: at worst you do not exercise.

**Time value** — everything else. It is what you pay for the chance that things
improve before expiry. It depends on how much time is left and on how much the
stock moves (volatility).

At expiry time value is **zero** by definition: no time is left. That is why on
the chart the «value today» curve always sits above the «at expiry» line when you
are long, and sinks onto it as the days go by. The gap between the two curves
*is* the time value.
""",
    ),
    (
        "payoff",
        "The payoff diagram",
        """
This is the central tool. The horizontal axis is the price of the underlying,
the vertical axis the profit or loss of the position.

**The white line** is the result at expiry. It is a broken line with a corner at
every strike, and it is the final P&L. It is the line that matters.

**The dashed purple line** is the value today, at the current volatility. It is
smoother and sits higher (if you are long) because it still includes time value.
Reduce the days to expiry and you will see it bend step by step towards the
white one: time decay made visible.

**The coloured areas** — green above zero, red below — refer to the result at
expiry, and their borders fall exactly on the break-evens.

**The vertical lines**: dashed orange for strikes, solid blue for the current
spot, dashed green for the break-evens.

A practical tip: load a strategy, then move the days slider from 365 towards 0
and watch only the purple curve. It is the densest lesson the simulator can
give.
""",
    ),
    (
        "break-even",
        "Break-even",
        """
The break-even is the price at which the position breaks even at expiry: you
neither gain nor lose. For a bought call it is simply `strike + premium`,
because you have to earn back what you paid.

With several legs there can be more than one break-even. An iron condor, for
example, has two: the profit zone lies in between.

In the simulator break-evens are not found by trial and error: the payoff at
expiry is **piecewise linear**, with corners only at the strikes, so they are
solved in closed form segment by segment. The P&L at the break-even is exactly
zero, not "zero within sampling error".
""",
    ),
    (
        "extremes",
        "Maximum profit and loss",
        """
Not every extreme is a number. A bought call has **unlimited** profit: the stock
can rise without a ceiling. A naked sold call has, symmetrically, **unlimited**
loss.

The simulator tells the two cases apart by looking at the slope of the payoff on
the far right: if it rises, profit is unlimited; if it falls, loss is. It does
not sample the visible chart — a maximum read "on the range shown" would be a
finite and falsely reassuring number.

Note one real asymmetry: a bought put has **limited** profit, because a stock
price cannot go below zero. The maximum is `strike − premium`.
""",
    ),
    (
        "greeks",
        "The Greeks, one by one",
        """
The Greeks measure how much the position's value reacts when one variable
changes. They are derivatives: they tell the *instantaneous* reaction, not the
one over large moves.

**Δ Delta** — how much the value changes for +$1 in the underlying. It is the
directional exposure: a delta of 0.53 behaves like 53 shares. A call has a delta
between 0 and 1, a put between −1 and 0, a share exactly 1.

**Γ Gamma** — how much the *delta* changes for +$1 in the underlying. It is the
curvature. High gamma means the directional exposure changes fast: it peaks near
the strike and close to expiry. Whoever is long options has positive gamma, which
is why they gain from sharp moves.

**Θ Theta** — how much the position loses for each day that passes, all else
equal. Negative for net buyers: time erodes the premium. Positive for net
sellers — it is precisely their business model.

**ν Vega** — how much the value changes for +1 point of implied volatility.
Always positive when you are long options. Vega is not really a Greek letter:
traders made the name up.

**ρ Rho** — how much the value changes for +1 point of the risk-free rate. The
least relevant on short expiries, the most relevant on long ones.

In the simulator the Greeks are **aggregated**: summed over all legs, with sign
and quantity already applied. It is the number that describes the position as a
whole.
""",
    ),
    (
        "volatility",
        "Implied volatility and vol crush",
        """
**Implied volatility** is not a forecast: it is the number that, fed into the
model, gives back the price the market is actually trading at. In practice it is
the price of uncertainty, expressed as an annual percentage.

It rises when the market expects movement — before earnings, a central bank
decision, a corporate event. And it collapses right after, when the uncertainty
is resolved. This collapse is called **vol crush**.

It is a classic trap: you buy options before earnings, the stock moves in the
right direction, and you lose anyway, because the drop in IV takes away more than
the price move gave.

The **«Scenarios»** tab is there to show it. You set three things — where the
stock will be, in how many days, with which volatility (there is a «Crash −50%»
button) — and the simulator shows the P&L and **where it comes from**:

- *if you closed today*: the starting point;
- *price move*: how much the stock's move adds or takes away;
- *time passing*: the theta accumulated up to that day;
- *volatility change*: the effect of IV, i.e. vega.

The four items add up exactly to the result. Below, the **scenario matrix**
crosses price changes (columns) with IV changes (rows): if the colours change
more going down than going right, the position fears volatility more than price.
""",
    ),
    (
        "european-american",
        "European, American and early exercise",
        """
A **European** option can be exercised only at expiry. An **American** one at
any time up to expiry.

That extra right is worth something, so an American option cannot cost less than
the matching European one. How much it is worth depends on the case:

- **Call without dividends**: early exercise is *never* optimal. Exercising means
  paying the strike earlier than needed, giving up the interest on that money,
  and throwing away the remaining time value. Better to sell the option. Result:
  American and European calls are worth **exactly the same**.
- **ITM put**: here early exercise can pay off. You collect the strike right away
  and start earning interest on it. The simulator shows it well with
  `S=80, K=100, 90 days, r=6%`: the American is worth ≈ 20.00 against ≈ 19.02 for
  the European.
- **Call with high dividends**: it can pay to exercise just before the ex-date to
  collect the dividend. Raise the «Dividend yield» field and you will see it.

Changing the exercise style in the simulator also changes the *model* used: a
closed formula for Europeans, a binomial tree for Americans.
""",
    ),
    (
        "models",
        "The two pricing models",
        """
**Black-Scholes-Merton** is a closed formula: give it the parameters and you get
the price in one direct calculation. It is valid only for European options,
because it assumes no early exercise. It is instant and also gives exact Greeks.

**The binomial tree (Cox-Ross-Rubinstein)** builds every possible price path over
N discrete steps, then walks back from expiry to today. At each node it compares
«keep the option» with «exercise it now» and takes the larger: that is how the
value of early exercise *emerges* from the calculation instead of being added by
hand.

The tree converges to Black-Scholes as the steps grow, but in an oscillating way:
with 500 steps it gives 3.5894 against the analytical 3.5911. That is not a bug —
it is discretisation, and the simulator has a test that checks it.

One visible detail: the tree costs O(N²). That is why the chart curves use fewer
steps than the numbers you read on screen. The shape is identical to the eye, the
numbers keep full precision.
""",
    ),
    (
        "strategies",
        "The prebuilt strategies",
        """
The «Strategies» menu is only a starting point: once a strategy is loaded, every
leg can still be edited.

- **Bull call spread** — buy an ATM call, sell a higher one. Bullish, but both
  gain and loss are limited. Cheaper than a plain call.
- **Bear put spread** — the bearish mirror image.
- **Long straddle** — call and put on the same strike. You bet on *movement*,
  not direction. It needs to move a lot: you pay two premiums.
- **Long strangle** — like the straddle but with different, further-out strikes.
  Cheaper, needs a bigger move.
- **Iron condor** — sell an inner strangle and buy the outer wings. You gain if
  the stock does *not* move. The bought wings are what keep the loss limited.
- **Covered call** — own 100 shares and sell a call. You collect the premium in
  exchange for a cap on the gain.
- **Protective put** — own the shares and buy a put. It is insurance: you pay a
  premium to limit the downside.
- **Collar** — the previous two together: the sold call pays for the bought put.
  Often at almost zero cost, in exchange for a limited gain.
- **Risk reversal** — sell an OTM put and buy an OTM call. Cheap bullish
  exposure, but with the risk of the sold put.

The three that include the stock use a leg of type «Stock», whose entry price is
not a strike: it is the price at which you bought the shares.
""",
    ),
    (
        "costs",
        "The real cost of the trade",
        """
The engine works **per unit of underlying**. The «Costs» tab turns those numbers
into real money, with two parameters:

**Contract multiplier** — how many units one contract controls. The US standard
is 100.

**Packages** — how many times you replicate the whole strategy.

The cost of a leg is therefore `premium × multiplier × contracts × packages`.
A bull call spread that "costs 2.94" per unit, with multiplier 100 and 5
packages, needs $1,468 of real money.

One warning the simulator cannot put in figures: **credit** positions (those that
collect net premium) need margin at the broker, which can be much larger than the
credit collected and is not shown here.
""",
    ),
    (
        "frozen-premiums",
        "Frozen premiums: why, and what changes",
        """
This is a design choice worth understanding, because it is the most important
difference from many simulators.

When you open a position you pay a certain premium. That cost is **history**: it
no longer changes. If the stock rises tomorrow, the *value* of your position
changes, not what you spent to open it.

Many simulators recompute the premium every time you move a slider. The result is
misleading: moving spot to see «what happens if it rises» also changes the entry
cost, and the break-evens slide along with the cursor. The «value today» curve
ends up *always* crossing zero at the spot price, which teaches nothing.

Here, with the switch on (the default), premiums stay fixed at the moment you
opened the position. Move spot and you see the net cost and the break-evens **stay
put**: that is the correct behaviour.

When the current market drifts away from the snapshot, a notice shows the values
the premiums are fixed at. It is needed, because otherwise a premium computed at
spot 100 while the sliders show 115 would simply look wrong.

If you want the traditional behaviour, turn the switch off.
""",
    ),
    (
        "time-map",
        "Time passing: the «in N days» curve and the P&L map",
        """
Above the chart there is a **time** slider. Moving it shows a terracotta curve,
«In N d»: the value of the position that many days from now, with volatility and
rate unchanged. With the ▶ button time runs by itself up to expiry, and you see
the «today» curve bend towards the final broken line. It is **theta** made
visible.

The **P&L map** tab shows the same idea on a grid: underlying price
horizontally, days from today to expiry vertically. Each cell is the gain (green)
or the loss (red) for that combination. Losses and profits have separate colour
scales: the deepest red is the worst loss on the map, the deepest green the best
profit, so even a small loss stays visible next to large profits.

For a bought **straddle**, for example, you see the red «valley» around the
strike widening as expiry approaches.
""",
    ),
    (
        "probability",
        "Probability of profit",
        """
The summary shows the **probability that the position ends in profit at
expiry**. It uses the same model as the prices: the stock's final price follows a
lognormal distribution with the current implied volatility. The break-evens split
the possible prices into ranges; the probabilities of the ranges where the P&L is
positive are added up.

Two caveats. It is a **risk-neutral** probability, i.e. the one implied by option
prices, not a forecast of where the stock will really go. And it is about
**expiry** only: a position can be in profit halfway and end in a loss, or the
other way round.

Strategies that collect premium (selling options) often have a high probability
of gaining a little and a low one of losing a lot: probability alone does not
tell you whether a strategy is «worth it».
""",
    ),
    (
        "saving",
        "Saving, comparing, exporting and printing",
        """
- **Save** (the «My positions» box) stores the position under a name. You find
  it again even after shutting the simulator down, and on the Settings page you
  can reopen or delete it.
- **Compare with** (above the chart) draws the at-expiry P&L of a saved position
  next to the open one: useful to see, for example, how much more a straddle
  costs than a single call.
- **Export file / Import file** write and read a `.json` file with the full
  position, to move it to another computer or another person.
- The **image** icon downloads the chart as PNG; the **PDF** icon opens a
  printable summary: in the print window choose «Save as PDF».
""",
    ),
    (
        "market",
        "Real options: the chain and the comparison with the model",
        """
The **Real options** page downloads from CBOE, the main US options exchange, all
the options listed on a US stock (AAPL, SPY, TSLA…). The data arrives with about
**15 minutes of delay** and is meant for learning, not trading. Index symbols
take an underscore: `_SPX`.

The search box suggests about 130 stocks, ETFs and indices grouped by category
(including European and Italian companies listed in the US, such as Ferrari,
Stellantis and Eni), but **any US symbol with options works**: just type it and
press Enter. Do not load dozens in a few seconds: CBOE pauses whoever makes too
many requests.

**The chain** is the table every broker shows: calls on the left, puts on the
right, strikes in the middle, the blue row at the current price. For each option:

| Column | Meaning |
|---|---|
| Bid | the price someone is willing to **buy** at: what you collect if you sell |
| Ask | the price someone is willing to **sell** at: what you pay if you buy |
| IV | the implied volatility in that price |
| Δ | the delta |
| OI | open interest: how many contracts exist on that option |

Clicking one side of a row chooses whether to buy (at the ask) or sell (at the
bid). Your picks gather in **«Your picks»**; with **«Study in the simulator»**
they become a position with real spot, days, IV and premiums. The gap between bid
and ask — the *spread* — is a real cost that the simulator, working from
theoretical prices, would otherwise not see.

**Rate and dividend are not made up.** The model needs both, but the market does
not publish them anywhere: they are derived from the options themselves through
**put-call parity**. A bought call and a sold put on the same strike are
equivalent to owning the stock «forward», so the difference C − P reveals the
forward price.

- The **rate** comes from the S&P 500, whose options are European: there the
  parity holds exactly. It is refreshed at most every 6 hours.
- Each stock's **implied yield** comes from its forward. It includes dividends
  but also the stock's borrow cost: that is why Tesla, which pays no dividend,
  still shows a small positive value.
- The **«Call/put check»** box verifies the result: with the right rate and
  dividend, a call and a put on the same strike have the same implied
  volatility. For high-dividend stocks (Exxon, JPMorgan, Coca-Cola) the gap drops
  from 2–4 points to about half a point, which is noise from the bid-ask spread.

Options on **indices** (SPX, NDX, RUT, VIX) are European, those on stocks and ETFs
American: the simulator uses the right style automatically.

**Model vs market** prices every strike with *a single* volatility, as
Black-Scholes does, and puts it next to the real price. If the model were right,
the market IV would be a flat line. It is not: on stocks, low-strike puts have
higher IV. It is the volatility **smile** (or *smirk*): the market pays for
protection against crashes that the lognormal distribution considers almost
impossible.
""",
    ),
    (
        "portfolio",
        "The virtual portfolio",
        """
The simulator tells you what **should** happen. The virtual portfolio shows you
what **really** happens, without risking a cent.

On the «Real options» page pick one or more options and press **«Open in the
portfolio»**. The program records:

- the **real prices**: buyers pay the ask, sellers collect the bid;
- the **model's forecast** at that moment: probability of profit, break-evens,
  maximum gain and loss;
- **your forecast**, if you write one («I think it goes above 340»).

On the **Portfolio** page press «Refresh prices» (it also happens on its own when
prices are more than a quarter of an hour old): each position shows what it is
worth now, how the stock price and volatility have changed, and a chart of its
progress with one point per day.

Two things stand out right away:

- **A freshly opened position is already at a loss.** Value is measured halfway
  between bid and ask, but you bought at the ask. Closing right away you pay the
  spread twice, on the way in and on the way out.
- **«Your forecasts against reality»** compares the average probability the model
  gave you with how many positions you actually closed in profit. With few trades
  luck weighs a lot: the comparison becomes meaningful after a few dozen.

Expired positions close by themselves at intrinsic value, computed on the stock
price of the day you refresh them. Commissions, margin and early exercise are not
simulated.
""",
    ),
    (
        "expensive-cheap",
        "Are options expensive or cheap? Implied against historical",
        """
On the «Real options» page, the **Volatility** tab compares two numbers:

- 30-day **implied volatility** (IV): how much the market *expects* the stock to
  move, derived from option prices;
- **historical volatility**: how much the stock *actually* moved, measured on the
  closing prices of the last 20 trading days (about a month), 60 (three months)
  and 252 (a year). It is the standard deviation of daily returns, multiplied by
  √252 to make it annual.

The ratio between the two gives the verdict:

| IV / 1-month historical | Verdict | What it means |
|---|---|---|
| 1.25 or more | **expensive** | the market charges a lot for movement: selling options pays more, buying them costs |
| between 0.90 and 1.25 | **average** | no clear edge |
| 0.90 or less | **cheap** | the stock moves more than options price in: buying them costs little |

The thresholds are not symmetric because IV usually sits **a little above**
historical volatility even in normal times: option sellers ask for a premium for
the risk of sudden moves. And before an expected event, such as earnings, IV rises
on purpose: «expensive» does not mean «wrong».

The **«Position in the year»** box tells on how many days of the last year the
realised volatility was lower than today's IV. The chart shows historical
volatility day by day, the stock price and today's IV.

For indices CBOE provides no history: the ETF that tracks them is used instead
(SPY for the S&P 500, QQQ for the Nasdaq 100, IWM for the Russell 2000). For the
VIX the comparison does not apply: the VIX already is an implied volatility.
""",
    ),
    (
        "appearance",
        "Language, theme and colour",
        """
On the **Settings** page (at the bottom of the sidebar):

- **Language** switches between Italian and English;
- **Theme** switches between automatic (follows Windows), light and dark;
- the **coloured dots** pick the main colour: terracotta, blue, purple, green,
  red or amber. With blue, purple and green the background also turns a cooler
  black (or white) that matches better.

Your choices stay saved in the browser.
""",
    ),
    (
        "limits",
        "The limits: what the simulator does not do",
        """
It is worth being explicit, because the models rest on strong assumptions that do
not hold in reality.

**Constant volatility.** The model assumes volatility is a fixed number. In
reality it changes all the time, and it differs across strikes (the so-called
*skew* or *smile*). Here there is a single IV for the whole position.

**No price jumps.** The model assumes the price moves continuously. Opening gaps
and sudden news do exist, and they are exactly the moments when option sellers
find out what the premium they collected was really worth.

**No transaction costs.** Commissions and the bid-ask spread are not modelled.
They hurt four-leg strategies most, where you pay the spread four times.

**No margin.** Credit positions tie up capital that does not show here.

**Rational exercise.** The tree assumes early exercise happens only when it is
optimal. Real counterparties do not always behave that way.

That is why prices here are **theoretical** and differ from market prices. The
simulator is for understanding *how the variables relate to each other* — what
theta does as expiry approaches, why gamma explodes near the strike, how much a
vol crush weighs. For that it is accurate and useful. For estimating the price at
which you will fill an order, it is not.
""",
    ),
]
