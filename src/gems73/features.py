"""Feature provenance — every external input is sha256-pinned in registry/data_manifest.json.

Official feature layers (read from training_features.tif, 19 bands, EPSG:32611 100m):
  0-... see registry/data_manifest.json for band descriptions (copied from reference solution notebook).
External layers (optional, free, official):
  - USGS 3DEP 1m DEM (via 1m_DEM_links.csv, official) -> 100m slope/curvature/relief
  - USGS GeoDAWN mag/rad (official)
  - NBMG INGENIOUS faults (official ArcGIS REST)
  - USGS ComCat epics (official FDSN, sub-km lineaments — H73-E, not yet fetched due sandbox block; status logged)
"""
