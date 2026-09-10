# 🚂 Railway Data Warehouse — Complete Setup Guide for New Users

> **Prerequisites:** Docker Desktop installed and running on your machine. That's it. Python is only needed if you want to re-run the ETL or generate figures.

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/<your-username>/railway-dw-project.git
cd railway-dw-project
```

---

## Step 2 — Get the Raw Data Files

The raw CSV data files (~1 GB total) are **not included in the repository** because they are too large for GitHub. You need to obtain them separately.

Ask the project owner to share the following files via Google Drive, OneDrive, or USB:

| File | Description |
|:---|:---|
| `combined_delay.csv` | ~38.5M rows of delay telemetry (~1 GB) |
| `station_full_names.csv` | 8,963 station names |
| `train_details.csv` | 8,720 train records |
| `combined_schedule.csv` | ~280K schedule entries |

Once you have the files, place them inside a `data/` folder in the project root:

```
railway-dw-project/
├── data/
│   ├── combined_delay.csv          ← place here
│   ├── station_full_names.csv      ← place here
│   ├── train_details.csv           ← place here
│   └── combined_schedule.csv       ← place here
├── docker-compose.yml
├── etl/
└── ...
```

---

## Step 3 — Start the Docker Containers

```bash
docker compose up -d
```

This command starts two services:
- **MySQL 8.0** data warehouse on port `3306`
- **Metabase** BI dashboard on port `3000`

Wait about 15–20 seconds for MySQL to finish its health check, then verify both are running:

```bash
docker ps
```

You should see two containers with status `Up` and `healthy`:
```
railway_dw_mysql       Up (healthy)
railway_bi_metabase    Up
```

> **Note on SQL Scripts:** You do *not* need to manually run the SQL files to create the database or schema. The `sql/` directory is mapped to the MySQL container, so all tables and views are automatically created the very first time you run `docker compose up -d`.

---

## Step 4 — Install Python Dependencies

You need Python 3.9 or higher. Install the required packages:

```bash
pip install -r requirements.txt
```

> **On macOS/Linux with a managed Python environment**, use:
> ```bash
> pip install --break-system-packages -r requirements.txt
> ```

---

## Step 5 — Run the ETL Pipeline

This is the main step that loads all 38.32 million rows into the MySQL data warehouse. It will take **30–60 minutes** depending on your machine.

```bash
python3 etl/run_etl.py
```

You will see progress output as the pipeline runs through each chunk. When it finishes, you should see a confirmation that all rows have been loaded.

To verify the data loaded correctly, run:

```bash
docker exec railway_dw_mysql mysql -u root -pdw_password \
  -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='railway_dw' ORDER BY TABLE_ROWS DESC;" 2>/dev/null | grep -v Warning
```

Expected output:
```
TABLE_NAME          TABLE_ROWS
Fact_TrainDelay     38322228
Dim_Station         8963
Dim_Train           8720
Dim_Date            1096
Dim_DelayCategory   4
```

---

## Step 6 — Set Up Metabase (BI Dashboard)

1. Open your browser and go to: **http://localhost:3000**
2. You will see the Metabase "Welcome!" setup screen.
3. Click **"Let's get started"** and create your admin account.
4. When Metabase asks to connect a database, choose **MySQL** and fill in:

| Field | Value |
|:---|:---|
| **Display Name** | Railway Data Warehouse |
| **Host** | `mysql` |
| **Port** | `3306` |
| **Database name** | `railway_dw` |
| **Username** | `root` |
| **Password** | `dw_password` |

5. Click **"Save"** and your data warehouse is connected.

---

## Step 7 — Generate the Paper Figures (Optional)

If you need to regenerate the 4 publication-quality PNG charts for the IEEE paper:

```bash
python3 generate_paper_figures.py
```

Figures are saved to `paper/figures/`:
- `figure1_delay_severity_pie.png`
- `figure2_top_10_bottleneck_stations.png`
- `figure3_monthly_delay_trajectory.png`
- `figure4_weekend_vs_weekday_comparison.png`

To also regenerate the ETL pipeline and Star Schema architecture diagrams:

```bash
pip install --break-system-packages graphviz   # one-time install
sudo apt-get install -y graphviz               # Linux only
python3 generate_diagrams.py
```

---

## Useful Commands

```bash
# Start all containers
docker compose up -d

# Stop all containers (data is preserved)
docker compose down

# ⚠️  DO NOT run this — it permanently deletes all your data
docker compose down -v

# Check MySQL row counts
docker exec railway_dw_mysql mysql -u root -pdw_password \
  -e "SELECT COUNT(*) FROM railway_dw.Fact_TrainDelay;" 2>/dev/null | grep -v Warning

# View container logs
docker logs railway_dw_mysql
docker logs railway_bi_metabase
```

---

## Data Persistence

All data is stored inside Docker named volumes on your machine:

| Volume | Contents |
|:---|:---|
| `mysql_dw_data` | All 38.32M warehouse rows + Metabase dashboards |

The data survives:
- ✅ Closing your terminal / IDE
- ✅ Restarting your computer
- ✅ Running `docker compose down` then `docker compose up -d`

It is **permanently deleted** only if you explicitly run `docker compose down -v`.

---

## Troubleshooting

**MySQL container won't start:**
```bash
docker logs railway_dw_mysql
# If port 3306 is in use by another MySQL instance:
# Change "3306:3306" to "3307:3306" in docker-compose.yml
```

**ETL fails with connection error:**
```bash
# Make sure MySQL is healthy before running ETL
docker ps   # Check status is "healthy"
```

**Metabase shows blank page at localhost:3000:**
```bash
# Metabase takes 1-2 minutes to start — wait and refresh
docker logs railway_bi_metabase
```

**"Externally managed environment" error with pip:**
```bash
pip install --break-system-packages -r requirements.txt
```

---

## Project Structure

```
railway-dw-project/
├── docker-compose.yml          ← Defines MySQL + Metabase services
├── Dockerfile                  ← ETL runner container definition
├── requirements.txt            ← Python dependencies
├── data/                       ← Raw CSV files (not in git — add manually)
├── sql/                        ← Database schema DDL (auto-runs on first start)
├── etl/
│   ├── run_etl.py              ← Main ETL entry point (run this)
│   ├── load_dimensions.py      ← Loads all 4 dimension tables
│   ├── load_fact.py            ← Loads the 38M-row fact table
│   └── db_connector.py        ← SQLAlchemy database connection
├── paper/
│   ├── IEEE_Railway_DW_Paper.md ← Full IEEE conference paper
│   └── figures/                ← Publication-quality PNG charts
├── generate_paper_figures.py   ← Generates the 4 paper figures
└── generate_diagrams.py        ← Generates architecture diagrams
```
