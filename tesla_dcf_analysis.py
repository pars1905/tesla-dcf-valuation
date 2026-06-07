"""
Tesla (TSLA) — Comprehensive DCF Valuation Model
Author: Osman Manay  (github.com/pars1905)

Builds a three-scenario discounted cash-flow model for Tesla, Inc.
- Pulls historical financials from yfinance
- Projects 5-year FCFF under Bear / Base / Bull cases
- Discounts at CAPM-derived WACC, adds Gordon-growth terminal value
- Produces investment-banking-style PNG charts and a sensitivity grid
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import yfinance as yf

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Style — investment-banking, minimal, Tesla red accent
# ---------------------------------------------------------------------------
TESLA_RED = "#cc0000"
DARK = "#1a1a1a"
GREY = "#595959"
LIGHT_GREY = "#d9d9d9"
BG = "#ffffff"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "axes.edgecolor": DARK,
    "axes.linewidth": 0.8,
    "axes.labelcolor": DARK,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlecolor": DARK,
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "font.size": 10,
    "xtick.color": DARK,
    "ytick.color": DARK,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "axes.grid": True,
    "grid.color": LIGHT_GREY,
    "grid.linewidth": 0.5,
    "grid.linestyle": "--",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ---------------------------------------------------------------------------
# Model assumptions
# ---------------------------------------------------------------------------
TAX_RATE = 0.21
WACC_BASE = 0.098            # CAPM: 4.2% + 2.3 * 5.5% = 16.85%; corp blended 9.8%
RF = 0.042
BETA = 2.3
ERP = 0.055
TERMINAL_G = 0.025
FORECAST_YEARS = 5

SCENARIOS = {
    "Bear":  {"growth": 0.12, "color": "#8c8c8c"},
    "Base":  {"growth": 0.18, "color": TESLA_RED},
    "Bull":  {"growth": 0.25, "color": "#404040"},
}


@dataclass
class Financials:
    revenue: pd.Series       # historical, descending by date
    ebit: pd.Series
    da: pd.Series
    capex: pd.Series
    wc_change: pd.Series
    net_debt: float
    cash: float
    shares_out: float
    current_price: float


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------
def _row(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for name in candidates:
        if name in df.index:
            return df.loc[name].astype(float)
    return pd.Series(dtype=float)


def fetch_financials(ticker: str = "TSLA") -> Financials:
    """Pull live TSLA financials. Falls back to filed-10-K snapshot offline."""
    try:
        t = yf.Ticker(ticker)
        fin = t.financials
        cf = t.cashflow
        bs = t.balance_sheet
        info = t.info or {}

        revenue = _row(fin, ["Total Revenue", "TotalRevenue"])
        ebit = _row(fin, ["EBIT", "Operating Income", "OperatingIncome"])
        da = _row(cf, [
            "Depreciation And Amortization",
            "Depreciation",
            "Reconciled Depreciation",
        ])
        capex = _row(cf, ["Capital Expenditure", "Capital Expenditures"]).abs()
        wc_change = _row(cf, [
            "Change In Working Capital",
            "Changes In Working Capital",
        ])

        cash_row = _row(bs, ["Cash And Cash Equivalents", "Cash"])
        debt_row = _row(bs, ["Total Debt", "TotalDebt"])
        cash = float(cash_row.iloc[0]) if not cash_row.empty else 0.0
        total_debt = float(debt_row.iloc[0]) if not debt_row.empty else 0.0

        shares_out = float(info.get("sharesOutstanding") or 0) or 3_180_000_000
        current_price = float(info.get("currentPrice")
                              or info.get("regularMarketPreviousClose") or 0.0)

        if revenue.empty:
            raise RuntimeError("yfinance returned empty income statement")

        return Financials(
            revenue=revenue.sort_index(),
            ebit=ebit.sort_index(),
            da=da.sort_index(),
            capex=capex.sort_index(),
            wc_change=wc_change.sort_index() if not wc_change.empty
            else pd.Series(dtype=float),
            net_debt=total_debt - cash,
            cash=cash,
            shares_out=shares_out,
            current_price=current_price,
        )
    except Exception as e:                                # noqa: BLE001
        print(f"      yfinance unavailable ({e.__class__.__name__}); "
              "using filed-10-K snapshot.")
        return Financials(
            revenue=pd.Series(dtype=float),
            ebit=pd.Series(dtype=float),
            da=pd.Series(dtype=float),
            capex=pd.Series(dtype=float),
            wc_change=pd.Series(dtype=float),
            net_debt=-22_185e6,      # 2023 10-K: cash 29.1B − debt 6.9B
            cash=29_094e6,
            shares_out=3_180_000_000,
            current_price=248.50,    # indicative recent close
        )


# ---------------------------------------------------------------------------
# Fallback historical figures (USD millions) — used if yfinance is blocked
# Sources: TSLA 10-K filings 2019-2023
# ---------------------------------------------------------------------------
FALLBACK = pd.DataFrame({
    "year":     [2019, 2020, 2021, 2022, 2023],
    "revenue":  [24578, 31536, 53823, 81462, 96773],
    "ebit":     [  -69,  1994,  6523, 13656,  8891],
    "da":       [ 2154,  2322,  2911,  3747,  4667],
    "capex":    [ 1327,  3157,  6482,  7163,  8898],
    "wc":       [ -349,   181,  -468,  3909,  3408],
}).set_index("year")


def normalize_or_fallback(fin: Financials) -> pd.DataFrame:
    """Return a tidy historical table in USD millions, indexed by year."""
    if fin.revenue.empty or len(fin.revenue) < 3:
        return FALLBACK.copy()

    df = pd.DataFrame({
        "revenue": fin.revenue,
        "ebit": fin.ebit,
        "da": fin.da,
        "capex": fin.capex,
        "wc": fin.wc_change if not fin.wc_change.empty
        else pd.Series(0.0, index=fin.revenue.index),
    })
    df = df.dropna(how="all") / 1e6                       # to USD millions
    df.index = [pd.Timestamp(i).year for i in df.index]
    df.index.name = "year"
    return df.sort_index()


# ---------------------------------------------------------------------------
# DCF engine
# ---------------------------------------------------------------------------
def project_fcff(hist: pd.DataFrame, growth: float,
                 years: int = FORECAST_YEARS) -> pd.DataFrame:
    last_year = int(hist.index.max())
    last = hist.iloc[-1]

    # Operating ratios held constant at trailing-3yr averages
    ebit_margin = (hist["ebit"].tail(3) / hist["revenue"].tail(3)).mean()
    da_pct = (hist["da"].tail(3) / hist["revenue"].tail(3)).mean()
    capex_pct = (hist["capex"].tail(3) / hist["revenue"].tail(3)).mean()
    wc_pct = (hist["wc"].tail(3) / hist["revenue"].tail(3)).mean()

    # Bear/base/bull skew margins — Tesla operating leverage is real but bounded
    margin_adj = {0.12: -0.01, 0.18: 0.0, 0.25: 0.015}.get(round(growth, 2), 0.0)
    capex_adj = {0.12: -0.005, 0.18: 0.0, 0.25: 0.01}.get(round(growth, 2), 0.0)

    # `wc` here is the cash-flow-statement line (positive = WC released cash).
    # FCFF treats incremental investment in WC as a use of cash, so we ADD this.
    rows = []
    rev = float(last["revenue"])
    for i in range(1, years + 1):
        rev *= (1 + growth)
        ebit = rev * (ebit_margin + margin_adj)
        da = rev * da_pct
        capex = rev * (capex_pct + capex_adj)
        dwc_cf = rev * wc_pct
        fcff = ebit * (1 - TAX_RATE) + da - capex + dwc_cf
        rows.append({
            "year": last_year + i,
            "revenue": rev,
            "ebit": ebit,
            "da": da,
            "capex": capex,
            "dwc": dwc_cf,
            "fcff": fcff,
        })
    return pd.DataFrame(rows).set_index("year")


def discount(fcff: pd.Series, wacc: float, g: float) -> dict:
    years = np.arange(1, len(fcff) + 1)
    pv = fcff.values / (1 + wacc) ** years
    terminal = fcff.values[-1] * (1 + g) / (wacc - g)
    pv_terminal = terminal / (1 + wacc) ** years[-1]
    return {
        "pv_explicit": float(pv.sum()),
        "pv_terminal": float(pv_terminal),
        "terminal_value": float(terminal),
        "enterprise_value": float(pv.sum() + pv_terminal),
        "pv_per_year": pv,
    }


def equity_to_price(ev_m: float, fin: Financials) -> dict:
    equity_m = ev_m - fin.net_debt / 1e6
    fair_price = equity_m * 1e6 / fin.shares_out
    upside = (fair_price - fin.current_price) / fin.current_price \
        if fin.current_price else np.nan
    return {
        "equity_value_m": equity_m,
        "fair_price": fair_price,
        "upside": upside,
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def fmt_b(x, _=None):                                    # USD billions
    return f"${x / 1e3:,.0f}B" if abs(x) >= 1e3 else f"${x:,.0f}M"


def chart_fcf_projections(projections: dict, outpath: str):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    for name, proj in projections.items():
        ax.plot(proj.index, proj["fcff"],
                marker="o", linewidth=2.2, markersize=7,
                color=SCENARIOS[name]["color"], label=f"{name} case")
        ax.fill_between(proj.index, 0, proj["fcff"],
                        color=SCENARIOS[name]["color"], alpha=0.06)

    ax.set_title("Tesla — Projected Free Cash Flow to the Firm",
                 loc="left", pad=14)
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("FCFF (USD millions)")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))
    years = sorted({y for p in projections.values() for y in p.index})
    ax.set_xticks(years)
    ax.legend(frameon=False, loc="upper left")
    ax.axhline(0, color=DARK, linewidth=0.6)

    fig.text(0.01, 0.01,
             "Source: TSLA 10-K filings · Author: Osman Manay (github.com/pars1905)",
             fontsize=8, color=GREY, style="italic")
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_sensitivity(sens: pd.DataFrame, current_price: float, outpath: str):
    fig, ax = plt.subplots(figsize=(11, 6.5))

    cmap = sns.light_palette(TESLA_RED, as_cmap=True)
    sns.heatmap(
        sens, annot=True, fmt=".0f", cmap=cmap,
        cbar_kws={"label": "Implied price per share (USD)"},
        linewidths=0.5, linecolor="white", ax=ax,
        annot_kws={"fontsize": 9, "color": DARK, "family": "serif"},
    )
    ax.set_title("Fair-value sensitivity — WACC × terminal growth (Base case)",
                 loc="left", pad=14)
    ax.set_xlabel("Terminal growth rate (g)")
    ax.set_ylabel("WACC")

    if current_price:
        ax.text(0.0, -0.18,
                f"Current TSLA price: ${current_price:,.2f}",
                transform=ax.transAxes, fontsize=10, color=TESLA_RED,
                style="italic", weight="bold")

    fig.text(0.01, 0.01,
             "Gordon-growth terminal · Author: Osman Manay (github.com/pars1905)",
             fontsize=8, color=GREY, style="italic")
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_waterfall(components: dict, outpath: str):
    """Build a bridge: PV explicit FCFF → + PV terminal → − net debt → equity."""
    labels = ["PV of\nexplicit FCFF",
              "PV of\nterminal value",
              "Enterprise\nvalue",
              "Less: net\ndebt",
              "Equity\nvalue"]
    pv_x = components["pv_explicit"]
    pv_tv = components["pv_terminal"]
    ev = components["enterprise_value"]
    net_debt = components["net_debt_m"]
    equity = components["equity_value_m"]

    values = [pv_x, pv_tv, 0, -net_debt, 0]
    cumulative = [0, pv_x, 0, ev, 0]
    bar_heights = [pv_x, pv_tv, ev, -net_debt, equity]
    bar_bottoms = [0, pv_x, 0, ev, 0]
    colors = [TESLA_RED, TESLA_RED, DARK, GREY, DARK]

    fig, ax = plt.subplots(figsize=(11, 6.5))
    for i, (lbl, h, b, c) in enumerate(zip(labels, bar_heights, bar_bottoms, colors)):
        ax.bar(i, h, bottom=b, color=c, edgecolor=DARK, linewidth=0.6, width=0.55)
        top = b + h
        ax.text(i, top + max(bar_heights) * 0.015, fmt_b(top if i in (2, 4) else h),
                ha="center", fontsize=10, weight="bold", color=DARK)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))
    ax.set_ylabel("USD millions")
    ax.set_title("Tesla DCF bridge — Enterprise to equity value (Base case)",
                 loc="left", pad=14)
    ax.axhline(0, color=DARK, linewidth=0.6)

    fig.text(0.01, 0.01,
             "Author: Osman Manay (github.com/pars1905)",
             fontsize=8, color=GREY, style="italic")
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_revenue_ebit(hist: pd.DataFrame, projection: pd.DataFrame, outpath: str):
    fig, ax1 = plt.subplots(figsize=(11, 6.5))

    hist_yr = hist.index.tolist()
    proj_yr = projection.index.tolist()

    ax1.bar(hist_yr, hist["revenue"], color=LIGHT_GREY,
            edgecolor=DARK, linewidth=0.4, label="Revenue (historical)")
    ax1.bar(proj_yr, projection["revenue"], color=TESLA_RED, alpha=0.55,
            edgecolor=DARK, linewidth=0.4, label="Revenue (projected, Base)")
    ax1.set_ylabel("Revenue (USD millions)", color=DARK)
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))

    ax2 = ax1.twinx()
    ax2.plot(hist_yr, hist["ebit"], color=DARK, marker="o",
             linewidth=2, label="EBIT (historical)")
    ax2.plot(proj_yr, projection["ebit"], color=TESLA_RED, marker="o",
             linewidth=2, linestyle="--", label="EBIT (projected)")
    ax2.set_ylabel("EBIT (USD millions)", color=DARK)
    ax2.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))
    ax2.grid(False)

    ax1.set_title("Tesla — Revenue and operating profit (history + Base projection)",
                  loc="left", pad=14)
    ax1.set_xlabel("Fiscal year")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               frameon=False, loc="upper left")

    fig.text(0.01, 0.01,
             "Source: TSLA filings · Author: Osman Manay (github.com/pars1905)",
             fontsize=8, color=GREY, style="italic")
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_dashboard(hist, projections, sens, components, fin, outpath):
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.32)

    # Title
    fig.suptitle("Tesla, Inc. (NASDAQ: TSLA) — DCF Valuation Dashboard",
                 fontsize=18, weight="bold", color=DARK, x=0.07, y=0.97,
                 ha="left", family="serif")
    fig.text(0.07, 0.935,
             "Three-scenario discounted cash-flow model · "
             "Author: Osman Manay (github.com/pars1905)",
             fontsize=10, style="italic", color=GREY)

    # 1. FCFF
    ax1 = fig.add_subplot(gs[0, 0])
    for n, p in projections.items():
        ax1.plot(p.index, p["fcff"], marker="o", linewidth=1.8,
                 color=SCENARIOS[n]["color"], label=n)
    ax1.set_title("Projected FCFF", loc="left")
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))
    fcf_years = sorted({y for p in projections.values() for y in p.index})
    ax1.set_xticks(fcf_years)
    ax1.tick_params(axis="x", labelsize=8)
    ax1.legend(frameon=False, fontsize=8)
    ax1.axhline(0, color=DARK, linewidth=0.5)

    # 2. Revenue history+projection
    ax2 = fig.add_subplot(gs[0, 1])
    base = projections["Base"]
    ax2.bar(hist.index, hist["revenue"], color=LIGHT_GREY,
            edgecolor=DARK, linewidth=0.3)
    ax2.bar(base.index, base["revenue"], color=TESLA_RED, alpha=0.55,
            edgecolor=DARK, linewidth=0.3)
    ax2.set_title("Revenue trajectory (Base)", loc="left")
    ax2.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))

    # 3. Fair value vs current
    ax3 = fig.add_subplot(gs[0, 2])
    names = list(projections.keys())
    prices = [components["scenario_prices"][n] for n in names]
    colors = [SCENARIOS[n]["color"] for n in names]
    bars = ax3.bar(names, prices, color=colors, edgecolor=DARK, linewidth=0.6)
    for b, v in zip(bars, prices):
        ax3.text(b.get_x() + b.get_width() / 2, v * 1.01, f"${v:,.0f}",
                 ha="center", fontsize=10, weight="bold")
    if fin.current_price:
        ax3.axhline(fin.current_price, color=DARK, linestyle="--",
                    linewidth=1.2,
                    label=f"Current ${fin.current_price:,.0f}")
        ax3.legend(frameon=False, fontsize=8)
    ax3.set_title("Implied fair price / share", loc="left")
    ax3.set_ylabel("USD")

    # 4. Sensitivity heatmap
    ax4 = fig.add_subplot(gs[1, 0])
    sns.heatmap(sens, annot=True, fmt=".0f",
                cmap=sns.light_palette(TESLA_RED, as_cmap=True),
                cbar=False, linewidths=0.4, linecolor="white", ax=ax4,
                annot_kws={"fontsize": 7})
    ax4.set_title("Sensitivity: WACC × g (Base)", loc="left")
    ax4.set_xlabel("g"); ax4.set_ylabel("WACC")

    # 5. Waterfall (compact)
    ax5 = fig.add_subplot(gs[1, 1])
    labels = ["PV FCFF", "PV TV", "EV", "−Debt", "Equity"]
    pv_x = components["pv_explicit"]; pv_tv = components["pv_terminal"]
    ev = components["enterprise_value"]; nd = components["net_debt_m"]
    eq = components["equity_value_m"]
    heights = [pv_x, pv_tv, ev, -nd, eq]
    bottoms = [0, pv_x, 0, ev, 0]
    cols = [TESLA_RED, TESLA_RED, DARK, GREY, DARK]
    for i, (h, b, c) in enumerate(zip(heights, bottoms, cols)):
        ax5.bar(i, h, bottom=b, color=c, edgecolor=DARK, linewidth=0.4)
    ax5.set_xticks(range(len(labels))); ax5.set_xticklabels(labels, fontsize=9)
    ax5.set_title("Valuation bridge (Base)", loc="left")
    ax5.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_b))

    # 6. Assumptions table
    ax6 = fig.add_subplot(gs[1, 2]); ax6.axis("off")
    table = [
        ["Risk-free rate", f"{RF:.2%}"],
        ["Beta", f"{BETA:.2f}"],
        ["Equity risk premium", f"{ERP:.2%}"],
        ["WACC", f"{WACC_BASE:.2%}"],
        ["Terminal growth", f"{TERMINAL_G:.2%}"],
        ["Tax rate", f"{TAX_RATE:.2%}"],
        ["Bear / Base / Bull growth", "12% / 18% / 25%"],
        ["Forecast horizon", f"{FORECAST_YEARS} yrs"],
        ["Shares outstanding", f"{fin.shares_out / 1e9:.2f}B"],
        ["Net debt", fmt_b(fin.net_debt / 1e6)],
    ]
    tbl = ax6.table(cellText=table, colLabels=["Assumption", "Value"],
                    loc="center", cellLoc="left", colWidths=[0.55, 0.4])
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.5)
    for (r, _), cell in tbl.get_celld().items():
        cell.set_edgecolor(LIGHT_GREY)
        if r == 0:
            cell.set_facecolor(TESLA_RED)
            cell.set_text_props(color="white", weight="bold")
    ax6.set_title("Model assumptions", loc="left")

    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def build_sensitivity(hist: pd.DataFrame, fin: Financials) -> pd.DataFrame:
    waccs = np.arange(0.085, 0.111, 0.005)
    gs = np.arange(0.020, 0.036, 0.005)
    base_proj = project_fcff(hist, SCENARIOS["Base"]["growth"])
    grid = np.zeros((len(waccs), len(gs)))
    for i, w in enumerate(waccs):
        for j, g in enumerate(gs):
            disc = discount(base_proj["fcff"], w, g)
            equity = equity_to_price(disc["enterprise_value"], fin)
            grid[i, j] = equity["fair_price"]
    return pd.DataFrame(
        grid,
        index=[f"{w:.2%}" for w in waccs],
        columns=[f"{g:.2%}" for g in gs],
    )


def cagr(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 2:
        return float("nan")
    return (s.iloc[-1] / s.iloc[0]) ** (1 / (len(s) - 1)) - 1


def main() -> None:
    print("[1/6] Pulling Tesla financials from yfinance …")
    fin = fetch_financials("TSLA")
    hist = normalize_or_fallback(fin)
    print(f"      Historical years: {hist.index.tolist()}")
    print(f"      Revenue CAGR    : {cagr(hist['revenue']):.2%}")
    print(f"      Current price   : ${fin.current_price:,.2f}")

    print("[2/6] Projecting FCFF under three scenarios …")
    projections = {name: project_fcff(hist, s["growth"])
                   for name, s in SCENARIOS.items()}

    print("[3/6] Discounting cash flows …")
    scenario_results = {}
    for name, proj in projections.items():
        disc = discount(proj["fcff"], WACC_BASE, TERMINAL_G)
        eq = equity_to_price(disc["enterprise_value"], fin)
        scenario_results[name] = {**disc, **eq}
        print(f"      {name:>4s}: EV ${disc['enterprise_value'] / 1e3:,.1f}B"
              f"  → fair price ${eq['fair_price']:,.2f}")

    base = scenario_results["Base"]
    components = {
        "pv_explicit": base["pv_explicit"],
        "pv_terminal": base["pv_terminal"],
        "enterprise_value": base["enterprise_value"],
        "net_debt_m": fin.net_debt / 1e6,
        "equity_value_m": base["equity_value_m"],
        "scenario_prices": {n: r["fair_price"]
                            for n, r in scenario_results.items()},
    }

    print("[4/6] Building sensitivity grid …")
    sens = build_sensitivity(hist, fin)

    print("[5/6] Rendering charts …")
    chart_fcf_projections(projections, "fcf_projections.png")
    chart_sensitivity(sens, fin.current_price, "sensitivity_table.png")
    chart_waterfall(components, "valuation_waterfall.png")
    chart_revenue_ebit(hist, projections["Base"], "revenue_ebit.png")
    chart_dashboard(hist, projections, sens, components, fin,
                    "dcf_dashboard.png")

    print("[6/6] Summary")
    summary = pd.DataFrame({
        n: {
            "EV (USD bn)":        r["enterprise_value"] / 1e3,
            "Equity (USD bn)":    r["equity_value_m"] / 1e3,
            "Fair price (USD)":   r["fair_price"],
            "Upside vs spot":     f"{r['upside']:.1%}"
                                   if not np.isnan(r["upside"]) else "n/a",
        } for n, r in scenario_results.items()
    }).T
    print(summary.to_string())
    summary.to_csv("dcf_summary.csv")
    sens.to_csv("sensitivity_table.csv")
    print("\nArtifacts written: 5 PNGs + 2 CSVs in current directory.")


if __name__ == "__main__":
    main()
