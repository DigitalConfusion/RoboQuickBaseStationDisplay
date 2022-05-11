# PYQT
from selectors import EpollSelector
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import folium

# Libraries
import sys
import threading
import serial
from random import randint

borderColor = QColor(180, 180, 180)
borderWidth = 3

# Serial data port
base_station = serial.Serial("COM1", 9600)

# String that we will receive from Serial port
base_station_data = ""
# Place to store data that can be corrupted
raw_data = []
# Place to store data that doesn't have any corruptions in it
# This is the data that will be used to split string to variables
displayed_data = []
# Variables from split data string
receive_time = ""
longitude = 0.0
latitude = 0.0
speed = 0.0
altitude = 0.0
temperature = 0.0
humidity = 0.0
pressure = 0.0
rssi = 0
snr = 0

# Lists for storing received data
data_recieve_time = []
data_longitude = []
data_latitude = []
data_speed = []
data_altitude = []
data_temperature = []
data_humidity = []
data_pressure = []


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.title = "Base station data display"
        self.left = 50
        self.top = 50
        self.width = 1500
        self.height = 900
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setAutoFillBackground(True)
        p = self.palette()
        # Here you can change colour of the background
        p.setColor(self.backgroundRole(), QColor(120, 120, 120))
        self.setPalette(p)

        # Temperature
        self.label_temperature = QLabel(self)
        self.label_temperature.setText("Temperature")
        # X, Y, Height, Width
        self.label_temperature.setGeometry(20, 17, 420, 20)
        self.label_temperature.setFont(QFont("Arial", 18))
        self.label_temperature.setStyleSheet("QLabel {color : rgb(150, 150, 150)}")
        self.label_temperature.setAlignment(QtCore.Qt.AlignCenter)

        self.graphWidget_temperature = pg.PlotWidget(self)
        # X, Y, Height, Width
        self.graphWidget_temperature.setGeometry(20, 50, 440, 350)
        self.graphWidget_temperature.setBackground(None)
        self.graphWidget_temperature.setYRange(10, 35, padding=0.04)

        # Colour and width of data line in plot
        data_pen = pg.mkPen(color=(255, 7, 58), width=3)
        self.dataLine_temperature = self.graphWidget_temperature.plot(data_recieve_time, data_temperature, pen=data_pen)

        # Humidity
        self.label_humidity = QLabel(self)
        self.label_humidity.setText("Humidity")
        self.label_humidity.setGeometry(490, 17, 440, 20)
        self.label_humidity.setFont(QFont("Arial", 18))
        self.label_humidity.setStyleSheet("QLabel {color : rgb(150, 150, 150)}")
        self.label_humidity.setAlignment(QtCore.Qt.AlignCenter)

        self.graphWidget_humidity = pg.PlotWidget(self)
        self.graphWidget_humidity.setGeometry(490, 50, 440, 350)
        self.graphWidget_humidity.setBackground(None)
        self.graphWidget_humidity.setYRange(0, 100, padding=0.04)

        data_pen = pg.mkPen(color=(255, 237, 39), width=3)
        self.dataLine_humidity = self.graphWidget_humidity.plot(data_recieve_time, data_humidity, pen=data_pen)

        # Air Pressure
        self.label_pressure = QLabel(self)
        self.label_pressure.setText("Air Pressure")
        self.label_pressure.setGeometry(20, 412, 420, 20)
        self.label_pressure.setFont(QFont("Arial", 18))
        self.label_pressure.setStyleSheet("QLabel {color : rgb(150, 150, 150)}")
        self.label_pressure.setAlignment(QtCore.Qt.AlignCenter)

        self.graphWidget_pressure = pg.PlotWidget(self)
        self.graphWidget_pressure.setGeometry(20, 443, 440, 350)
        self.graphWidget_pressure.setBackground(None)
        self.graphWidget_pressure.setYRange(700000, 1100000, padding=0.04)

        data_pen = pg.mkPen(color=(0, 200, 255), width=3)
        self.dataLine_pressure = self.graphWidget_pressure.plot(data_recieve_time, data_pressure, pen=data_pen)

        # Altitude
        self.label_altitude = QLabel(self)
        self.label_altitude.setText("Altitude")
        self.label_altitude.setGeometry(490, 412, 440, 20)
        self.label_altitude.setFont(QFont("Arial", 18))
        self.label_altitude.setStyleSheet("QLabel {color : rgb(150, 150, 150)}")
        self.label_altitude.setAlignment(QtCore.Qt.AlignCenter)

        self.graphWidget_altitude = pg.PlotWidget(self)
        self.graphWidget_altitude.setGeometry(490, 443, 440, 350)
        self.graphWidget_altitude.setBackground(None)
        self.graphWidget_altitude.setYRange(0, 2000, padding=0.04)

        data_pen = pg.mkPen(color=(57, 255, 20), width=3)
        self.dataLine_altitude = self.graphWidget_altitude.plot(data_recieve_time, data_altitude, pen=data_pen)

        # Speed
        self.label_speed = QLabel(self)
        self.label_speed.setText("Speed")
        self.label_speed.setGeometry(940, 17, 440, 20)
        self.label_speed.setFont(QFont("Arial", 18))
        self.label_speed.setStyleSheet("QLabel {color : rgb(150, 150, 150)}")
        self.label_speed.setAlignment(QtCore.Qt.AlignCenter)

        self.graphWidget_speed = pg.PlotWidget(self)
        self.graphWidget_speed.setGeometry(940, 50, 440, 350)
        self.graphWidget_speed.setBackground(None)
        self.graphWidget_speed.setYRange(0, 2000, padding=0.04)

        data_pen = pg.mkPen(color=(57, 255, 20), width=3)
        self.dataLine_speed = self.graphWidget_speed.plot(data_recieve_time, data_speed, pen=data_pen)

        # Display everything
        self.show()

    # Update data in plots
    def update_plot_data(self):
        self.dataLine_temperature.setData(data_recieve_time, data_temperature)
        self.dataLine_humidity.setData(data_recieve_time, data_humidity)
        self.dataLine_pressure.setData(data_recieve_time, data_pressure)
        self.dataLine_altitude.setData(data_recieve_time, data_altitude)

    # Shows the lines that seperates graphs
    def paintEvent(self, event):
        global borderColor, borderWidth

        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Pen for drawing the sensor box borders
        painter.setPen(QPen(borderColor, borderWidth))

        # Main sensor box borders
        painter.drawRect(10, 10, 940, 1000)

        # Sensor box input data retangles
        painter.drawRect(10, 800, 940, 210)

        # Drawing the graph separators
        painter.drawLine(475, 10, 475, 800)
        painter.drawLine(10, 405, 945, 405)


