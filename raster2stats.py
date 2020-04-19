# -*- coding: utf-8 -*-
"""
Created on Sat Apr 18 12:21:25 2020

@author: Sharon
"""

import os
import numpy     as np
import pandas    as pd
import shapefile as shp
from matplotlib.path import Path
from tqdm import tqdm
from shapely.geometry import Polygon


#input tiff folder
rasterBundles ="Regen 2000 - 2019"

#input polygon file
plz = "plz-gebiete.shp\plz-gebiete.shp"

ncols = 611
nrows = 971
nodata = -999

xdelta = 1/60
ydelta = 1/120

x0 = (6-10*xdelta)
xn = 16.
y0 = (55+10*ydelta)
yn = 47.


xarr = np.linspace(x0,xn,ncols)
yarr = np.linspace(y0,yn,nrows)

x, y   = np.meshgrid(xarr,yarr)
x, y   = x.flatten(), y.flatten()
points = np.vstack((x,y)).T 
index  = np.arange(len(points))
    
#open zip code file
pin_idx = {}
r = shp.Reader(plz)
print('Assigning coordinates to pin codes...')
for n,s in tqdm(enumerate(r.shapeRecords())):
    pin  = r.record(n)['plz']
    poly = Polygon(s.shape.points)
    x_i,y_i,x_j,y_j = poly.bounds
    
    start = np.logical_and(np.greater_equal(points[:,0],x_i),np.less_equal(points[:,1], y_j))
    end   = np.logical_and(np.less_equal(points[:,0],x_j),np.greater_equal(points[:,1], y_i))
    
    bidx = np.logical_and(start,end)
    poly = Path(s.shape.points) 
    
    idx  = poly.contains_points(points[bidx])
    
    if pin in pin_idx.keys():
        pin_idx[pin] += [*list(index[bidx][idx])]
    else:
        pin_idx[pin] = list(index[bidx][idx])
    
r.close()

#save state
w = shp.Writer('plz_nodes')
w.fields = [('plz','N',8,0)]

for pin,idx in pin_idx.items():
    for i in idx:
        w.point(*points[i])
        w.record(pin)
w.close()

#sorting
arr_2_sort = np.full((nrows*ncols),-1)
for pin,idx in pin_idx.items(): arr_2_sort[idx] = int(pin)
sort = np.argsort(arr_2_sort)
plz,splits = np.unique(arr_2_sort[sort],return_index=True)


def mkarray(lines):
    array = np.array([float(l[z:z+4]) for l in lines[:-1] for z in range(0,ncols*4,4)])
    nan   = np.where(array == nodata)
    array[nan] = np.nan
    return array

#loop through rasters
yearly_dict = {}
print('Generating Statistics...')
for year in tqdm(os.listdir(rasterBundles)):
    print('Year: ',year)
    daily_dict = {}
    for day in tqdm(os.listdir(os.path.join(rasterBundles,year))):
        ras = os.path.join(rasterBundles,year,day)
        
        with open(ras,'r') as rf: lines = rf.readlines()
        
        array = mkarray(lines)
        
        day_ = pd.to_datetime(day.replace('ra',''),yearfirst=True)
        
        daily_dict[day_] = [np.nanmean(sa) for sa in np.array_split(array[sort],splits)[2:]]
        
    df = pd.DataFrame(daily_dict,index = plz[1:])
    df.to_csv(year+'.csv')
    yearly_dict[year[2:-1]] = df.mean(axis=1)
dfy = pd.DataFrame(yearly_dict)
dfy.to_csv(os.path.join('yearly_aggregate.csv'))