__all__ = ["DateAxisItem"]

import numpy
from pyqtgraph import AxisItem
from datetime import datetime, timedelta
from time import mktime

import time
import sys
import pyqtgraph as pg
from pyqtgraph import QtGui, QtWidgets
import random

from PyQt5.QtWidgets import (QApplication, QWidget,
QPushButton, QGridLayout)
from PyQt5.QtCore import Qt, QTimer

# Šo klasi nevajag aiztikt, tā strāda kā vajag un nevajag kautko salauzt
class DateAxisItem(AxisItem):
    # Max width in pixels reserved for each label in axis
    _pxLabelWidth = 80

    def __init__(self, *args, **kwargs):
        AxisItem.__init__(self, *args, **kwargs)
        self._oldAxis = None

    def tickValues(self, minVal, maxVal, size):
        maxMajSteps = int(size/self._pxLabelWidth)

        dt1 = datetime.fromtimestamp(minVal)
        dt2 = datetime.fromtimestamp(maxVal)

        dx = maxVal - minVal
        majticks = []

        if dx > 63072001:  # 3600s*24*(365+366) = 2 years (count leap year)
            d = timedelta(days=366)
            for y in range(dt1.year + 1, dt2.year):
                dt = datetime(year=y, month=1, day=1)
                majticks.append(mktime(dt.timetuple()))

        elif dx > 5270400:  # 3600s*24*61 = 61 days
            d = timedelta(days=31)
            dt = dt1.replace(day=1, hour=0, minute=0,
                             second=0, microsecond=0) + d
            while dt < dt2:
                # make sure that we are on day 1 (even if always sum 31 days)
                dt = dt.replace(day=1)
                majticks.append(mktime(dt.timetuple()))
                dt += d

        elif dx > 172800:  # 3600s24*2 = 2 days
            d = timedelta(days=1)
            dt = dt1.replace(hour=0, minute=0, second=0, microsecond=0) + d
            while dt < dt2:
                majticks.append(mktime(dt.timetuple()))
                dt += d

        elif dx > 7200:  # 3600s*2 = 2hours
            d = timedelta(hours=1)
            dt = dt1.replace(minute=0, second=0, microsecond=0) + d
            while dt < dt2:
                majticks.append(mktime(dt.timetuple()))
                dt += d

        elif dx > 1200:  # 60s*20 = 20 minutes
            d = timedelta(minutes=10)
            dt = dt1.replace(minute=(dt1.minute // 10) * 10,
                             second=0, microsecond=0) + d
            while dt < dt2:
                majticks.append(mktime(dt.timetuple()))
                dt += d

        elif dx > 120:  # 60s*2 = 2 minutes
            d = timedelta(minutes=1)
            dt = dt1.replace(second=0, microsecond=0) + d
            while dt < dt2:
                majticks.append(mktime(dt.timetuple()))
                dt += d

        elif dx > 20:  # 20s
            d = timedelta(seconds=10)
            dt = dt1.replace(second=(dt1.second // 10) * 10, microsecond=0) + d
            while dt < dt2:
                majticks.append(mktime(dt.timetuple()))
                dt += d

        elif dx > 2:  # 2s
            d = timedelta(seconds=1)
            majticks = range(int(minVal), int(maxVal))

        else:  # <2s , use standard implementation from parent
            return AxisItem.tickValues(self, minVal, maxVal, size)

        L = len(majticks)
        if L > maxMajSteps:
            majticks = majticks[::int(numpy.ceil(float(L) / maxMajSteps))]

        return [(d.total_seconds(), majticks)]

    def tickStrings(self, values, scale, spacing):
        ret = []
        if not values:
            return []

        if spacing >= 31622400:  # 366 days
            fmt = "%Y"

        elif spacing >= 2678400:  # 31 days
            fmt = "%Y %b"

        elif spacing >= 86400:  # = 1 day
            fmt = "%b/%d"

        elif spacing >= 3600:  # 1 h
            fmt = "%b/%d-%Hh"

        elif spacing >= 60:  # 1 m
            fmt = "%H:%M"

        elif spacing >= 1:  # 1s
            fmt = "%H:%M:%S"

        else:
            # less than 2s (show microseconds)
            # fmt = '%S.%f"'
            fmt = '[+%fms]'  # explicitly relative to last second

        for x in values:
            try:
                t = datetime.fromtimestamp(x)
                ret.append(t.strftime(fmt))
            except ValueError:  # Windows can't handle dates before 1970
                ret.append('')

        return ret

    def attachToPlotItem(self, plotItem):
        self.setParentItem(plotItem)
        viewBox = plotItem.getViewBox()
        self.linkToView(viewBox)
        self._oldAxis = plotItem.axes[self.orientation]['item']
        self._oldAxis.hide()
        plotItem.axes[self.orientation]['item'] = self
        pos = plotItem.axes[self.orientation]['pos']
        plotItem.layout.addItem(self, *pos)
        self.setZValue(-1000)

    def detachFromPlotItem(self):
        raise NotImplementedError()  # TODO


class Window(QWidget):
    def __init__(self):
        super().__init__()
        # Lists where all required data is stored
        self.timestamps = []
        self.data_temp = []
        self.data_humid = []
        self.data_alt = []
        self.data_press = []
        # Timer that updates data
        self.qTimer = QTimer()
        self.qTimer.setInterval(10) # milliseconds
        self.qTimer.start()
        self.qTimer.timeout.connect(self.update_data)
        self.initUI()
    
    def update_data(self):
        self.timestamps.append(time.time())
        self.data_temp.append(random.uniform(0, 30))
        self.data_humid.append(random.uniform(0, 100))
        self.data_alt.append(random.uniform(0, 1000))
        self.data_press.append(random.randint(900, 1200))
        
        self.temp_plot.setData(self.timestamps, self.data_temp)
        self.press_plot.setData(self.timestamps, self.data_press)
        self.humid_plot.setData(self.timestamps, self.data_humid)
        self.alt_plot.setData(self.timestamps, self.data_alt)
        
    def initUI(self):   
        grid = QGridLayout()  
        self.setLayout(grid)
        self.setWindowTitle("Base station data")
        
        self.temperature_plot = pg.PlotWidget()
        self.pressure_plot = pg.PlotWidget()
        self.humidity_plot = pg.PlotWidget()
        self.altitude_plot = pg.PlotWidget()

        # Add the Date-time axis
        axis1 = DateAxisItem(orientation='bottom')
        axis1.attachToPlotItem(self.temperature_plot.getPlotItem())
        
        axis2 = DateAxisItem(orientation='bottom')
        axis2.attachToPlotItem(self.pressure_plot.getPlotItem())
        
        axis3 = DateAxisItem(orientation='bottom')
        axis3.attachToPlotItem(self.humidity_plot.getPlotItem())
        
        axis4 = DateAxisItem(orientation='bottom')
        axis4.attachToPlotItem(self.altitude_plot.getPlotItem())
        
        # plot some rndom data with timestamps in the last hour
        self.temp_plot = self.temperature_plot.plot(x=self.timestamps, y=self.data_temp, symbol='o')
        
        self.press_plot = self.pressure_plot.plot(x=self.timestamps, y=self.data_press, symbol='o')
        
        self.humid_plot = self.humidity_plot.plot(x=self.timestamps, y=self.data_humid, symbol='o')
        
        self.alt_plot = self.altitude_plot.plot(x=self.timestamps, y=self.data_alt, symbol='o')
        
        grid.addWidget(self.temperature_plot, 0, 0)
        grid.addWidget(self.pressure_plot, 1, 0);
        grid.addWidget(self.humidity_plot, 2, 0)
        grid.addWidget(self.altitude_plot, 3, 0);
          
        self.show()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = Window()
    sys.exit(app.exec_())
