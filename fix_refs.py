import os

filepath = '/Volumes/Mac/docker-sandboxes/railway-dw-project/paper/IEEE_Railway_DW_Paper.md'

with open(filepath, 'r') as f:
    content = f.read()

# 1. Section II A
orig_sec2a = """### A. Data Warehousing in Transit Systems

The conceptual foundations of this work go back to Kimball's dimensional modelling framework [3], which introduced the ideas of Star Schemas, surrogate keys, and conformed dimensions that we rely on throughout. Inmon's competing top-down approach [4] is equally well-established, though it tends to front-load far more modelling effort upfront — a trade-off that makes it less practical for research-scale projects like ours. Both traditions have found applications in transit.

On the applied side, Singh et al. [5] built a DW-based analytics platform for urban bus transit in India and reported a 40% improvement in query speed over equivalent OLTP-based reporting. That finding resonates with our own experience: analytical queries that would time out against raw operational tables complete in seconds against the warehouse. Farooq and Kim [6] took a similar approach to metro rail delays in Seoul, using OLAP roll-up and drill-down to pinpoint station-level bottlenecks with 92% spatial accuracy."""

new_sec2a = """### A. Data Warehousing in Transit Systems

The conceptual foundations of this work go back to Kimball's dimensional modelling framework [3], which introduced the ideas of Star Schemas, surrogate keys, and conformed dimensions that we rely on throughout. Inmon's competing top-down approach [4] is equally well-established, though it tends to front-load far more modelling effort upfront — a trade-off that makes it less practical for research-scale projects like ours. Both traditions have found applications in transit, where analytical queries that would time out against raw operational tables complete in seconds against a warehouse."""

content = content.replace(orig_sec2a, new_sec2a)

# 2. Section II B
orig_sec2b = """### B. Big Data in Railway Operations

As railway sensors have become more pervasive and data volumes have grown, the field has shifted toward a Big Data framing. Zhang et al. [7] applied the 5 Vs framework — Volume, Velocity, Variety, Veracity, and Value — to Chinese high-speed rail sensor streams, building real-time anomaly detection models on top. Our dataset, at 38.32 million records and roughly 1 GB of raw CSV, clearly qualifies under the Volume and Velocity criteria, even if we operate in batch rather than real-time mode.

Two other studies shaped our thinking directly. Goverde et al. [8] introduced a timetable stability index derived from delay propagation graphs — an elegant formalisation of what rail operators already know intuitively: delays breed more delays. Murali et al. [9] showed that congestion at terminal stations tends to originate from minor upstream delays that compound into severe events, a pattern we independently observe in our spatial bottleneck analysis (Section IV-B)."""

new_sec2b = """### B. Big Data in Railway Operations

As railway sensors have become more pervasive and data volumes have grown, the field has shifted toward a Big Data framing. Our dataset, at 38.32 million records and roughly 1 GB of raw CSV, clearly qualifies under the Volume and Velocity dimensions of Big Data, even if we operate in batch rather than real-time mode.

Two studies shaped our thinking directly. Goverde et al. [5] introduced a timetable stability index derived from delay propagation graphs — an elegant formalisation of what rail operators already know intuitively: delays breed more delays. Murali et al. [6] showed that congestion at terminal stations tends to originate from minor upstream delays that compound into severe events, a pattern we independently observe in our spatial bottleneck analysis (Section IV-B)."""

content = content.replace(orig_sec2b, new_sec2b)

# 3. Section II C
orig_sec2c = """### C. ETL and Data Quality

There is a reason ETL is sometimes described as the unglamorous backbone of data warehousing: it is where most of the real work happens, and where most projects silently fail [10]. Batch-chunked loading — the approach we use — is widely recommended for large-scale fact table ingestion because it keeps memory footprints predictable regardless of source file size [11]. Less obvious, but equally important, is the question of when to enforce referential integrity. Golfarelli and Rizzi [12] found that enforcing surrogate key mappings at ETL time, rather than trusting downstream application logic, reduced analytical inconsistency by up to 17% in their study cohort. We adopted the same approach."""

new_sec2c = """### C. ETL and Data Quality

There is a reason ETL is sometimes described as the unglamorous backbone of data warehousing: it is where most of the real work happens, and where most projects silently fail [7]. Batch-chunked loading — the approach we use — is widely recommended for large-scale fact table ingestion because it keeps memory footprints predictable regardless of source file size. Less obvious, but equally important, is the question of when to enforce referential integrity. Golfarelli and Rizzi [8] found that enforcing surrogate key mappings at ETL time, rather than trusting downstream application logic, reduced analytical inconsistency by up to 17% in their study cohort. We adopted the same approach."""

content = content.replace(orig_sec2c, new_sec2c)

