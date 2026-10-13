"""
Generates the visual diagrams used in the submission report and presentation:
  paper/figures/fig_component_architecture.png - System & ETL Process Component Diagram (Page 1 of report)
  Component_Process_Diagram_MS25905854_MS25905922.pdf - Standalone PDF of the Component Diagram
  paper/figures/fig_star_traindelay.png        - Star schema of Fact_TrainDelay (with FK join lines)
  paper/figures/fig_bus_matrix.png             - Enterprise bus matrix (8 events x 8 dimensions)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "paper", "figures")
os.makedirs(OUT, exist_ok=True)

NAVY, TEAL, GOLD, LIGHT = "#1f3a5f", "#2a9d8f", "#e9c46a", "#f4f7fb"


DIMS = {
    "Dim_Date": ["PK DateSK", "FullDate (NK)", "Year", "Quarter, QuarterName", "Month, MonthName", "Day, WeekOfYear",
                 "DayOfWeek", "IsWeekend", "IsHoliday", "HolidayName", "Season"],
    "Dim_Time": ["PK TimeSK", "TimeLabel (NK)", "Hour24", "Minute", "TimeOfDayBand", "IsPeakHour"],
    "Dim_Station": ["PK StationSK", "StationCode (NK)", "StationName", "ZoneCode", "ZoneName"],
    "Dim_Train (SCD2)": ["PK TrainSK", "TrainNumber (NK)", "TrainName", "TrainTypeCode", "TrainTypeName",
                         "ServiceClass", "EffectiveStartDate", "EffectiveEndDate", "IsCurrent"],
    "Dim_DelayCategory": ["PK DelayCatSK", "CategoryName", "MinDelayMinutes", "MaxDelayMinutes"],
}
FACT = ["PK FactID", "FK DateSK", "FK TimeSK", "FK StationSK", "FK TrainSK", "FK DelayCatSK",
        "StopSequence (DD)", "DelayMinutes (Raw)", "TripCount (Derived)", "IsDelayed (Derived)",
        "PunctualFlag (Derived)", "SevereDelayFlag (Derived)", "ExcessDelayMinutes (Derived)"]


def box(ax, x, y, w, title, rows, head_color, row_h=0.32):
    h = (len(rows) + 1) * row_h
    ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0.02", fc=LIGHT, ec=head_color, lw=2))
    ax.add_patch(FancyBboxPatch((x, y - row_h), w, row_h, boxstyle="round,pad=0.02", fc=head_color, ec=head_color))
    ax.text(x + w / 2, y - row_h / 2, title, ha="center", va="center", color="white", fontsize=10, weight="bold")
    for i, r in enumerate(rows):
        ax.text(x + 0.12, y - row_h * (i + 1.5), r, va="center", fontsize=8,
                weight="bold" if r.startswith(("PK", "FK")) else "normal")
    return (x, y - h, w, h)


def star():
    fig, ax = plt.subplots(figsize=(15, 9.5))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9.5)
    ax.axis("off")
    ax.set_title("Star Schema - Fact_TrainDelay (Event 1: Train Arrival at Station)", fontsize=14, weight="bold", color=NAVY)

    fx, fy, fw = 5.6, 8.1, 3.8
    f = box(ax, fx, fy, fw, "Fact_TrainDelay", FACT, NAVY)
    fcx, fcy = fx + fw / 2, f[1] + f[3] / 2

    placements = {
        "Dim_Date": (0.3, 9.1, 3.3),
        "Dim_Time": (0.3, 4.4, 3.3),
        "Dim_Station": (11.3, 9.1, 3.4),
        "Dim_Train (SCD2)": (11.3, 6.2, 3.4),
        "Dim_DelayCategory": (5.6, 2.7, 3.8),
    }
    for name, (x, y, w) in placements.items():
        b = box(ax, x, y, w, name, DIMS[name], TEAL)
        bx = b[0] + b[2] if x < fx else b[0]
        if name == "Dim_DelayCategory":
            sx, sy, tx, ty = fcx, f[1], b[0] + b[2] / 2, b[1] + b[3]
        else:
            sx, sy = (fx if x < fx else fx + fw), fcy + (0.9 if name in ("Dim_Date", "Dim_Station") else -0.9)
            tx, ty = bx, b[1] + b[3] / 2
        ax.annotate("", xy=(tx, ty), xytext=(sx, sy), arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=2.2))
        ax.text((sx + tx) / 2, (sy + ty) / 2 + 0.14, "N : 1", fontsize=8.5, color=NAVY, weight="bold")
    ax.text(0.3, 0.25, "PK = Surrogate Primary Key | FK = Surrogate Foreign Key | NK = Natural Key | DD = Degenerate Dimension",
            fontsize=9, color=NAVY, weight="bold")
    fig.savefig(os.path.join(OUT, "fig_star_traindelay.png"), dpi=180, bbox_inches="tight")
    plt.close(fig)


def bus():
    dims = ["Dim_Date", "Dim_Time", "Dim_Station", "Dim_Train", "Dim_DelayCategory",
            "Dim_Weather", "Dim_DelayReason", "Dim_CancellationReason"]
    events = [
        ("1  Train arrival delay", "Fact_TrainDelay", {"Dim_Date", "Dim_Time", "Dim_Station", "Dim_Train", "Dim_DelayCategory"}),
        ("2  Scheduled stop", "Fact_TrainSchedule", {"Dim_Time", "Dim_Station", "Dim_Train"}),
        ("3  Journey departure", "Fact_JourneyDeparture", {"Dim_Date", "Dim_Time", "Dim_Station", "Dim_Train", "Dim_DelayCategory"}),
        ("4  Journey arrival", "Fact_JourneyArrival", {"Dim_Date", "Dim_Time", "Dim_Station", "Dim_Train", "Dim_DelayCategory"}),
        ("5  Journey cancellation", "Fact_JourneyCancellation", {"Dim_Date", "Dim_Station", "Dim_Train", "Dim_CancellationReason"}),
        ("6  Delay incident", "Fact_DelayIncident", {"Dim_Date", "Dim_Station", "Dim_Train", "Dim_DelayCategory", "Dim_DelayReason"}),
        ("7  Weather observation", "Fact_WeatherObservation", {"Dim_Date", "Dim_Station", "Dim_Train", "Dim_Weather"}),
        ("8  Daily train snapshot", "Fact_TrainDailySnapshot", {"Dim_Date", "Dim_Train"}),
    ]
    fig, ax = plt.subplots(figsize=(17, 6.8))
    ax.axis("off")
    ax.set_xlim(0, len(dims)*1.45 + 4.4)
    ax.set_ylim(0, len(events) + 1.5)
    ax.set_title("Enterprise Bus Matrix - 8 Business Events x 8 Conformed Dimensions", fontsize=14, weight="bold", color=NAVY)
    top = len(events) + 0.8
    for j, d in enumerate(dims):
        ax.text(4.4 + j*1.45 + 0.7, top, d.replace("Dim_", "Dim_\n"), ha="center", va="center", fontsize=8.5,
                weight="bold", color="white", bbox=dict(boxstyle="round,pad=0.35", fc=TEAL, ec=TEAL))
    for i, (ev, fact, used) in enumerate(events):
        y = top - 1 - i
        ax.add_patch(Rectangle((0, y - 0.45), len(dims)*1.45 + 4.4, 0.9, fc=LIGHT if i % 2 == 0 else "white", ec="#d8e2ef", lw=0.6))
        ax.text(0.12, y, ev, va="center", fontsize=9.5, weight="bold", color=NAVY)
        ax.text(2.35, y, fact, va="center", fontsize=8.5, color="#333")
        for j, d in enumerate(dims):
            if d in used:
                ax.text(4.4 + j*1.45 + 0.7, y, "X", ha="center", va="center", fontsize=12, weight="bold", color=NAVY)
    fig.savefig(os.path.join(OUT, "fig_bus_matrix.png"), dpi=180, bbox_inches="tight")
    plt.close(fig)


def component_diagram():
    """Renders the complete end-to-end Process & Component Architecture Diagram
    (aligned with 5 CSV sources, 4 ETL phases, 8 Facts, 8 Conformed Dimensions, and 5 KPI views)."""
    fig, ax = plt.subplots(figsize=(16, 20))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 20)
    ax.axis("off")

    def group_box(x, y, w, h, title, fc="#fcfbf4", ec="#8c7a3e", title_bg="#1f3a5f"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=fc, ec=ec, lw=1.8))
        ax.add_patch(FancyBboxPatch((x + 0.15, y + h - 0.55), w - 0.3, 0.45,
                                    boxstyle="round,pad=0.03", fc=title_bg, ec=title_bg))
        ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="center",
                color="white", fontsize=10.5, weight="bold")

    def node_box(x, y, w, h, lines, fc="white", ec="#333", fontsize=8.3, bold_first=True):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=fc, ec=ec, lw=1.3))
        n = len(lines)
        for idx, line in enumerate(lines):
            ly = y + h - (idx + 0.7) * (h / (n + 0.4))
            ax.text(x + w / 2, ly, line, ha="center", va="center",
                    fontsize=fontsize,
                    weight="bold" if (bold_first and idx == 0) else "normal",
                    color="#1a1a1a")

    def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#1f3a5f", lw=1.8, mutation_scale=14))
        if label:
            tx = lx if lx is not None else (x1 + x2) / 2
            ty = ly if ly is not None else (y1 + y2) / 2
            ax.text(tx, ty, label, ha="center", va="center", fontsize=8, weight="bold",
                    color="#1f3a5f", bbox=dict(boxstyle="round,pad=0.2", fc="#eef4fa", ec="#1f3a5f", lw=0.8))

    # Header banner with Student IDs (matching the user's uploaded PDF header)
    ax.add_patch(FancyBboxPatch((0.6, 18.85), 14.8, 0.95, boxstyle="round,pad=0.05", fc="#263849", ec="#1f3a5f", lw=2))
    ax.text(1.0, 19.48, "MS25905854  |  MS25905922  —  Group 19", fontsize=13, weight="bold", color="#5bc0be")
    ax.text(1.0, 19.08, "Indian Railways Data Warehouse — End-to-End Process & Component Architecture (8 Business Events × 8 Conformed Dimensions)",
            fontsize=10.5, weight="bold", color="white")

    # 1. RAW DATA SOURCE LAYER (y: 15.9 -> 18.6)
    group_box(0.6, 15.9, 14.8, 2.7, "1. Raw Operational Data Sources (Host Storage — 5 CSV Feeds)", fc="#faf9f0", ec="#b5a66b")
    node_box(0.9, 17.05, 4.5, 0.9, ["combined_delay.csv", "38,428,703 rows (1.02 GB)", "Station Arrival Delay Telemetry"], fc="#fff", ec=NAVY)
    node_box(5.75, 17.05, 4.5, 0.9, ["combined_schedule.csv", "172,112 rows", "Master Train Timetable & Distances"], fc="#fff", ec=NAVY)
    node_box(10.6, 17.05, 4.5, 0.9, ["train_delays.csv", "30 Operational Journey Records", "Cancellations, Delay Causes & Weather"], fc="#fff", ec=NAVY)
    node_box(2.5, 16.05, 5.0, 0.82, ["station_full_names.csv (8,963 stations)", "Station Code, Name, Zone (Street Address Stripped)"], fc="#fff", ec=TEAL)
    node_box(8.5, 16.05, 5.0, 0.82, ["train_details.csv (8,992 train records)", "Train Number, Name, Type -> SCD Type 2 Source"], fc="#fff", ec=TEAL)

    # Arrow Layer 1 -> Layer 2
    arrow(8.0, 15.9, 8.0, 15.1, "Streaming CSV Ingestion (250K rows/chunk) + Data Quality Cleansing", lx=8.0, ly=15.5)

    # 2. PYTHON ETL & VALIDATION ENGINE (y: 11.4 -> 15.1)
    group_box(0.6, 11.4, 14.8, 3.7, "2. Python ETL & Automated Validation Engine (etl/)", fc="#f4f8fb", ec=TEAL, title_bg=TEAL)
    node_box(5.8, 13.85, 4.4, 0.58, ["etl/run_etl.py — Master Pipeline Orchestrator"], fc="#e6f4f1", ec=TEAL)

    node_box(0.85, 12.45, 3.4, 1.1, [
        "Phase 1: load_dimensions.py",
        "• Dim_Date (Holidays/Weekends/Seasons)",
        "• Dim_Time (1,440 mins + Peak Band)",
        "• Dim_Station (Zone Hierarchy, No Bloat)",
        "• Dim_Train (SCD Type 2: Start/End/Current)"
    ], fc="white", ec=NAVY, fontsize=7.6)

    node_box(4.5, 12.45, 3.55, 1.1, [
        "Phase 2: load_fact.py",
        "• Events 1–4 Streaming Loader",
        "• Surrogate Key Hash-Map Lookup",
        "• 5 Derived Measures Computed",
        "• Outlier (>1440m) & Null Filtering"
    ], fc="white", ec=NAVY, fontsize=7.6)

    node_box(8.3, 12.45, 3.45, 1.1, [
        "Phase 3: load_event_facts.py",
        "• Event 5: Fact_JourneyCancellation",
        "• Event 6: Fact_DelayIncident",
        "• Event 7: Fact_WeatherObservation",
        "• Event 8: Fact_TrainDailySnapshot"
    ], fc="white", ec=NAVY, fontsize=7.6)

    node_box(12.0, 12.45, 3.15, 1.1, [
        "Phase 4: validate_load.py",
        "• 68/68 Automated Checks",
        "• Source-to-Fact Reconciliation",
        "• SCD2 Validity & Grain Checks",
        "• 100% FK Referential Integrity"
    ], fc="white", ec=NAVY, fontsize=7.6)

    node_box(4.8, 11.55, 6.4, 0.62, [
        "etl/db_connector.py & etl/common.py",
        "SQLAlchemy Pool + LOAD DATA LOCAL INFILE Bulk TSV Loader + Verbose Descriptor Maps"
    ], fc="#eef4fa", ec=NAVY, fontsize=8.0)

    for tx in (2.55, 6.27, 10.02, 13.57):
        arrow(8.0, 13.85, tx, 13.55)
        arrow(tx, 12.45, 8.0, 12.17)

    # Arrow Layer 2 -> Layer 3
    arrow(8.0, 11.4, 8.0, 10.55, "MySQL Protocol / TCP Port 3306 (Bulk TSV Load & Schema Validation)", lx=8.0, ly=10.98)

    # 3. DOCKER COMPOSE RUNTIME (y: 3.4 -> 10.55)
    group_box(0.6, 3.4, 14.8, 7.15, "3. Docker Compose Execution Runtime (MySQL 8.0 OLAP DW + Metabase BI)", fc="#fdf8f3", ec="#c88a4b", title_bg="#1f3a5f")

    # 3A. MySQL OLAP Data Warehouse (left/center sub-box)
    group_box(0.9, 3.7, 9.6, 6.15, "OLAP Data Warehouse Container (railway_dw_mysql — Port 3306)", fc="#f4f7fb", ec=NAVY, title_bg=NAVY)

    node_box(1.15, 8.45, 2.9, 0.72, ["01_create_database.sql", "UTF8MB4 Schema Init"], fc="white", ec=NAVY, fontsize=7.8)
    node_box(4.25, 8.45, 2.9, 0.72, ["02_create_star_schema.sql", "8 Facts + 8 Conformed Dims"], fc="white", ec=NAVY, fontsize=7.8)
    node_box(7.35, 8.45, 2.9, 0.72, ["03_indexes_and_views.sql", "Composite Indexes & 4 Views"], fc="white", ec=NAVY, fontsize=7.8)

    # Fact Constellation sub-panel
    group_box(1.15, 4.65, 9.1, 3.6, "Kimball Fact Constellation / Multi-Star Schema (railway_dw)", fc="#ffffff", ec=TEAL, title_bg=TEAL)

    node_box(1.35, 5.75, 4.25, 1.85, [
        "8 Business Event Fact Tables (Surrogate FKs)",
        "1. Fact_TrainDelay (Arrival + 5 Derived Measures)",
        "2. Fact_TrainSchedule (Dwell & Segment Km)",
        "3. Fact_JourneyDeparture (Origin Stop 1)",
        "4. Fact_JourneyArrival (Destination Terminus)",
        "5. Fact_JourneyCancellation  6. Fact_DelayIncident",
        "7. Fact_WeatherObservation   8. Fact_TrainDailySnapshot"
    ], fc="#eef4fa", ec=NAVY, fontsize=7.0)

    node_box(5.8, 5.75, 4.25, 1.85, [
        "8 Conformed Dimensions (Surrogate PK + NK)",
        "1. Dim_Date (Year>Quarter>Month>Day, Holiday, Season)",
        "2. Dim_Time (TimeOfDayBand>Hour24>Minute, Peak)",
        "3. Dim_Station (ZoneName>StationName; No Address)",
        "4. Dim_Train (SCD Type 2: StartDate, EndDate, Current)",
        "5. Dim_DelayCategory (4 Bands)   6. Dim_Weather",
        "7. Dim_DelayReason               8. Dim_CancellationReason"
    ], fc="#e6f4f1", ec=TEAL, fontsize=6.9)

    node_box(1.35, 4.75, 4.25, 0.85, [
        "Composite B-Tree OLAP Indexes",
        "idx_fact_date_station, idx_fact_train_cat,",
        "idx_fact_time, idx_sched_train"
    ], fc="#fff9e6", ec="#b58900", fontsize=7.1)

    node_box(5.8, 4.75, 4.25, 0.85, [
        "Analytical & 5 KPI SQL Views",
        "vw_RailwayAnalytics, vw_KPI_Monthly,",
        "vw_KPI_WeekendUplift, vw_KPI_PeakSurge"
    ], fc="#fff9e6", ec="#b58900", fontsize=7.1)

    node_box(3.3, 3.85, 4.8, 0.65, [
        "Docker Named Volume: mysql_dw_data (/var/lib/mysql)",
        "Persistent Storage for All 16 Warehouse Tables & Indexes"
    ], fc="#e9ecef", ec=NAVY, fontsize=7.5)

    # 3B. Metabase BI Container (right sub-box)
    group_box(10.85, 3.7, 4.25, 6.15, "BI Engine (railway_bi_metabase :3000)", fc="#f9f5ff", ec="#5a3e85", title_bg="#5a3e85")
    node_box(11.15, 8.2, 3.65, 0.85, ["HTTP Interface: Port 3000", "Interactive Dashboard Server"], fc="white", ec="#5a3e85", fontsize=7.8)
    node_box(11.15, 6.8, 3.65, 1.05, ["Metabase Native SQL Runner", "Queries Star Schema &", "vw_KPI_* Views via JDBC"], fc="white", ec="#5a3e85", fontsize=7.8)
    node_box(11.15, 5.4, 3.65, 1.05, ["Adaptive Query Cache &", "Application Metadata DB", "(metabase_db in MySQL)"], fc="white", ec="#5a3e85", fontsize=7.8)
    arrow(12.97, 8.2, 12.97, 7.85)
    arrow(12.97, 6.8, 12.97, 6.45)

    # Internal Docker Bridge arrow between Metabase and MySQL
    arrow(10.85, 4.25, 10.5, 4.25, "JDBC :3306", lx=10.67, ly=4.68)

    # 4. CLIENT, KPI & PRESENTATION LAYER (y: 0.4 -> 2.75)
    group_box(0.6, 0.4, 14.8, 2.35, "4. Presentation, KPI Scorecard & Automated Submission Layer", fc="#faf9f0", ec="#b5a66b", title_bg=NAVY)

    node_box(0.9, 0.65, 4.6, 1.35, [
        "5 Standardized KPIs (4 Mandatory Properties)",
        "K1: Punctuality Rate (>=75%) | K2: Severe Delay (<=10%)",
        "K3: Excess Delay (<=10m) | K4: Weekend Uplift (<=5%)",
        "K5: Peak Surge (<=10%) + Green/Amber/Red + MoM Trend"
    ], fc="white", ec=NAVY, fontsize=7.6)

    node_box(5.8, 0.65, 4.5, 1.35, [
        "Automated Submission & Diagram Generators",
        "• generate_submission_docx.py (Word + Markdown Spec)",
        "• generate_model_diagrams.py (Bus Matrix & Star Schema)",
        "• 100% KPI-to-Fact Column Traceability Matrix"
    ], fc="white", ec=TEAL, fontsize=7.6)

    node_box(10.6, 0.65, 4.5, 1.35, [
        "Interactive BI & Viva Verification Suite",
        "• Metabase Web UI (http://localhost:3000)",
        "• Power BI DAX Library (bi_reports/dax_measures.txt)",
        "• scripts/run_viva_queries.py & Validation Report"
    ], fc="white", ec="#5a3e85", fontsize=7.6)

    arrow(5.7, 3.7, 3.2, 2.0, "KPI Views", lx=4.2, ly=3.05)
    arrow(7.8, 3.7, 8.05, 2.0, "Direct SQL Query", lx=8.05, ly=3.05)
    arrow(12.95, 3.7, 12.85, 2.0, "HTTP REST / JSON", lx=12.9, ly=3.05)

    png_path = os.path.join(OUT, "fig_component_architecture.png")
    pdf_path = os.path.join(ROOT, "Component_Process_Diagram_MS25905854_MS25905922.pdf")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    star()
    bus()
    component_diagram()
    print("Diagrams written to", OUT)
