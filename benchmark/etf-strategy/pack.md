# Blinded idea comparison

Six ideas for the brief below, in random order. Some were written by a multi-agent system and some by a single agent; do not try to guess which. Rate each idea on its own merits, then rank all six. Do not open `key.json` until the table is filled in.

## Brief

Design a rule-based, long-only trading strategy for a universe of 10 liquid ETFs (US large cap, US small cap, developed ex-US, emerging markets, US Treasuries 7-10y, TIPS, investment-grade credit, gold, broad commodities, US REITs). It must trade on at least 3 days per week, keep weekly turnover at or below 20%, and use only daily closing prices. Optimise long-run growth while keeping maximum drawdown below 20% and staying diversified across asset classes.

## Ratings

Score 1 (poor) to 5 (excellent). *Constraints*: how convincingly the idea meets the brief's hard rules (trading days, turnover, daily closes, long only). *Drawdown*: how credible the case for staying under 20 % is. *Growth*, *Diversification*: as named. *Would pursue*: would you spend a week testing this? Rank: 1 = best of the six.

| Idea | Constraints | Drawdown | Growth | Diversification | Would pursue | Rank |
|---|---|---|---|---|---|---|
| A | | | | | | |
| B | | | | | | |
| C | | | | | | |
| D | | | | | | |
| E | | | | | | |
| F | | | | | | |

## Idea A: Multi-horizon trend ensemble with daily partial-step rebalancing

**Pitch.** A continuous trend-strength ensemble scales inverse-volatility risk budgets, and the portfolio tracks the target by moving a fixed fraction of the gap each day under a 4% cap.

**Mechanism.** Target weight t_i proportional to (1/sigma_i) * s_i with s_i = mean over L in {21,63,126,252} of clip(ret_L / (sigma_i * sqrt(L/252)), 0, 1); scale to 8% portfolio vol, cap 100% invested. Daily trade: Delta w = alpha*(t - w), alpha = 0.25, then scale Delta w so one-way turnover <= 4% of NAV.

**Rationale.** Continuous signals and exponential tracking (half-life about 2.4 days at alpha 0.25) minimise whipsaw and spread trades across days, meeting the 3-days-per-week rule naturally while retaining trend protection.

**Assumptions.** Trend strength measured as risk-adjusted return is informative.; Partial tracking lag does not destroy the trend edge.; Cash allowed.

**How it fails.** Tracking lag deepens losses in fast crashes.; In trendless markets the portfolio drifts to low exposure and growth stalls.; Signals correlated across assets during crises reduce diversification.

**Cheapest test.** Same backtest harness as Idea 1; sweep alpha in {0.1, 0.25, 0.5} and plot turnover vs CAGR vs max DD.

**Effort.** Low: about 1 day once Idea 1 harness exists.

**Operational spec.** Trade days: trade whenever gap exceeds 0.05% NAV, which drift makes true on nearly every day; fallback forced trade on Mon/Wed/Fri. Turnover: 4% daily one-way cap gives <= 20% weekly. Caps and class limits as Idea 1; drawdown governor as Idea 1; closes only, execute next close.

## Idea B: Droop-governed 3-bucket risk parity: deadband drawdown droop, 3.5%/day slew ramp, 10% reserve cash

**Pitch.** Equal-risk-bucket inverse-vol portfolio whose exposure follows a deadband droop law on its own drawdown, executed through a 3.5%-per-day slew limit so the turnover and trading-frequency gates are the control dynamics.

**Mechanism.** Buckets: equity-like (LC, SC, DM, EM, REIT), duration/credit (UST, TIPS, IG), real (gold, commodities). Within-bucket weights proportional to 1/sigma_i (63d). Bucket weight proportional to 1/sigma_k, sigma_k = 63d stdev of the bucket's own sub-portfolio, then normalised to 1; standalone risk is equal across buckets by rule. Peak P_t = max NAV over 756 days; DD_t = 1 - NAV_t/P_t. E_t = clip(0.90 - 8*(DD_t - 0.05), 0.25, 0.90). Backstop: E_t <= 0.10 while all-time-peak DD >= 15%. Target w* = E_t*b, cash = 1 - E_t >= 10%. Each day trade at the next close along the gap vector, scaled so one-way turnover <= 3.5% (17.5%/week plus at most ~1.5% drift, under 20%).

