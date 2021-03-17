import pandas as pd
import plotly.express as px
import plotly.express as px
import plotly.graph_objects as go
import sys, os
import glob
import pandas as pd


path = os.path.dirname(os.path.abspath(sys.argv[0])) + "/"                  
all_files = glob.glob(os.path.join(path, "*.csv")) 
names = [os.path.basename(x) for x in glob.glob(path+'\*.csv')] 

#print(names)

df = pd.DataFrame()
for file_ in all_files:
    file_df = pd.read_csv(file_)
    file_df['file_name'] = file_
    df = df.append(file_df)

    # use this for 1 line for each csv
fig = px.line_3d(df, x="X", y="Z", z="Y", color="file_name")
    # 2d speed time
#fig = px.line(df, x="ANGLE_BEETLE", y="SPEED", title='SPEED over Time', color="file_name")
    # and this for show speed points
#fig = px.scatter_3d(df, x="ACCELERATION", y="SPEED", z="ANGLE_BEETLE", color="SPEED")
    # 2d speed time
#fig = px.scatter(df, x="ANGLE_BEETLE", y="ACCELERATION", color="SPEED")


fig.show()