class Controller:

    def __init__(self):
        pass

    def show_sensor_window(self):
        self.sensor_window = MainWindow()
        self.sensor_window.show()


def main():
    app = QApplication(sys.argv)
    controller = Controller()
    controller.show_sensor_window()
    sys.exit(app.exec_())

# Checks if data that was received from Cansat isn't corrupted, that it doesn't contain
# any charachters that it shoudn't


def isDataOK():
    allowed_chars = [",", ":", "."]
    no_corruption = True
    for char in base_station_data:
        if not (char.isdigit()) or (char not in allowed_chars):
            no_corruption = False
            break
    return no_corruption

# Splits latest data and appends it to the lists to display updated data


def appendDataLists():
    global data_recieve_time, data_longitude, data_latitude, data_speed, data_altitude, data_temperature, data_humidity, data_pressure
    data = displayed_data[-1].split(",")
    data_recieve_time = data[0]
    data_longitude = data[1]
    data_latitude = data[2]
    data_speed = data[3]
    data_altitude = data[4]
    data_temperature = data[5]
    data_humidity = data[6]
    data_pressure = data[7]

# Reads data from Serial port, if data isn't corruptedm append it
# to both data lists, and split data and save it to lists to update the graphs


def serialDataFunction():
    while True:
        base_station_data = str(base_station.readline())
        if isDataOK():
            raw_data.append(base_station_data)
            displayed_data.append(base_station_data)
            appendDataLists()
        else:
            raw_data.append(raw_data)


# Main function
if __name__ == "__main__":
    # Starts the function in background that monitors
    # serial port for any new data
    serialThread = threading.Thread(target=serialDataFunction)
    serialThread.start()

    # Runs the rest of the programm
    main()