**Rationale.** Bucketed risk parity spreads standalone risk over equity, duration and real assets (Qian 2005; Maillard et al. 2010). Drawdown-keyed exposure is CPPI-like and motivated by, not derived from, Grossman-Zhou (1993). The slew limit damps whipsaw.

**Assumptions.** Crashes unfold over 2-3 weeks or more; One-way cost about 5 bp; Cash earns 0 (conservative); Base book vol about 4.5%

**How it fails.** A one-week gap outruns the ramp; A grind of more than 4 years is only stopped by the 15% backstop; Slow re-risking after V-shaped recoveries; Positive stock-bond correlation (2022) hits the duration-heavy base; Net growth only about 3-4%/yr, an unrun estimate

**Cheapest test.** Backtest 2004-2025 on ETF closes (index proxies pre-inception), 1-day lag, 5 bp cost. Report max DD in 2008, 2020 and 2022, the weekly turnover histogram including drift, mean E, and CAGR versus static inverse-vol.

**Effort.** Low: about 100 lines of pandas, one day. Kill if max DD exceeds 20% in any crisis, weekly turnover exceeds 20%, or net CAGR is below cash.

**Operational spec.** Close t: sigma_i, sigma_k, b, P_t, DD_t, E_t, w* = E_t*b (cash = 1 - E_t). Trade at close t+1: g = w* - w over 11 positions incl. cash; T = sum|g|/2; if T > 0.035, g *= 0.035/T. If T < 0.0005, swap 0.0005 from argmin_i to argmax_i of (w*_i - w_i) over the 10 ETFs (cash untouched, always toward target). Ties: lowest ticker index.

## Idea C: Turnover-budgeted fractional-Kelly optimiser

**Pitch.** Each day, solve a log-growth maximisation with shrunk trend forecasts, shrinkage covariance, a volatility ceiling and an explicit 4% daily L1 trade budget.

