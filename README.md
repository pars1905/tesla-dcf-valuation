# Tesla (TSLA) — DCF Valuation

Three-scenario discounted-cash-flow model for Tesla, Inc.

**Author:** Osman Manay · github.com/pars1905

## Run

```bash
pip install -r requirements.txt
python tesla_dcf_analysis.py
```

The script pulls live financials from `yfinance`; if the network is blocked it
falls back to the 2019–2023 10-K snapshot baked into the script.

## Model

| Input | Value |
|---|---|
| Risk-free rate | 4.20% |
| Beta | 2.30 |
| Equity risk premium | 5.50% |
| WACC | 9.80% |
| Terminal growth (g) | 2.50% |
| Tax rate | 21.0% |
| Forecast horizon | 5 years |
| Revenue growth (Bear / Base / Bull) | 12% / 18% / 25% |

FCFF = EBIT·(1−t) + D&A − CapEx + ΔWC<sub>cash-flow</sub>

Enterprise value = Σ PV(FCFF<sub>1…5</sub>) + PV(Gordon terminal). Equity =
EV − net debt. Per-share fair value = Equity / shares outstanding.

## Outputs

- `fcf_projections.png` — FCFF trajectory across scenarios
- `revenue_ebit.png` — Historical + projected revenue and operating profit
- `valuation_waterfall.png` — EV → equity bridge (Base)
- `sensitivity_table.png` — WACC × g heat-map
- `dcf_dashboard.png` — Single-page summary
- `dcf_summary.csv`, `sensitivity_table.csv` — Tabular outputs
