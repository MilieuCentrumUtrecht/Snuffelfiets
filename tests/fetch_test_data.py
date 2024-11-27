# Fetches the test data from the server. In principle,
# this should not be run often, but can be run if the
# test data needs to be updated.
from pathlib import Path

import numpy as np
import pandas as pd

from snuffelfiets import inlezen

api_key = ""  # Get API key from internal documents

# Select dataset one: curated bike rides from Michiel
day = 12
month = 11
year = 2024
date = f"{year}-{month:02d}-{day:02d}"

# Read data.
start_datum = f"{year}-{month:02d}-{day-1:02d}"
stop_datum = f"{year}-{month:02d}-{day+1:02d}"
df = inlezen.call_api(api_key, start_datum, stop_datum)

# Select data for id's.
ids = []
ids += [356726100940667, 356726101114817]  ## set 1
ids += [359215101327527, 356726100940915]  ## set 2
ids += [356726101510196, 356726100944040]  ## set 3
ids += [352753098853250, 359215101207828]  ## set 4
ids += [352753098851148, 359215101323005]  ## set 5
df = df.loc[df["entity_id"].astype(np.int64).isin(ids)]

# Select dataset two: curated bike rides from Ad
month = 7
year = 2024
date = f"{year}-{month:02d}-{day:02d}"

# Read data
start_datum = f"{year}-{month:02d}-{day-1:02d}"
stop_datum = f"{year}-{month:02d}-{day+1:02d}"
df2 = inlezen.call_api(api_key, start_datum, stop_datum)

# Select data for id's
ids = [356726100940899]
df2 = df2.loc[df2["entity_id"].astype(np.int64).isin(ids)]

# Combine datasets with unique index and save to disk
df_final = pd.concat([df, df2], ignore_index=True)
data_folder = Path(__file__, "../data/").resolve()
df_final.to_csv(data_folder / "test_data.csv")