**Mechanism.** Maximise w'mu - (1/2) w'Sigma w - lambda*||w - w_prev||_1 subject to w >= 0, sum(w) <= 1, sqrt(w'Sigma w) <= 9%, ||w - w_prev||_1 / 2 <= 4%, per-asset and per-class caps. mu_i = k * sigma_i * s_i where s_i is the multi-horizon trend score in [-1,1] and k = 0.3 (a Sharpe of 0.3 per unit signal, deliberately conservative); Sigma is Ledoit-Wolf shrunk from 252 days of returns. Solve with cvxpy daily.

**Rationale.** Mean minus half variance is the second-order approximation to expected log growth, the brief's objective; fractional Kelly via shrunk mu and a vol ceiling curbs estimation error; the L1 penalty and hard trade budget make turnover a first-class constraint.

**Assumptions.** Trend-scaled expected returns carry modest but positive information.; Shrinkage covariance is stable enough week to week.; Convex solver available and deterministic daily.

**How it fails.** Optimiser corner solutions concentrate in 2-3 assets if caps are loose.; Mis-specified mu scaling causes near-full-Kelly risk and drawdowns.; Trade budget binds during regime breaks, slowing de-risking.; Minimum trade-day requirement can fail if lambda suppresses all trades.

**Cheapest test.** Backtest with k in {0.1, 0.3, 0.5} and lambda in {0, 5 bp, 20 bp}; compare CAGR and max DD against Idea 1 and verify trade-days and turnover logs.

**Effort.** Medium: 3-4 days including solver tuning and constraint validation.

**Operational spec.** Trade days: trade on any day with a solved change above 0.05% NAV; if fewer than 3 trades have occurred by Wednesday close, force a minimum 0.2% rebalance toward target on Thursday and Friday. Turnover: rolling 5-day one-way sum capped at 20% as a hard constraint (daily 4%). Diversification: 25% per ETF, class caps as Idea 1, and at least 5 ETFs with weight >= 5%. Drawdown: 9% vol ceiling plus same governor as Idea 1.

## Idea D: Staggered-tranche trend-filtered risk parity with drawdown governor

**Pitch.** Five weekday tranches each rebalance once a week to a trend-filtered, volatility-targeted inverse-volatility portfolio, with a drawdown governor that de-risks as losses approach the 20% limit.

**Mechanism.** Each weekday d, tranche d (20% of NAV) is reset to target weights. Target: raw weight r_i = 1/sigma_i (sigma_i = 63-day EWMA vol) times trend score s_i = average over lookbacks {21,63,126,252} of 1[P_t > P_{t-L}]. Normalise, apply caps, then scale total exposure so ex-ante portfolio vol (EWMA covariance, 63-day halflife) is 8%, capped at 100% invested; remainder in cash. Governor multiplies risky exposure by g = clip(1 - (DD - 0.08)/0.08, 0.5, 1), where DD is drawdown from the high-water mark.

**Rationale.** Risk parity gives balanced exposure to growth, inflation and deflation shocks; trend filters historically cut the deep equity and commodity drawdowns (2008) and the 2022 bond sell-off; volatility targeting stabilises risk, and staggering removes rebalance-day timing luck.

**Assumptions.** Uninvested cash is allowed and earns roughly the T-bill rate.; Trend persistence at 1-12 month horizons continues across asset classes.; EWMA volatility forecasts are adequate one week ahead.; Trading costs are about 2-5 bp per side for these ETFs.

**How it fails.** Sharp V-shaped reversals (2020) cause whipsaw: sold low, re-entered late.; Simultaneous stock-bond drawdown faster than trend lookbacks (early 2022) before filters react.; Low vol target caps growth in long bull markets; underperforms 60/40 in 2010s-style regimes.; Cash-heavy periods cede returns if cash yields near zero.

**Cheapest test.** Backtest 2004-present on the ten ETFs (proxy indices pre-inception) with 5 bp costs; report CAGR, max DD, weekly turnover distribution, trade days per week, and compare to static inverse-vol and 60/40. Then sweep vol target 6-10% and governor thresholds for stability.

**Effort.** Low: about 1-2 days to implement and backtest in pandas; no optimiser required.

**Operational spec.** Universe: 10 ETFs. Data: daily closes only. Caps: 25% per ETF; equities (4) <= 50%, bonds (Treasuries, TIPS, IG) <= 50%, real assets (gold, commodities, REITs) <= 40%; effective N = 1/sum(w^2) >= 4 when invested. Trade days: one tranche per weekday gives 5 trade days/week; holidays skip that tranche. Turnover: each tranche is 20% of NAV so one-way weekly turnover <= 20% by construction; additionally clip any day's trade to 4% one-way NAV. Drawdown: 8% vol target plus governor (full de-risk to 50% at 16% DD) aims at max DD around 12-16%, below 20%. Execution at next close after signal.

## Idea E: Crisis-correlation risk budgeting: stress-day covariance, trend gates, drawdown brake, weekday sleeves

**Pitch.** Budget risk equally across growth, duration and real classes using sell-off-day covariance, cut exposure to cash in downtrends and drawdowns, and trade one of five weekday sleeves daily.

**Mechanism.** A covariance blended from worst-20% days and the full sample lowers weights of assets that co-move in crises. Gate and brake are multiplicative cuts to cash, never renormalised. Staggered sleeves make every trading day trade with turnover headroom.

**Rationale.** Crisis correlation exceeds calm correlation (Longin-Solnik 2001). Trend rules to cash cut drawdowns (Faber 2007; Hurst et al. 2017). Staggering removes rebalance-date luck (Hoffstein et al. 2020). Expected net CAGR 4-5% at 4-5% vol; a 12-16% worst-case drawdown is an untested estimate.

**Assumptions.** Stress-day covariance is a useful crisis proxy despite selection bias; Gate and graded brake cut exposure faster than losses accrue in multi-week sell-offs

**How it fails.** 2020-style crash outruns the 17.5%/week cut speed; Trend whipsaw; Growth risk capped at 1/3 lags equity bull runs; 500-day window lags 2022; only SMA200 reacts fast

**Cheapest test.** Backtest 2008-2025, 5 bp costs, against full-sample covariance and the old renormalising gate. Kill if max drawdown exceeds 18% in 2008, 2020 or 2022, net CAGR is below 2.5%, or stress covariance cuts 2022 drawdown by under 2 points.

**Effort.** 3-4 days

**Operational spec.** Close t: stress set = 100 lowest equal-weight-10 returns in [t-499,t] (ties: earlier). Sigma = 252*(0.5*S_stress about stress mean + 0.5*S_500 zero-mean). Budgets: Growth (US LC, US SC, DM, EM, REIT) 1/15 each; Duration (UST, IG, TIPS) 1/9 each; Real (gold, commodities) 1/6 each. Solve min 0.5y'Sigma y - sum b_i ln y_i (Newton, tol 1e-8); w=y/sum y. v_i = w_i*(0.5 if close<SMA200 else 1); v *= min(1, 5%/s), s = max(sqrt(v'Sigma v), 21-day realised vol of v). Brake: v *= clip(1-(DD-0.03)/0.08, 0.25, 1), DD vs trailing-252-day NAV high. Target T=v, rest cash, no upward renormalisation. Five 20%-NAV sleeves, one per weekday (holiday: skipped). Sleeve at close: g=T-u (u = post-drift sleeve weights); x=g*min(1, 0.35/sum|g|), one-way at most 3.5% NAV. Stop trading once week-to-date turnover incl. drift reaches 19.5%, unless fewer than 3 days have traded.

