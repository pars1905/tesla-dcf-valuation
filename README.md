![Banner](banner.png)

# 📊 Tesla (TSLA) — DCF Valuation Model

> Comprehensive Discounted Cash Flow (DCF) valuation of Tesla, Inc. with revenue projections, WACC calculation, terminal value estimation, and sensitivity analysis.

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python) ![pandas](https://img.shields.io/badge/pandas-2.0-150458?logo=pandas) ![numpy](https://img.shields.io/badge/numpy-statistical-013243?logo=numpy) ![Status](https://img.shields.io/badge/status-completed-brightgreen)

---

## 📌 Project Overview

This project builds a complete intrinsic value DCF model for Tesla, Inc. (NASDAQ: TSLA), forecasting free cash flows from 2024–2029, applying a weighted average cost of capital (WACC), and computing terminal value to derive an implied share price. The model includes a two-dimensional sensitivity analysis on WACC and terminal growth assumptions.

**Key Questions:**
- What is Tesla's intrinsic value based on fundamental cash flow projections?
- How sensitive is the valuation to changes in WACC and terminal growth rate?
- Is Tesla undervalued or overvalued relative to current market price?

---

## 🧮 Model Methodology

| Step | Description |
|---|---|
| 1. Revenue Forecast | Project Tesla revenue 2024–2029 based on growth assumptions |
| 2. Operating Margin | Apply EBIT margin to derive operating income |
| 3. Tax & D&A | Calculate NOPAT, add back depreciation & amortization |
| 4. CapEx & Working Capital | Subtract investments to derive Free Cash Flow (FCF) |
| 5. WACC Calculation | Cost of Equity (CAPM) + Cost of Debt, weighted |
| 6. Discount FCF | Bring projected FCFs to present value |
| 7. Terminal Value | Apply Gordon Growth Model |
| 8. Enterprise Value | Sum PV of FCFs + PV of Terminal Value |
| 9. Equity Value | Subtract net debt, divide by shares outstanding |
| 10. Sensitivity Analysis | Vary WACC & terminal growth, observe implied price |

---

## 📊 Visualizations

### Free Cash Flow Projections (2024–2029)
![FCF Projections](fcf_projections.png)

### Sensitivity Analysis — WACC vs Terminal Growth
![Sensitivity](sensitivity_table.png)

### Valuation Waterfall
![Waterfall](valuation_waterfall.png)

---

## 🔍 Key Findings

1. **Implied Share Price: $285** vs. market price of ~$245 → **+16.3% upside**
2. **WACC: 9.8%** based on CAPM (β = 2.3, Risk-free 4.2%, ERP 5.5%) and effective debt cost
3. **Terminal Value represents ~62%** of total enterprise value (typical for growth companies)
4. **Sensitivity Analysis:** Price ranges from $210 (WACC 11%, g 2%) to $365 (WACC 8.5%, g 3.5%)
5. **Conclusion:** Tesla appears **moderately undervalued** under base-case assumptions; valuation highly sensitive to terminal growth rate

---

## 🧾 Key Assumptions

| Assumption | Value |
|---|---|
| Revenue CAGR (2024–2029) | 18% |
| EBIT Margin (Terminal) | 14% |
| Tax Rate | 21% |
| WACC | 9.8% |
| Terminal Growth Rate | 2.5% |
| Shares Outstanding | 3.18 B |
| Net Debt | -$15 B (net cash position) |

---

## 🛠️ Tools & Libraries

- **Python 3.10** · **pandas** · **numpy**
- **matplotlib** · **seaborn** — visualization
- **Google Colab** — cloud notebook environment

---

## 📁 Repository Structure

```
tesla-dcf-valuation/
├── tesla_dcf_analysis.ipynb        ← Main DCF notebook
├── fcf_projections.png             ← FCF projection chart
├── sensitivity_table.png           ← WACC × growth sensitivity
├── valuation_waterfall.png         ← Enterprise value waterfall
├── banner.png
└── README.md
```

---

## ⚠️ Disclaimer

This analysis is for **educational and portfolio purposes only**. The DCF model relies on forward-looking assumptions that may not reflect Tesla's actual future performance. Not investment advice.

---

## 👤 Author

**Osman Manay** — Applied Economist & Financial Analyst  
[LinkedIn](https://linkedin.com/in/osman-manay-48b3171ba) · [GitHub](https://github.com/pars1905)

---

*Financial modeling portfolio · DCF · LBO · Comparable Analysis*
