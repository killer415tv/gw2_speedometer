import sys

import pandas as pd

try:
    import plotly.express as px
except ImportError:
    sys.exit("plotly is not installed (optional). Install it with: "
             "pip install -r requirements-optional.txt")

import os
import glob
from pathlib import Path


# CSV files placed next to this script (same folder as before)
path = Path(__file__).resolve().parent
all_files = glob.glob(os.path.join(path, "*.csv"))
names = [os.path.basename(x) for x in all_files]

#print(names)

df = pd.DataFrame()
for file_ in all_files:
    file_df = pd.read_csv(file_)
    file_df['file_name'] = file_
    df = pd.concat([df, file_df], ignore_index=True)

    # use this for 1 line for each csv
fig = px.line_3d(df, x="X", y="Z", z="Y", color="file_name")
    # 2d speed time
#fig = px.line(df, x="ANGLE_BEETLE", y="SPEED", title='SPEED over Time', color="file_name")
    # and this for show speed points
#fig = px.scatter_3d(df, x="ACCELERATION", y="SPEED", z="ANGLE_BEETLE", color="SPEED")
    # 2d speed time
#fig = px.scatter(df, x="ANGLE_BEETLE", y="ACCELERATION", color="SPEED")


fig.show()
