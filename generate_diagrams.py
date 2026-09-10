import os
import graphviz

FIGURES_DIR = '/Volumes/Mac/docker-sandboxes/railway-dw-project/paper/figures/'
os.makedirs(FIGURES_DIR, exist_ok=True)

# 1. Star Schema
schema = graphviz.Digraph('StarSchema', format='png')
schema.attr(rankdir='TB', nodesep='0.8', ranksep='0.8')
schema.attr('node', shape='record', fontname='Helvetica', style='filled', fillcolor='#f8f9fa')

schema.node('Fact', '''<<table border="0" cellborder="1" cellspacing="0" cellpadding="8">
<tr><td bgcolor="#34495e" align="center" colspan="2"><font color="white"><b>Fact_TrainDelay</b></font></td></tr>
<tr><td align="left"><b>FactID</b></td><td align="left">PK BIGINT AUTO_INCREMENT</td></tr>
<tr><td port="DateSK" align="left">DateSK</td><td align="left">FK (Dim_Date)</td></tr>
<tr><td port="StationSK" align="left">StationSK</td><td align="left">FK (Dim_Station)</td></tr>
<tr><td port="TrainSK" align="left">TrainSK</td><td align="left">FK (Dim_Train)</td></tr>
<tr><td port="DelayCatSK" align="left">DelayCatSK</td><td align="left">FK (Dim_DelayCategory)</td></tr>
<tr><td align="left"><i>DelayMinutes</i></td><td align="left">MEASURE INT</td></tr>
<tr><td align="left"><i>IsDelayed</i></td><td align="left">MEASURE TINYINT</td></tr>
</table>>''', shape='plaintext')

schema.node('DimDate', '''<<table border="0" cellborder="1" cellspacing="0" cellpadding="8">
<tr><td bgcolor="#2980b9" align="center" colspan="2"><font color="white"><b>Dim_Date</b></font></td></tr>
<tr><td port="DateSK" align="left"><b>DateSK</b></td><td align="left">PK INT</td></tr>
<tr><td align="left">Year</td><td align="left">INT</td></tr>
<tr><td align="left">Month</td><td align="left">INT</td></tr>
<tr><td align="left">Day</td><td align="left">INT</td></tr>
<tr><td align="left">IsWeekend</td><td align="left">TINYINT</td></tr>
</table>>''', shape='plaintext')

schema.node('DimStation', '''<<table border="0" cellborder="1" cellspacing="0" cellpadding="8">
<tr><td bgcolor="#27ae60" align="center" colspan="2"><font color="white"><b>Dim_Station</b></font></td></tr>
<tr><td port="StationSK" align="left"><b>StationSK</b></td><td align="left">PK INT</td></tr>
<tr><td align="left">StationCode</td><td align="left">VARCHAR</td></tr>
<tr><td align="left">StationName</td><td align="left">VARCHAR</td></tr>
</table>>''', shape='plaintext')

schema.node('DimTrain', '''<<table border="0" cellborder="1" cellspacing="0" cellpadding="8">
<tr><td bgcolor="#8e44ad" align="center" colspan="2"><font color="white"><b>Dim_Train</b></font></td></tr>
<tr><td port="TrainSK" align="left"><b>TrainSK</b></td><td align="left">PK INT</td></tr>
<tr><td align="left">TrainNo</td><td align="left">VARCHAR</td></tr>
<tr><td align="left">TrainName</td><td align="left">VARCHAR</td></tr>
<tr><td align="left">ServiceType</td><td align="left">VARCHAR</td></tr>
</table>>''', shape='plaintext')

schema.node('DimCat', '''<<table border="0" cellborder="1" cellspacing="0" cellpadding="8">
<tr><td bgcolor="#d35400" align="center" colspan="2"><font color="white"><b>Dim_DelayCategory</b></font></td></tr>
<tr><td port="DelayCatSK" align="left"><b>DelayCatSK</b></td><td align="left">PK INT</td></tr>
<tr><td align="left">CategoryName</td><td align="left">VARCHAR</td></tr>
<tr><td align="left">MinThreshold</td><td align="left">INT</td></tr>
<tr><td align="left">MaxThreshold</td><td align="left">INT</td></tr>
</table>>''', shape='plaintext')

# Edges (1:N from Dim to Fact)
schema.attr('edge', dir='back', arrowtail='crow', style='solid', color='#7f8c8d', penwidth='1.5')
schema.edge('Fact:DateSK', 'DimDate:DateSK')
schema.edge('Fact:StationSK', 'DimStation:StationSK')
schema.edge('Fact:TrainSK', 'DimTrain:TrainSK')
schema.edge('Fact:DelayCatSK', 'DimCat:DelayCatSK')

schema.render(os.path.join(FIGURES_DIR, 'fig_star_schema'), cleanup=True)

# 2. ETL Pipeline
etl = graphviz.Digraph('ETLPipeline', format='png')
etl.attr(rankdir='TB', nodesep='0.5', ranksep='0.7')
etl.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', margin='0.3')

etl.node('Source', 'Raw CSV Files (1.07 GB)', shape='cylinder', fillcolor='#ecf0f1')

etl.node('Phase1', '''<<table border="0" cellborder="0" cellspacing="0" cellpadding="4">
<tr><td align="left" bgcolor="#2980b9"><font color="white"><b>PHASE 1: Dimension Loading (load_dimensions.py)</b></font></td></tr>
<tr><td align="left">• Dim_Date: 1,096 calendar rows (in-memory)</td></tr>
<tr><td align="left">• Dim_Train: 8,720 rows from train_details.csv</td></tr>
<tr><td align="left">• Dim_Station: 8,963 rows from station_full_names.csv</td></tr>
<tr><td align="left">• Dim_DelayCategory: 4 rows (SQL DDL seeded)</td></tr>
</table>>''', shape='plaintext', style='filled', fillcolor='#ebedef')

etl.node('Phase2', '''<<table border="0" cellborder="0" cellspacing="0" cellpadding="4">
<tr><td align="left" bgcolor="#e67e22"><font color="white"><b>PHASE 2: Fact Table Loading (load_fact.py)</b></font></td></tr>
<tr><td align="left">• Read combined_delay.csv in 50,000-row chunks</td></tr>
<tr><td align="left">• Pre-fetch SK lookup dictionaries into memory</td></tr>
<tr><td align="left">• Derive DateSK: YYYYMMDD integer</td></tr>
<tr><td align="left">• Map DelayCatSK via banding function</td></tr>
<tr><td align="left">• Set IsDelayed = (delay &gt; 0)</td></tr>
<tr><td align="left">• Drop rows with NULL SK (referential integrity)</td></tr>
<tr><td align="left">• Append chunk → Fact_TrainDelay via to_sql()</td></tr>
</table>>''', shape='plaintext', style='filled', fillcolor='#fdf2e9')

etl.node('Target', 'MySQL Data Warehouse\n38,322,228 fact rows loaded', shape='cylinder', fillcolor='#2ecc71', fontcolor='white')

etl.attr('edge', color='#34495e', penwidth='2.0', arrowsize='1.2')
etl.edge('Source', 'Phase1')
etl.edge('Phase1', 'Phase2')
etl.edge('Phase2', 'Target')

etl.render(os.path.join(FIGURES_DIR, 'fig_etl_pipeline'), cleanup=True)
print("Diagrams generated successfully.")
