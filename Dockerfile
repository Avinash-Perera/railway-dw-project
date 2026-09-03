FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files & enable unbuffered standard output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install required dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY etl/ ./etl/
COPY sql/ ./sql/
COPY run_sql_scripts.py .

# Default entrypoint runs the master ETL orchestration
CMD ["python", "etl/run_etl.py"]