## Idea F: N-1 contingency reserve: cluster risk parity with stress-memory reserve and asymmetric ramps

**Pitch.** Hold the cash needed to survive a stressed 20-day loss of the largest cluster plus the simulated joint loss; cut risk twice as fast as it is restored.

**Mechanism.** Clusters: Equity (5 ETFs), Duration (3), Real (gold, commodities). Mix u: inverse 63d vol within cluster; ERC across clusters on 63d cluster covariance. Trend: ETFs below 200d SMA have u_i halved, freed weight goes to cash (no renormalisation). Reserve S uses unfiltered u: S = max(max_c u_c L_c + 0.5*sum_others u_c L_c, HS), where HS = |1% quantile of 20d returns of current u, last 1260d|. L_c and HS are floored at half the worst 20d loss since 2004 and at 2.33*sqrt(20)*63d vol. lambda = clip((0.17 - DD)/S, 0, 0.95), DD from trailing 504d NAV peak. Ramps: cut 4%/day, restore 2%/day. Target w* = lambda * filtered u.

**Rationale.** Grid N-1 reserves against the largest outage; here it is CPPI with a measured, stress-floored multiplier (Maillard 2010 ERC; Faber 2007 trend-to-cash). Net growth 3.5-4.5%/yr after 5bp costs.

**Assumptions.** Stress floor plus joint simulation bounds next-month loss within about 3 points; A 2-year peak suffices as drawdown reference; 5bp costs; cash earns 0

**How it fails.** Multi-year grind: rolling peak forgets, so all-time DD can exceed 17% by staircase (conceded); Unprecedented shock beyond twice the historical worst; Stress floor lowers exposure in calm years, costing growth

**Cheapest test.** Backtest 2004-2025, 1-day lag. Log realised 20d portfolio loss vs S (exceedance target <=2%), max DD in 2008, 2020, 2022, and net CAGR. Kill if max DD >20% in any crisis, net CAGR <2.5%, or S exceedance >4%.

**Effort.** Moderate: 2-3 days.

**Operational spec.** Signal at close t, trade at close t+1. g = w* - w incl. cash; T = sum|g|/2. Cap = 0.02 if exposure rising, else 0.04; scale g by min(1, cap/T). Weekly turnover <= 5*0.04 = 0.20. If scaled T < 0.0005, swap 0.0005 from most overweight to most underweight ETF vs w* (ties alphabetical); needs no cash. 5% cash floor via lambda <= 0.95.
