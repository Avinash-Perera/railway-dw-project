#!/usr/bin/env python3
"""
Master ETL Orchestration Pipeline for Railway Data Warehouse
============================================================
Research Project:
    "Railway Passenger Congestion and Transit Delay Dynamics"
    University Project & IEEE Paper Submission

System Architecture:
    MySQL Fact Constellation (OLAP) - 8 business events sharing 8 conformed dimensions
    - Dimensions: Dim_Date, Dim_Time, Dim_Station, Dim_Train (SCD2), Dim_DelayCategory,
                  Dim_Weather, Dim_DelayReason, Dim_CancellationReason
    - Facts     : Fact_TrainDelay, Fact_TrainSchedule, Fact_JourneyDeparture, Fact_JourneyArrival,
                  Fact_JourneyCancellation, Fact_DelayIncident, Fact_WeatherObservation,
                  Fact_TrainDailySnapshot

Execution Order:
    1. Dimension Tables (Dim_Date, Dim_Time, Dim_Train, Dim_Station; small dims are seeded by DDL)
    2. Large-file facts (Fact_TrainSchedule; Fact_TrainDelay + Departure + Arrival in one pass)
    3. Event facts (Cancellation, DelayIncident, Weather from train_delays.csv; Daily snapshot)
"""

import os
import sys
import time
from datetime import datetime

# Ensure project root directory is on sys.path for robust imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import main ETL routines
from etl.load_dimensions import main as load_dimensions_main
from etl.load_fact import main as load_fact_main
from etl.load_event_facts import main as load_event_facts_main


def print_banner():
    banner = """
================================================================================
 🚂  RAILWAY DATA WAREHOUSE — MASTER ETL ORCHESTRATION PIPELINE  🚀
================================================================================
 🎯 Objective : Railway Passenger Congestion & Transit Delay Dynamics (OLAP)
 🏛️  Schema    : MySQL Fact Constellation (8 facts x 8 conformed dimensions)
 ⏰ Started   : {start_time}
================================================================================
""".format(start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(banner)


PHASES = [
    ("Loading Dimension Tables",
     "Dim_Date, Dim_Time, Dim_Train (SCD2), Dim_Station", load_dimensions_main),
    ("Loading Large-File Fact Tables",
     "Fact_TrainSchedule, Fact_TrainDelay, Fact_JourneyDeparture, Fact_JourneyArrival", load_fact_main),
    ("Loading Event Fact Tables",
     "Fact_JourneyCancellation, Fact_DelayIncident, Fact_WeatherObservation, Fact_TrainDailySnapshot",
     load_event_facts_main),
]


def run_pipeline():
    start_total = time.time()
    print_banner()

    for n, (title, targets, func) in enumerate(PHASES, start=1):
        print("🔹" * 40)
        print(f"📦 [PHASE {n}/{len(PHASES)}] {title}...")
        print(f"   Targets : {targets}")
        print("🔹" * 40)
        phase_start = time.time()
        try:
            func()
        except Exception as e:
            print(f"\n❌ [PHASE {n} FAILED] {title}: {e}")
            sys.exit(1)
        print(f"\n✅ [PHASE {n}/{len(PHASES)} COMPLETED] in {time.time() - phase_start:.2f}s.\n")

    # -------------------------------------------------------------------------
    # PIPELINE COMPLETION SUMMARY
    # -------------------------------------------------------------------------
    total_duration = time.time() - start_total
    minutes = int(total_duration // 60)
    seconds = total_duration % 60

    print("=" * 80)
    print("🎉 MASTER ETL PIPELINE EXECUTED SUCCESSFULLY!")
    print(f"⏱️  Total Pipeline Runtime: {minutes}m {seconds:.2f}s ({total_duration:.2f}s total)")
    print("📈 Data Warehouse is fully populated. Next: python3 etl/validate_load.py")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()
