OpenMarineStream v1.0: Raw Multi-Sensor Marine Time Series for Online Anomaly Detection
Author: Samuel Moses Orokpo. Published 7 January 2026 (v1.0.0). DOI 10.5281/zenodo.18177103, https://zenodo.org/records/18177103
Licence: Creative Commons Attribution 4.0 International (CC BY 4.0). Files here are unchanged copies.
Supplied by Alan on 31 Oct 2026. A FerryBox-style flow-through system; one reading a minute, 28 to 30 October (the record gives no year; the timestamps say 2021).
Used by tools/hexn_real_ocean_v1.py and _v2.py, in this folder:
  Labeled_PreProcessed_Dataset.csv                     (4,315 rows: Timestamp + 9 sensor columns; the Zenodo page does not explain any labels and the file has NO label column)
  Optode_Saturation_10-28_10-30_with_position.csv      (the raw saturation file; its third column carries the platform position as GeoJSON, used for the sun height)
The eight other raw sensor files on the record hold the same readings and are not copied here.
Intended use named by the author: online anomaly detection, sensor fusion and concept drift.
