import pandas as pd
from scipy.spatial import cKDTree
import numpy as np

# Load Excel file
file_path = 'rhb-gm-summits.xlsx'
byregion = pd.read_excel(file_path, sheet_name='byregion')
gm_sota = pd.read_excel(file_path, sheet_name='gm-sota')

# Ensure lat/lon columns exist and are named consistently
byregion = byregion.rename(columns=lambda x: x.strip().capitalize())
gm_sota = gm_sota.rename(columns=lambda x: x.strip().capitalize())

# Extract lat/lon from both sheets
by_latlon = byregion[['Latitude', 'Longitude']].to_numpy()
sota_latlon = gm_sota[['Latitude', 'Longitude']].to_numpy()

# Build a spatial index on gm-sota coords
tree = cKDTree(sota_latlon)

# Find closest gm-sota point for each byregion point
distances, indices = tree.query(by_latlon, k=1)

# Add closest SummitCode to byregion
byregion['SOTA Ref'] = gm_sota.loc[indices, 'Summitcode'].values

# Save the result (option 1: overwrite original)
with pd.ExcelWriter(file_path, mode='a', if_sheet_exists='replace') as writer:
    byregion.to_excel(writer, sheet_name='byregion', index=False)

# Alternative: Save to a new file
# byregion.to_excel('rhb-gm-summits-updated.xlsx', sheet_name='byregion', index=False)
