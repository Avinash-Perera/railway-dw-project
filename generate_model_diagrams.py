"""
Generates the model diagrams used in the submission document:
  paper/figures/fig_star_traindelay.png   - star schema of the main fact table (with FK join lines)
  paper/figures/fig_bus_matrix.png        - enterprise bus matrix (8 events x 8 dimensions)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper", "figures")
os.makedirs(OUT, exist_ok=True)

NAVY, TEAL, GOLD, LIGHT = "#1f3a5f", "#2a9d8f", "#e9c46a", "#f4f7fb"

DIMS = {
    "Dim_Date": ["PK DateSK", "FullDate", "Year", "Quarter", "Month", "MonthName", "Day",
                 "DayOfWeek", "IsWeekend", "IsHoliday", "HolidayName", "Season"],
    "Dim_Time": ["PK TimeSK", "TimeLabel", "Hour24", "Minute", "TimeOfDayBand", "IsPeakHour"],
    "Dim_Station": ["PK StationSK", "StationCode (NK)", "StationName", "ZoneCode", "ZoneName"],
    "Dim_Train": ["PK TrainSK", "TrainNumber (NK)", "TrainName", "TrainTypeName", "ServiceClass",
                  "EffectiveStartDate", "EffectiveEndDate", "IsCurrent"],
    "Dim_DelayCategory": ["PK DelayCatSK", "CategoryName", "MinDelayMinutes", "MaxDelayMinutes"],
}
FACT = ["PK FactID", "FK DateSK", "FK TimeSK", "FK StationSK", "FK TrainSK", "FK DelayCatSK",
        "StopSequence (DD)", "DelayMinutes", "TripCount", "IsDelayed", "PunctualFlag",
        "SevereDelayFlag", "ExcessDelayMinutes"]


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
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9)
    ax.axis("off")
    ax.set_title("Star Schema - Fact_TrainDelay (Event 1: train arrival delay)", fontsize=14, weight="bold", color=NAVY)

    fx, fy, fw = 5.8, 7.6, 3.4
    f = box(ax, fx, fy, fw, "Fact_TrainDelay", FACT, NAVY)
    fcx, fcy = fx + fw / 2, f[1] + f[3] / 2

    placements = {
        "Dim_Date": (0.3, 8.7, 3.2),
        "Dim_Time": (0.3, 4.2, 3.2),
        "Dim_Station": (11.3, 8.7, 3.4),
        "Dim_Train": (11.3, 5.6, 3.4),
        "Dim_DelayCategory": (5.8, 2.6, 3.4),
    }
    for name, (x, y, w) in placements.items():
        b = box(ax, x, y, w, name, DIMS[name], TEAL)
        bx = b[0] + b[2] if x < fx else b[0]
        if name == "Dim_DelayCategory":
            sx, sy, tx, ty = fcx, f[1], b[0] + b[2] / 2, b[1] + b[3]
        else:
            sx, sy = (fx if x < fx else fx + fw), fcy + (0.9 if name in ("Dim_Date", "Dim_Station") else -0.9)
            tx, ty = bx, b[1] + b[3] / 2
        ax.annotate("", xy=(tx, ty), xytext=(sx, sy), arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=2))
        ax.text((sx + tx) / 2, (sy + ty) / 2 + 0.12, "N : 1", fontsize=8, color=NAVY, weight="bold")
    ax.text(0.3, 0.3, "PK = surrogate primary key | FK = surrogate foreign key | NK = natural key | DD = degenerate dimension",
            fontsize=9, color=NAVY)
    fig.savefig(os.path.join(OUT, "fig_star_traindelay.png"), dpi=170, bbox_inches="tight")
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
    fig, ax = plt.subplots(figsize=(17, 6.5))
    ax.axis("off")
    ax.set_xlim(0, len(dims)*1.45 + 4.4)
    ax.set_ylim(0, len(events) + 1.5)
    ax.set_title("Enterprise Bus Matrix - business events x conformed dimensions", fontsize=14, weight="bold", color=NAVY)
    top = len(events) + 0.8
    for j, d in enumerate(dims):
        ax.text(4.4 + j*1.45 + 0.7, top, d.replace("Dim_", "Dim_\n"), ha="center", va="center", fontsize=8,
                weight="bold", color="white", bbox=dict(boxstyle="round", fc=TEAL, ec=TEAL))
    for i, (ev, fact, used) in enumerate(events):
        y = top - 1 - i
        ax.add_patch(plt.Rectangle((0, y - 0.45), len(dims)*1.45 + 4.4, 0.9, fc=LIGHT if i % 2 == 0 else "white", ec="none"))
        ax.text(0.1, y, ev, va="center", fontsize=9, weight="bold", color=NAVY)
        ax.text(2.35, y, fact, va="center", fontsize=8, color="#444")
        for j, d in enumerate(dims):
            if d in used:
                ax.text(4.4 + j*1.45 + 0.7, y, "X", ha="center", va="center", fontsize=12, weight="bold", color=NAVY)
    fig.savefig(os.path.join(OUT, "fig_bus_matrix.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    star()
    bus()
    print("Diagrams written to", OUT)
