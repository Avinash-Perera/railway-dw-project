#!/usr/bin/env python3
"""
Master ETL Orchestration Pipeline for Railway Data Warehouse
============================================================
Research Project:
    "Railway Passenger Congestion and Transit Delay Dynamics"
    University Project & IEEE Paper Submission

System Architecture:
    MySQL Star Schema (OLAP)
    - Dimensions: Dim_Date, Dim_Train, Dim_Station, Dim_DelayCategory
    - Central Fact: Fact_TrainDelay

Execution Order:
    1. Dimension Tables (Dim_Date, Dim_Train, Dim_Station)
    2. Fact Table (Fact_TrainDelay - performs surrogate key lookups & joins)
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
try:
    from etl.load_dimensions import main as load_dimensions_main
    from etl.load_fact import main as load_fact_main
except ImportError:
    from load_dimensions import main as load_dimensions_main
    from load_fact import main as load_fact_main


def print_banner():
    banner = """
================================================================================
 🚂  RAILWAY DATA WAREHOUSE — MASTER ETL ORCHESTRATION PIPELINE  🚀
================================================================================
 🎯 Objective : Railway Passenger Congestion & Transit Delay Dynamics (OLAP)
 🏛️  Schema    : MySQL Star Schema (Dimensions + Central Fact)
 ⏰ Started   : {start_time}
================================================================================
""".format(start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(banner)


def run_pipeline():
    start_total = time.time()
    print_banner()

    # -------------------------------------------------------------------------
    # PHASE 1: LOAD DIMENSION TABLES
    # -------------------------------------------------------------------------
    print("🔹" * 40)
    print("📦 [PHASE 1/2] Loading Dimension Tables into Data Warehouse...")
    print("   Target Dimensions : Dim_Date, Dim_Train, Dim_Station")
    print("🔹" * 40)
    phase1_start = time.time()

    try:
        load_dimensions_main()
        phase1_duration = time.time() - phase1_start
        print(f"\n✅ [PHASE 1/2 COMPLETED] Dimension tables loaded successfully in {phase1_duration:.2f}s.\n")
    except Exception as e:
        print(f"\n❌ [PHASE 1 FAILED] Error loading dimensions: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # PHASE 2: LOAD FACT TABLE
    # -------------------------------------------------------------------------
    print("🔹" * 40)
    print("📊 [PHASE 2/2] Loading Fact Table into Data Warehouse...")
    print("   Target Fact Table : Fact_TrainDelay")
    print("   Transformations   : DateSK derivation, Surrogate Key lookup mapping,")
    print("                       Delay Category banding & IsDelayed boolean flag")
    print("🔹" * 40)
    phase2_start = time.time()

    try:
        load_fact_main()
        phase2_duration = time.time() - phase2_start
        print(f"\n✅ [PHASE 2/2 COMPLETED] Fact table loaded successfully in {phase2_duration:.2f}s.\n")
    except Exception as e:
        print(f"\n❌ [PHASE 2 FAILED] Error loading fact table: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # PIPELINE COMPLETION SUMMARY
    # -------------------------------------------------------------------------
    total_duration = time.time() - start_total
    minutes = int(total_duration // 60)
    seconds = total_duration % 60

    print("=" * 80)
    print("🎉 MASTER ETL PIPELINE EXECUTED SUCCESSFULLY!")
    print(f"⏱️  Total Pipeline Runtime: {minutes}m {seconds:.2f}s ({total_duration:.2f}s total)")
    print("📈 Data Warehouse is fully populated and ready for OLAP queries & Power BI!")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()
