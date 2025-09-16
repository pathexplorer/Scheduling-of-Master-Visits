import pandas as pd
import openrouteservice
import numpy as np
from tqdm import tqdm

# Loading CSV
df = pd.read_csv("fin1.csv")
df.columns = ['Num', 'Geo']
# Geocoordinates Processing 
df[['lat', 'lon']] = df['Geo'].str.split(',', expand=True).astype(float)
locations = list(zip(df['lon'], df['lat']))  # (longitude, latitude)
store_ids = df['Num'].tolist()
N = len(locations)

# Initialization ORS-client
client = openrouteservice.Client(key='...............')  # <-- insert there API key

# Create empty matrix
distance_matrix = np.zeros((N, N))

# Splitting by blocks 
MAX_BLOCK = 50
num_blocks = (N + MAX_BLOCK - 1) // MAX_BLOCK

# Queries for blocks
print(f"🔄 Processing of {N} locations in {num_blocks} blocks")

for i in tqdm(range(num_blocks)):
    for j in range(num_blocks):
        from_start = i * MAX_BLOCK
        from_end = min((i + 1) * MAX_BLOCK, N)
        to_start = j * MAX_BLOCK
        to_end = min((j + 1) * MAX_BLOCK, N)

        from_locs = locations[from_start:from_end]
        to_locs = locations[to_start:to_end]

        try:
            response = client.distance_matrix(
                locations=from_locs + to_locs,
                sources=list(range(len(from_locs))),
                destinations=list(range(len(from_locs), len(from_locs) + len(to_locs))),
                profile='driving-car',
                metrics=['distance'],
                units='km'
            )
            distances = np.array(response['distances'])
            distance_matrix[from_start:from_end, to_start:to_end] = distances

        except Exception as e:
            print(f"Error during processing block ({i}, {j}): {e}")
            continue

# Creating a table of results
distance_df = pd.DataFrame(distance_matrix, index=store_ids, columns=store_ids)
print("Matrix ready")

# Saving to file
distance_df.to_csv("distance_one_to_one.csv")
print("Saved to file distance_oneto_one.csv")
