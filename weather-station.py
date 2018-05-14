import sqlite3
import matplotlib

matplotlib.use('Agg')

from math import isnan
from threading import Thread
from time import sleep
from matplotlib import pyplot
from matplotlib.dates import date2num
from datetime import datetime
from dateutil import parser
from flask import Flask, render_template
from grovepi import dht

app = Flask(__name__)


@app.route('/')
def index():
    [ctemp, chumidity] = dht(4, 1)
    return render_template('index.html', temperature=ctemp, humidity=chumidity)


def update_db():
    while True:
        [temp_m, hum_m] = dht(4, 1)
        if not isnan(temp_m) and not isnan(hum_m) and hum_m != 0.0:
            datetime_m = datetime.now().strftime("%y-%m-%d %H:%M:%S.%f")
            datetime_m = datetime_m[:-3]

            conn_m = sqlite3.connect('/home/pi/weather-station/weather-data.db')
            conn_m.execute("INSERT INTO MEASUREMENTS (TEMPERATURE, HUMIDITY, DATETIME_M) VALUES (?, ?, ?);",
                           (temp_m, hum_m, datetime_m))
            conn_m.commit()
            conn_m.close()

            graph_data()

            print("Temperature : %.02f / Humidite : %.02f / Heure : %s" % (temp_m, hum_m, datetime_m))
            sleep(10)


def graph_data():
    conn_g = sqlite3.connect('/home/pi/weather-station/weather-data.db')
    cursor = conn_g.execute(
        'SELECT * FROM (SELECT TEMPERATURE, HUMIDITY, DATETIME_M FROM MEASUREMENTS ORDER BY ROWID DESC LIMIT 10) ORDER BY ROWID ASC ;')
    data = cursor.fetchall()

    temperature = []
    humidity = []
    datetime_m = []

    for row in data:
        temperature.append(row[0])
        humidity.append(row[1])
        datetime_m.append(parser.parse(row[2]))

    dates = [date2num(t) for t in datetime_m]

    fig = pyplot.figure()
    ax1 = fig.add_subplot(111)
    ax1.set_title("Evolution de la temperature et de l'humidite")

    # Configure x-ticks
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d.%m.%Y %H:%M'))

    # Plot temperature data on left Y axis
    ax1.set_ylabel("Temperature [C]")
    ax1.plot_date(dates, temperature, '-', label="Temperature", color='b')

    # Plot humidity data on right Y axis
    ax2 = ax1.twinx()
    ax2.set_ylabel("Humidity [% RH]")
    ax2.plot_date(dates, humidity, '-', label="Humidite", color='g')

    # Format the x-axis for dates (label formatting, rotation)
    fig.autofmt_xdate(rotation=60)
    fig.tight_layout()

    # Show grids and legends
    ax1.grid(True)
    ax1.legend(loc='best', framealpha=0.5)
    ax2.legend(loc='best', framealpha=0.5)

    pyplot.savefig("/home/pi/weather-station/static/img/graph.png")
    conn_g.close()


if __name__ == "__main__":
    conn = sqlite3.connect('/home/pi/weather-station/weather-data.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS MEASUREMENTS(
              ID INTEGER PRIMARY KEY,
              TEMPERATURE        REAL    NOT NULL,
              HUMIDITY           REAL    NOT NULL,
              DATETIME_M               TEXT    NOT NULL);''')
    conn.close()

    Thread(target=update_db).start()
    app.run(host='192.168.43.16', debug=False)