# 4. Section IV A
orig_iv_a = """What is more interesting, though, is the tail. Severe delays — trips more than 45 minutes late — account for just 1.5% by count, but that translates to roughly 700,000 trip-events in absolute terms. Worse, because severe delays are longer by definition, they punch well above their weight in terms of total passenger-hours lost. This is a classic heavy-tailed distribution: the rare events cause a disproportionate share of the harm [8]. Any intervention strategy that ignores this tail will systematically underestimate the true cost of delay."""

new_iv_a = orig_iv_a.replace("[8]", "[5]")

content = content.replace(orig_iv_a, new_iv_a)

# 5. Section IV B
orig_iv_b = """This is consistent with what Murali et al. [9] described — congestion at terminal and interchange stations creates a local feedback loop where inbound delays cause outbound delays for connecting services. Our data provides empirical confirmation of that dynamic at the Indian Railways scale."""

new_iv_b = orig_iv_b.replace("[9]", "[6]")

content = content.replace(orig_iv_b, new_iv_b)

# 6. References
orig_refs = """## References

[1] Ministry of Railways, Government of India, *Indian Railways Statistical Summary 2023-24*, New Delhi: Railway Board Publications, 2024.

[2] R. Kimball and M. Ross, *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*, 3rd ed. Indianapolis: Wiley, 2013.

[3] R. Kimball, *The Data Warehouse Lifecycle Toolkit*, 2nd ed. Indianapolis: Wiley, 2008.

[4] W. H. Inmon, *Building the Data Warehouse*, 4th ed. Indianapolis: Wiley, 2005.

[5] A. Singh, P. Sharma, and R. Kumar, "OLAP-based performance analytics framework for urban bus transit systems," *Int. J. Transportation Science and Technology*, vol. 11, no. 3, pp. 512–529, 2022.

[6] H. Farooq and Y. Kim, "Real-time delay analytics for Seoul Metro using multidimensional OLAP cubes," in *Proc. IEEE Int. Conf. Intelligent Transportation Systems (ITSC)*, Indianapolis, IN, USA, 2021, pp. 1847–1854.

[7] L. Zhang, T. Wang, and H. Chen, "Big Data analytics for high-speed railway anomaly detection: A 5V framework implementation," *IEEE Trans. Intelligent Transportation Systems*, vol. 23, no. 8, pp. 11342–11358, Aug. 2022.

[8] R. M. P. Goverde, F. Corman, and A. D'Ariano, "Railway line capacity consumption of different railway signalling systems under scheduled and disturbed conditions," *J. Rail Transport Planning & Management*, vol. 3, no. 3, pp. 78–94, 2013.

[9] P. Murali, M. Dessouky, F. Ordóñez, and K. Palmer, "A delay estimation technique for single and double-track railroads," *Transportation Research Part E: Logistics and Transportation Review*, vol. 46, no. 4, pp. 483–495, 2010.

[10] R. Kimball and J. Caserta, *The Data Warehouse ETL Toolkit: Practical Techniques for Extracting, Cleaning, Conforming, and Delivering Data*. Indianapolis: Wiley, 2004.

[11] A. Castellanos, J. Sanz, J. Blanco, and J. C. Dueñas, "An architecture for data quality management in data warehouses," in *Proc. 20th Int. Conf. Information Quality (ICIQ)*, Cambridge, MA, USA, 2015, pp. 1–14.

[12] M. Golfarelli and S. Rizzi, *Data Warehouse Design: Modern Principles and Methodologies*. New York: McGraw-Hill Osborne Media, 2009.

---"""

new_refs = """## References

[1] Ministry of Railways, Government of India, *Indian Railways Statistical Summary 2023-24*, New Delhi: Railway Board Publications, 2024.

[2] R. Kimball and M. Ross, *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*, 3rd ed. Indianapolis: Wiley, 2013.

[3] R. Kimball, *The Data Warehouse Lifecycle Toolkit*, 2nd ed. Indianapolis: Wiley, 2008.

[4] W. H. Inmon, *Building the Data Warehouse*, 4th ed. Indianapolis: Wiley, 2005.

[5] R. M. P. Goverde, F. Corman, and A. D'Ariano, "Railway line capacity consumption of different railway signalling systems under scheduled and disturbed conditions," *J. Rail Transport Planning & Management*, vol. 3, no. 3, pp. 78–94, 2013.

[6] P. Murali, M. Dessouky, F. Ordóñez, and K. Palmer, "A delay estimation technique for single and double-track railroads," *Transportation Research Part E: Logistics and Transportation Review*, vol. 46, no. 4, pp. 483–495, 2010.

[7] R. Kimball and J. Caserta, *The Data Warehouse ETL Toolkit: Practical Techniques for Extracting, Cleaning, Conforming, and Delivering Data*. Indianapolis: Wiley, 2004.

[8] M. Golfarelli and S. Rizzi, *Data Warehouse Design: Modern Principles and Methodologies*. New York: McGraw-Hill Osborne Media, 2009.

---"""

content = content.replace(orig_refs, new_refs)

with open(filepath, 'w') as f:
    f.write(content)

print("Replacement done!")
