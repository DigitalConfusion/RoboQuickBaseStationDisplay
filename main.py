# Required libaries
# PyQt5 libaries
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtCore import QTimer
from pyqtgraph import AxisItem
from pyqtgraph import QtWidgets
import pyqtgraph as pg

# Rest of the libaries
import numpy
import sys
import threading
import serial
import random
from datetime import datetime, timedelta
import time
from time import mktime

# String for receiving serial data
base_station_data = ""

# Raw data - all data that comes in from serial port, it can be corrupted
# It can still be useful to get data, even if not everything can be used
raw_data = []

# Displayed data - data that shouldn't be corrupted
# Non-corrupted data received from serial port is appended to this list
# Latest data is split and gets appended to data lists, to be used by graphs
displayed_data = []

# Serial port being uses
# The new school laptop uses COM4, my computer uses COM8
com_port = "COM8"

# Is serial communication used? Intended for testing purposes
com_used = True


# This class makes it possible for graphs to display time as x-axis
# Don't touch this class, it works as it should.
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


# Main window
class Window(QWidget):
    def __init__(self):
        super().__init__()
        # Lists where all data is stored
        self.timestamps = []
        self.data_latitude = []
        self.data_longitude = []
        self.data_speed = []
        self.data_temp = []
        self.data_humid = []
        self.data_alt = []
        self.data_press = []

        # Starts a timer that updates lists and the graphs every second
        self.qTimer = QTimer()
        self.qTimer.setInterval(1000)  # milliseconds
        self.qTimer.start()
        self.qTimer.timeout.connect(self.update_data_real)

        # Run the ui
        self.initUI()

    # For testing purposes
    # Can be used to generate random data for graphs to plot
    # To use it change the function name in the qTimer.timeout to this function's name
    def update_data_random(self):
        # Appends random data to data lists
        self.timestamps.append(time.time())
        self.data_temp.append(random.uniform(0, 30))
        self.data_humid.append(random.uniform(0, 100))
        self.data_alt.append(random.uniform(0, 1000))
        self.data_press.append(random.randint(900, 1200))
        self.data_speed.append(random.uniform(0, 30))

        # Updates all graphs with the new data
        self.temp_plot.setData(self.timestamps, self.data_temp)
        self.press_plot.setData(self.timestamps, self.data_press)
        self.humid_plot.setData(self.timestamps, self.data_humid)
        self.alt_plot.setData(self.timestamps, self.data_alt)
        self.spd_plot.setData(self.timestamps, self.data_speed)

        # Prints all of the appended data
        self.raw_console.append(self.timestamps[-1], self.data_temp[-1], self.data_humid[-1], self.data_alt[-1], self.data_press[-1], self.data_speed[-1])
        self.displayed_console.append(self.timestamps[-1], self.data_temp[-1], self.data_humid[-1], self.data_alt[-1], self.data_press[-1], self.data_speed[-1])

    # For use with base station itself
    # For this function to work it needs to be set above in qTimer.timeout
    # and also base station has to be connected to PC and
    # Cansat has to be transmitting data
    def update_data_real(self):
        # Splits last received data
        split_data = displayed_data[-1].split(",")
        try:
            # Converts every data unit to float
            split_data = [float(x) for x in split_data]
            # Gets time when data was received
            self.timestamps.append(time.time())
            # Appends split data to data lists
            self.data_latitude.append(split_data[0])
            self.data_longitude.append(split_data[1])
            self.data_speed.append(split_data[2])
            self.data_alt.append(split_data[3])
            self.data_temp.append(split_data[4])
            self.data_humid.append(split_data[5])
            self.data_press.append(split_data[6])

            # makes sure that it doesn't try to change data to lists with no values
            if len(self.data_latitude) > 0:
                # Updates all graphs with new data
                self.temp_plot.setData(self.timestamps, self.data_temp)
                self.press_plot.setData(self.timestamps, self.data_press)
                self.humid_plot.setData(self.timestamps, self.data_humid)
                self.alt_plot.setData(self.timestamps, self.data_alt)
                self.spd_plot.setData(self.timestamps, self.data_speed)
                # Prints received data to consoles in app
                self.raw_console.append(raw_data[-1])
                self.displayed_console.append(displayed_data[-1])
        except:
            pass

    def initUI(self):
        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle("Base station data")
        self.setAutoFillBackground(True)
        p = self.palette()
        # Here it is possible to change background colour of app
        p.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(p)

        # Creates new text blocks to be used as consoles to display received data
        self.raw_console = QtWidgets.QTextEdit()
        self.displayed_console = QtWidgets.QTextEdit()

        # Makes consoles wider
        self.raw_console.setFixedWidth(500)
        self.displayed_console.setFixedWidth(500)

        # Creates graph widgets
        self.temperature_plot = pg.PlotWidget()
        self.pressure_plot = pg.PlotWidget()
        self.humidity_plot = pg.PlotWidget()
        self.altitude_plot = pg.PlotWidget()
        self.speed_plot = pg.PlotWidget()

        # Sets y-axis labels
        self.temperature_plot.setLabel(axis="left", text="Temperature, Celsius")
        self.pressure_plot.setLabel(axis="left", text="Pressure, kPa")
        self.humidity_plot.setLabel(axis="left", text="Humidity, %")
        self.altitude_plot.setLabel(axis="left", text="Altitude, meters")
        self.speed_plot.setLabel(axis="left", text="Speed, km/h")

        # Changes background of graphs to the same colour as app
        self.temperature_plot.setBackground(None)
        self.pressure_plot.setBackground(None)
        self.humidity_plot.setBackground(None)
        self.altitude_plot.setBackground(None)
        self.speed_plot.setBackground(None)

        # Add the Date-time axis to each graph
        axis1 = DateAxisItem(orientation='bottom')
        axis1.attachToPlotItem(self.temperature_plot.getPlotItem())

        axis2 = DateAxisItem(orientation='bottom')
        axis2.attachToPlotItem(self.pressure_plot.getPlotItem())

        axis3 = DateAxisItem(orientation='bottom')
        axis3.attachToPlotItem(self.humidity_plot.getPlotItem())

        axis4 = DateAxisItem(orientation='bottom')
        axis4.attachToPlotItem(self.altitude_plot.getPlotItem())

        axis5 = DateAxisItem(orientation='bottom')
        axis5.attachToPlotItem(self.speed_plot.getPlotItem())

        # Plots data to graphs
        self.temp_plot = self.temperature_plot.plot(x=self.timestamps, y=self.data_temp, symbol='o')

        self.press_plot = self.pressure_plot.plot(x=self.timestamps, y=self.data_press, symbol='o')

        self.humid_plot = self.humidity_plot.plot(x=self.timestamps, y=self.data_humid, symbol='o')

        self.alt_plot = self.altitude_plot.plot(x=self.timestamps, y=self.data_alt, symbol='o')

        self.spd_plot = self.speed_plot.plot(x=self.timestamps, y=self.data_speed, symbol='o')

        # Adds all widgets to grid
        grid.addWidget(self.temperature_plot, 0, 0)
        grid.addWidget(self.pressure_plot, 1, 0)
        grid.addWidget(self.humidity_plot, 2, 0)
        grid.addWidget(self.altitude_plot, 3, 0)
        grid.addWidget(self.speed_plot, 4, 0)
        grid.addWidget(self.raw_console, 0, 1)
        grid.addWidget(self.displayed_console, 1, 1)

        # Shows the ui
        self.show()

