""" Creates a video file showing detections on the SLP dataset. """

from mpl_toolkits.basemap import Basemap
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, os.path, re
from utils import *


MARGIN = 10
PAUSE_LEN = 3
MAX_DET = 0


if __name__ == '__main__':

    # Load data
    data = loadTensor()
    gridspec = getSLPGridSpec()
    vmin = data.min()
    vmax = data.max()
    base_date = datetime.datetime(gridspec['year_offs'], 1, 1)
    lats = np.arange(gridspec['lat_offs'], gridspec['lat_offs'] + gridspec['lat_step'] * data.shape[1], gridspec['lat_step'])
    lons = np.arange(gridspec['lon_offs'], gridspec['lon_offs'] + gridspec['lon_step'] * data.shape[2], gridspec['lon_step'])
    
    # Load detections
    detections = []
    if len(sys.argv) > 1:
        
        show = np.zeros(data.shape[0], dtype = bool)
        
        with open(sys.argv[1]) as f:
            detfile = f.read()

        detRE = re.compile('TIMEFRAME:\\s+([0-9-]+) - ([0-9-]+)\\s+LOCATION:\\s+(-?[0-9.]+) N, (-?[0-9.]+) E - (-?[0-9.]+) N, (-?[0-9.]+) E(\\s+SCORE:\\s+[0-9.-]+\\s+IDENT:\\s+([^(]+)\\s\\()?')

        for i, match in enumerate(detRE.finditer(detfile)):
            date_start = datetime.datetime.strptime(match.group(1), '%Y-%m-%d')
            date_end = datetime.datetime.strptime(match.group(2), '%Y-%m-%d')
            time_start = (date_start - base_date).days
            time_end = (date_end - base_date).days
            show[max(0, time_start - MARGIN):min(data.shape[0], time_end + 1 + MARGIN)] = True
            detections.append({
                'time_start': time_start,
                'time_end'  : time_end,
                'loc_start' : (float(match.group(3)), float(match.group(4))),
                'loc_end'   : (float(match.group(5)), float(match.group(6))),
                'event_name': match.group(8)
            })
            if (MAX_DET > 0) and (len(detections) >= MAX_DET):
                break
        
        animRange = np.arange(data.shape[0])[show].tolist()
        i = 1
        while (i < len(animRange)):
            if animRange[i] != animRange[i-1] + 1:
                for p in range(PAUSE_LEN):
                    animRange.insert(i, -1)
                i += PAUSE_LEN
            i += 1
    
    else:
        animRange = range(data.shape[0])
    
    detections.sort(key = lambda x: x['time_start'])
    
    # Create figure
    fig = plt.figure()
    ax = fig.add_subplot(111, title = 'Sea Level Pressure')
    fig.subplots_adjust(left = 0.04, bottom = 0.04, right = 0.96, top = 0.96, wspace = 0.2, hspace = None)
    m = Basemap(llcrnrlat = lats[0], llcrnrlon = lons[0], urcrnrlat = lats[-1], urcrnrlon = lons[-1], resolution = 'l', ax = ax)
    m.drawmapboundary()
    m.drawcoastlines()

    lons, lats = np.meshgrid(lons, lats)
    
    # Animation
    artists = { 'im' : None, 'cb' : None }
    
    def animate(t):
        
        # Update title
        if t < 0:
            ax.set_title('Sea Level Pressure')
        else:
            ax.set_title('Sea Level Pressure at {}'.format((base_date + datetime.timedelta(days = t)).date()))
        if (len(detections) > 0) and (detections[0]['event_name'] is not None) and (t >= detections[0]['time_start']) and (t <= detections[0]['time_end']):
            fig.suptitle('{}'.format(detections[0]['event_name']))
        else:
            fig.suptitle('')
        
        # Data heatmap
        if artists['im'] is not None:
            artists['im'].remove()
            artists['im'] = None
        if t >= 0:
            artists['im'] = m.pcolormesh(lons, lats, data[t,:,:].squeeze(), shading = 'flat', cmap = plt.cm.jet, vmin = vmin, vmax = vmax, latlon = True)
        
        # Color bar
        if (artists['cb'] is None) and (artists['im'] is not None):
            artists['cb'] = m.colorbar(artists['im'], 'bottom', size = '5%', pad = '2%')
        
        # Detection bounding box
        if (len(detections) > 0) and (t > detections[0]['time_end']):
            detections.pop(0)
            artists['bbox'].remove()
            artists['bbox'] = None
        if (len(detections) > 0) and (t == detections[0]['time_start']):
            artists['bbox'] = m.plot(
                [detections[0]['loc_start'][1], detections[0]['loc_start'][1], detections[0]['loc_end'][1], detections[0]['loc_end'][1], detections[0]['loc_start'][1]],
                [detections[0]['loc_start'][0], detections[0]['loc_end'][0], detections[0]['loc_end'][0], detections[0]['loc_start'][0], detections[0]['loc_start'][0]],
                color = 'red', linewidth = 3, latlon = True
            )[0]
    

    ani = animation.FuncAnimation(fig, animate, animRange, interval = 250 if len(detections) > 0 else 50, repeat = False, blit = False)
    if len(sys.argv) > 2:
        ani.save(sys.argv[2], bitrate = 1200)
    else:
        plt.show()
