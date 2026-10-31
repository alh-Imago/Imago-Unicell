Ocean-sensor log supplied by Alan on 31 Oct 2026 (source and licence not stated; the CSV files are NOT committed, see .gitignore).
Needed by tools/hexn_real_ocean_v1.py and _v2.py, in this folder:
  Labeled_PreProcessed_Dataset.csv                     (4,315 rows: Timestamp + 9 sensor columns, one row per minute, 2021-10-28 to 2021-10-30; there is NO label column)
  Optode_Saturation_10-28_10-30_with_position.csv      (the raw saturation file; its third column carries the platform position as GeoJSON, used for the sun height)
The eight other raw files from the same upload (conductivity, C3 temperature, optode temperature and concentration, flow, flow temperature, salinity, turbidity) hold the same readings and are not needed.