# Checks if received data doesn't have symbols that it shouldn't have
# Doesn't account if one number has changed to another one
# If this check is required, then that has to be set in Cansats and Base station arduino code
# But then we won't receive data if even one charecter has been corrupted
# This way we still can receive data, even if not all of it can be used


def isDataOK():
    allowed_chars = [",", ".", "$"]
    for char in base_station_data:
        if not (char.isdigit() or char in allowed_chars):
            return False
    return True

# Connects to serial port and reads data from it


def serialDataFunction():
    # Opens serial data port
    base_station = serial.Serial("COM8", 9600, timeout=2)
    while True:
        try:
            # If serial connection has been lost, tries to reconnect back
            if(base_station == None):
                base_station = serial.Serial("COM8", 9600, timeout=2)
                print("Reconnecting")
            # Reads data from serial port
            # It blocks function from progressing untill some data has been received
            base_station_data = str(base_station.readline())
            # Removes useless data from string
            base_station_data = base_station_data[3:-6]
            # If data is not corrupted add data to both data lists
            if isDataOK():
                raw_data.append(base_station_data)
                displayed_data.append(base_station_data)
            # If some data has been corrupted, doesn't add it to list that
            # is used to update data to graphs
            else:
                raw_data.append(base_station_data)
        except:
            # If something goes wrong closes port and tries again
            if(not(base_station == None)):
                base_station.close()
                base_station = None
                print("Disconnecting")

            print("No Connection")
            time.sleep(0.25)


if __name__ == '__main__':
    # If serial is used, starts a thread that runs in background and collects data from serial port
    if com_used:
        serialThread = threading.Thread(target=serialDataFunction, daemon=True)
        serialThread.start()
    # Creates a new application process
    app = QtWidgets.QApplication([])
    # Creates the main window
    window = Window()
    # If app is closed, stop running code
    sys.exit(app.exec_())
