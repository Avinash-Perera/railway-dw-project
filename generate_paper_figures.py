#!/usr/bin/env python3
"""
generate_paper_figures.py
=========================
Generates 4 publication-quality PNG figures for the IEEE research paper:
  "A Multidimensional Data Warehouse and Trend Analytics Framework for
   Railway Transit Delay Dynamics: A Case Study of Indian Railways"

Reads directly from the live MySQL `railway_dw` data warehouse.
Output: paper/figures/figure1_*.png ... figure4_*.png
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connector import get_engine

# ─────────────────────────────────────────────────────────────────────────────
# Style configuration
# ─────────────────────────────────────────────────────────────────────────────
FIGURES_DIR = os.path.join(PROJECT_ROOT, 'paper', 'figures')
os.makedirs(FIGURES_DIR, exist_ok=True)

# Publication-quality style
plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.6,
    'legend.framealpha': 0.9,
    'legend.fontsize': 10,
})

# Colour palette matching IEEE publication aesthetics
PALETTE = {
    'on_time':    '#2ecc71',   # green
    'minor':      '#f39c12',   # amber
    'moderate':   '#e67e22',   # orange
    'severe':     '#c0392b',   # red
    'primary':    '#2c3e50',
    'accent':     '#2980b9',
    'highlight':  '#e74c3c',
    'weekend':    '#8e44ad',
    'weekday':    '#2980b9',
}


def connect():
    print("[+] Connecting to railway_dw …")
    engine = get_engine()
    return engine


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 – Delay Severity Distribution (Pie / Donut)
# ─────────────────────────────────────────────────────────────────────────────
def figure1_delay_severity_pie(engine):
    print("[1/4] Generating Figure 1 – Delay Severity Distribution …")
    sql = """
        SELECT d.CategoryName, COUNT(f.FactID) AS TripCount
        FROM Fact_TrainDelay f
        JOIN Dim_DelayCategory d ON f.DelayCatSK = d.DelayCatSK
        GROUP BY d.DelayCatSK, d.CategoryName
        ORDER BY d.DelayCatSK;
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    total = df['TripCount'].sum()
    df['Pct'] = df['TripCount'] / total * 100

    colors = [PALETTE['on_time'], PALETTE['minor'], PALETTE['moderate'], PALETTE['severe']]
    explode = [0.03, 0.03, 0.03, 0.06]

    fig, ax = plt.subplots(figsize=(8, 7))
    wedges, texts, autotexts = ax.pie(
        df['TripCount'],
        labels=None,
        colors=colors,
        explode=explode,
        autopct='%1.1f%%',
        startangle=140,
        pctdistance=0.78,
        wedgeprops={'linewidth': 1.5, 'edgecolor': 'white', 'width': 0.55}
    )
    for at in autotexts:
        at.set_fontsize(12)
        at.set_fontweight('bold')
        at.set_color('white')

    # Centre annotation
    ax.text(0, 0, f'{total/1e6:.2f}M\nTotal Trips',
            ha='center', va='center', fontsize=13, fontweight='bold', color=PALETTE['primary'])

    legend_labels = [f"{row['CategoryName']}  ({row['Pct']:.1f}%,  {row['TripCount']:,})"
                     for _, row in df.iterrows()]
    ax.legend(wedges, legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.12),
              ncol=2, frameon=True, fontsize=10)

    ax.set_title(
        'Figure 1: Distribution of Train Trips Across Delay Severity Categories\n'
        'Indian Railways — 38.32M Fact Records, 2024–2026',
        fontsize=12, fontweight='bold', pad=18, color=PALETTE['primary']
    )
    ax.axis('equal')

    out = os.path.join(FIGURES_DIR, 'figure1_delay_severity_pie.png')
    fig.savefig(out)
    plt.close(fig)
    print(f"    ✅ Saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 – Top 10 Bottleneck Stations (Horizontal Bar)
# ─────────────────────────────────────────────────────────────────────────────
def figure2_top10_bottleneck_stations(engine):
    print("[2/4] Generating Figure 2 – Top 10 Bottleneck Stations …")
    sql = """
        SELECT s.StationName,
               SUM(f.DelayMinutes) AS TotalDelayMins,
               COUNT(f.FactID)     AS TripCount,
               AVG(f.DelayMinutes) AS AvgDelayMins
        FROM Fact_TrainDelay f
        JOIN Dim_Station s ON f.StationSK = s.StationSK
        WHERE f.IsDelayed = 1
        GROUP BY s.StationSK, s.StationName
        ORDER BY TotalDelayMins DESC
        LIMIT 10;
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    df = df.sort_values('TotalDelayMins', ascending=True)
    df['TotalDelayHrs'] = df['TotalDelayMins'] / 60
    df['AvgDelayMins']  = df['AvgDelayMins'].round(1)

    # Truncate long names
    df['Label'] = df['StationName'].apply(lambda x: x[:30] if len(x) > 30 else x)

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = [plt.cm.Reds_r(i / len(df)) for i in range(len(df))]
    colors = list(reversed([plt.cm.YlOrRd(0.3 + 0.7 * i / len(df)) for i in range(len(df))]))

    bars = ax.barh(df['Label'], df['TotalDelayHrs'], color=colors, height=0.65,
                   edgecolor='white', linewidth=0.8)

    # Data labels
    for bar, (_, row) in zip(bars, df.iterrows()):
        w = bar.get_width()
        ax.text(w + w * 0.01, bar.get_y() + bar.get_height() / 2,
                f"  {w:,.0f} hrs  (avg {row['AvgDelayMins']}m/trip)",
                va='center', ha='left', fontsize=9, color=PALETTE['primary'])

    ax.set_xlabel('Cumulative Delay (Hours)', fontsize=11, labelpad=8)
    ax.set_title(
        'Figure 2: Top 10 Railway Bottleneck Stations by Cumulative Delay Hours\n'
        'Indian Railways — Delayed Trips Only, 2024–2026',
        fontsize=12, fontweight='bold', pad=14, color=PALETTE['primary']
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.set_xlim(0, df['TotalDelayHrs'].max() * 1.22)
    ax.grid(axis='x', alpha=0.35)
    ax.grid(axis='y', alpha=0)

    out = os.path.join(FIGURES_DIR, 'figure2_top_10_bottleneck_stations.png')
    fig.savefig(out)
    plt.close(fig)
    print(f"    ✅ Saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 – Monthly Average Delay Trajectory (Line Chart)
# ─────────────────────────────────────────────────────────────────────────────
def figure3_monthly_delay_trajectory(engine):
    print("[3/4] Generating Figure 3 – Monthly Delay Trajectory …")
    sql = """
        SELECT d.Year, d.Month, d.MonthName,
               AVG(f.DelayMinutes) AS AvgDelay,
               SUM(f.DelayMinutes) AS TotalDelay,
               COUNT(f.FactID)     AS TripCount,
               SUM(f.IsDelayed)    AS DelayedCount
        FROM Fact_TrainDelay f
        JOIN Dim_Date d ON f.DateSK = d.DateSK
        GROUP BY d.Year, d.Month, d.MonthName
        ORDER BY d.Year, d.Month;
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    df['PeriodLabel'] = df['MonthName'].str[:3] + " '" + df['Year'].astype(str).str[-2:]
    df['DelayRate']   = df['DelayedCount'] / df['TripCount'] * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), sharex=True,
                                    gridspec_kw={'height_ratios': [3, 1.2]})

    # ── Top: Avg delay line ──
    ax1.fill_between(df.index, df['AvgDelay'], alpha=0.15, color=PALETTE['accent'])
    ax1.plot(df.index, df['AvgDelay'], marker='o', markersize=5,
             linewidth=2.2, color=PALETTE['accent'], label='Avg Delay (minutes)')

    # Moving average
    if len(df) >= 3:
        ma = df['AvgDelay'].rolling(3, center=True).mean()
        ax1.plot(df.index, ma, linestyle='--', linewidth=1.8,
                 color=PALETTE['highlight'], alpha=0.8, label='3-Month Moving Avg')

    ax1.set_ylabel('Avg Delay (minutes)', fontsize=11)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.set_title(
        'Figure 3: Monthly Average Train Delay Trajectory (2024–2026)\n'
        'Indian Railways — Trend Analysis of 38.32M Transit Records',
        fontsize=12, fontweight='bold', pad=12, color=PALETTE['primary']
    )

    # Annotate peak month
    peak_idx = df['AvgDelay'].idxmax()
    ax1.annotate(
        f"Peak: {df.loc[peak_idx, 'PeriodLabel']}\n{df.loc[peak_idx, 'AvgDelay']:.1f} min",
        xy=(peak_idx, df.loc[peak_idx, 'AvgDelay']),
        xytext=(peak_idx + 1.5, df.loc[peak_idx, 'AvgDelay'] + 0.5),
        arrowprops=dict(arrowstyle='->', color=PALETTE['highlight'], lw=1.8),
        fontsize=9, color=PALETTE['highlight'], fontweight='bold'
    )

    # ── Bottom: Delay rate bar ──
    ax2.bar(df.index, df['DelayRate'], color=PALETTE['moderate'], alpha=0.75,
            label='% Delayed Trips')
    ax2.set_ylabel('Delay Rate (%)', fontsize=10)
    ax2.set_xticks(df.index)
    ax2.set_xticklabels(df['PeriodLabel'], rotation=45, ha='right', fontsize=8)
    ax2.legend(loc='upper right', fontsize=9)

    plt.tight_layout(h_pad=0.5)

    out = os.path.join(FIGURES_DIR, 'figure3_monthly_delay_trajectory.png')
    fig.savefig(out)
    plt.close(fig)
    print(f"    ✅ Saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 4 – Weekend vs Weekday Delay Dynamics (Grouped Bar)
# ─────────────────────────────────────────────────────────────────────────────
def figure4_weekend_vs_weekday(engine):
    print("[4/4] Generating Figure 4 – Weekend vs Weekday Comparison …")
    sql = """
        SELECT d.IsWeekend,
               dc.CategoryName,
               dc.DelayCatSK,
               COUNT(f.FactID)     AS TripCount,
               AVG(f.DelayMinutes) AS AvgDelay,
               SUM(f.IsDelayed)    AS DelayedCount
        FROM Fact_TrainDelay f
        JOIN Dim_Date          d  ON f.DateSK     = d.DateSK
        JOIN Dim_DelayCategory dc ON f.DelayCatSK = dc.DelayCatSK
        GROUP BY d.IsWeekend, dc.DelayCatSK, dc.CategoryName
        ORDER BY d.IsWeekend, dc.DelayCatSK;
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    df['DayType']  = df['IsWeekend'].map({0: 'Weekday', 1: 'Weekend'})
    df['DelayRate'] = df['DelayedCount'] / df['TripCount'] * 100

    # ── Pivot: trips by day type × category ──
    pivot_trips = df.pivot(index='CategoryName', columns='DayType', values='TripCount').fillna(0)
    pivot_trips = pivot_trips.reindex(['On-Time / Early', 'Minor Delay', 'Moderate Delay', 'Severe Delay'])

    # ── Pivot: avg delay by day type × category ──
    pivot_avg = df.pivot(index='CategoryName', columns='DayType', values='AvgDelay').fillna(0)
    pivot_avg = pivot_avg.reindex(pivot_trips.index)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # Sub-plot 1: Trip Volume Distribution
    x = range(len(pivot_trips))
    w = 0.35
    bars1 = ax1.bar([i - w/2 for i in x], pivot_trips.get('Weekday', [0]*4) / 1e6,
                    width=w, color=PALETTE['weekday'], label='Weekday', edgecolor='white')
    bars2 = ax1.bar([i + w/2 for i in x], pivot_trips.get('Weekend', [0]*4) / 1e6,
                    width=w, color=PALETTE['weekend'], label='Weekend', edgecolor='white')

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(
        ['On-Time', 'Minor\nDelay', 'Moderate\nDelay', 'Severe\nDelay'],
        fontsize=10
    )
    ax1.set_ylabel('Trip Volume (Millions)', fontsize=11)
    ax1.set_title('(a) Trip Volume by Delay Category', fontweight='bold', fontsize=12)
    ax1.legend(fontsize=10)

    for bar in [*bars1, *bars2]:
        h = bar.get_height()
        if h > 0.05:
            ax1.text(bar.get_x() + bar.get_width()/2, h + 0.02,
                     f'{h:.2f}M', ha='center', va='bottom', fontsize=8, color=PALETTE['primary'])

    # Sub-plot 2: Average Delay Comparison
    if 'Weekday' in pivot_avg.columns and 'Weekend' in pivot_avg.columns:
        bars3 = ax2.bar([i - w/2 for i in x], pivot_avg['Weekday'],
                        width=w, color=PALETTE['weekday'], label='Weekday', edgecolor='white')
        bars4 = ax2.bar([i + w/2 for i in x], pivot_avg['Weekend'],
                        width=w, color=PALETTE['weekend'], label='Weekend', edgecolor='white')

        ax2.set_xticks(list(x))
        ax2.set_xticklabels(
            ['On-Time', 'Minor\nDelay', 'Moderate\nDelay', 'Severe\nDelay'],
            fontsize=10
        )
        ax2.set_ylabel('Average Delay (Minutes)', fontsize=11)
        ax2.set_title('(b) Average Delay Duration by Category', fontweight='bold', fontsize=12)
        ax2.legend(fontsize=10)

        for bar in [*bars3, *bars4]:
            h = bar.get_height()
            if h > 0.5:
                ax2.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                         f'{h:.1f}', ha='center', va='bottom', fontsize=8, color=PALETTE['primary'])

    fig.suptitle(
        'Figure 4: Weekday vs. Weekend Train Delay Dynamics\n'
        'Indian Railways — Temporal Behaviour Analysis, 2024–2026',
        fontsize=13, fontweight='bold', y=1.02, color=PALETTE['primary']
    )
    plt.tight_layout()

    out = os.path.join(FIGURES_DIR, 'figure4_weekend_vs_weekday_comparison.png')
    fig.savefig(out)
    plt.close(fig)
    print(f"    ✅ Saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  IEEE Paper Figure Generator — Railway Data Warehouse")
    print("=" * 65)
    engine = connect()

    figure1_delay_severity_pie(engine)
    figure2_top10_bottleneck_stations(engine)
    figure3_monthly_delay_trajectory(engine)
    figure4_weekend_vs_weekday(engine)

    print()
    print("=" * 65)
    print("  ✅  All 4 figures saved to paper/figures/")
    print("=" * 65)


if __name__ == '__main__':
    main()
