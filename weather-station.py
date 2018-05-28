import sqlite3
import matplotlib

matplotlib.use('Agg')

from math import isnan
from threading import Thread
from time import sleep
from datetime import datetime
from flask import Flask, render_template
from grovepi import dht
from matplotlib import pyplot
from matplotlib.dates import date2num
from dateutil import parser
from urllib.request import urlopen
from urllib.parse import quote

app = Flask(__name__)


@app.route('/')
def index():
    # On recupere la température et l'humidité actuelle, à l'heure où on se connecte au site
    [ctemp, chumidity] = dht(4, 1)  # 4 pour le port du GrovePi / 1 pour le capteur de type DHT22
    # On transmet les mesures à la page web
    return render_template('index.html', temperature=ctemp, humidity=chumidity)


def update_db():
    while True:
        # On mesure la température et l'humidité
        [temp_m, hum_m] = dht(4, 1)
        if not isnan(temp_m) and not isnan(hum_m) and hum_m != 0.0:
            # On recupère l'heure de la mesure qu'on reformatte au format conseillé
            datetime_m = datetime.now().strftime("%y-%m-%d %H:%M:%S.%f")
            datetime_m = datetime_m[:-3]

            # On se connecte à la base de données (BDD)
            conn_m = sqlite3.connect('/home/pi/weather-station/weather-data.db')
            # On ajoute la mesure
            conn_m.execute("INSERT INTO MEASUREMENTS (TEMPERATURE, HUMIDITY, DATETIME_M) VALUES (?, ?, ?);",
                           (temp_m, hum_m, datetime_m))
            # On valide l'ajout
            conn_m.commit()
            # On ferme la base
            conn_m.close()

            # On met à jour le graphique d'évolution de la méteo que va afficher la page
            graph_data()

            print("Temperature : %.02f / Humidite : %.02f / Heure : %s" % (temp_m, hum_m, datetime_m))

            # EMONCMS
            # On prépare les données
            json = "{temp:" + "%.2f" % temp_m + ",humidity:" + "%.2f" % hum_m+ "}"
            # On prépare l'URL
            emonapikey = "3e48fb506d975511674f59465a7df345"
            url = "http://emoncms.org/" + "input/post.json?node=1&apikey=" + emonapikey + "&json=" + quote(json)
            # On envoie les données sur le serveur Emoncms
            urlopen(url)

            # On ajoute une mesure toutes les 10s
            sleep(10)


def graph_data():
    # On se connecte à la BDD
    conn_g = sqlite3.connect('/home/pi/weather-station/weather-data.db')
    # On récupère les mesures de la plus ancienne à la plus récente
    cursor = conn_g.execute(
        'SELECT * FROM (SELECT TEMPERATURE, HUMIDITY, DATETIME_M FROM MEASUREMENTS ORDER BY ROWID DESC LIMIT 10) ORDER BY ROWID ASC ;')
    data = cursor.fetchall()
    # On ferme la BDD
    conn_g.close()

    # On prépare les tableaux qui vont contenir les données des mesures
    temperature = []
    humidity = []
    datetime_m = []

    # On remplit les tableaux
    for row in data:
        temperature.append(row[0])
        humidity.append(row[1])
        datetime_m.append(parser.parse(row[2]))

    # On reformatte les dates
    dates = [date2num(t) for t in datetime_m]

    # On crée une figure grâce à Matplotlib
    fig = pyplot.figure()
    ax1 = fig.add_subplot(111)
    ax1.set_title("Evolution de la temperature et de l'humidite")

    # On configure l'axe X pour les dates des mesures
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d.%m.%Y %H:%M'))

    # On affiche la température sur l'axe Y
    ax1.set_ylabel("Temperature [C]")
    ax1.plot_date(dates, temperature, '-', label="Temperature", color='b')

    # On affiche l'humidité sur l'axe Y
    ax2 = ax1.twinx()
    ax2.set_ylabel("Humidity [% RH]")
    ax2.plot_date(dates, humidity, '-', label="Humidite", color='g')

    # On configure l'axe X pour afficher les dates des mesures
    fig.autofmt_xdate(rotation=60)
    fig.tight_layout()

    # On affiche la grille et les légendes
    ax1.grid(True)
    ax1.legend(loc='best', framealpha=0.5)
    ax2.legend(loc='best', framealpha=0.5)

    # On sauvegarde le graphique
    pyplot.savefig("/home/pi/weather-station/static/img/graph.png")


if __name__ == "__main__":
    # On crée une BDD si nécessaire
    conn = sqlite3.connect('/home/pi/weather-station/weather-data.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS MEASUREMENTS(
              ID INTEGER PRIMARY KEY,
              TEMPERATURE        REAL    NOT NULL,
              HUMIDITY           REAL    NOT NULL,
              DATETIME_M               TEXT    NOT NULL);''')
    conn.close()
    # On démarre le thread d'arrière-plan pour mettre à jour la BDD et le graphique
    Thread(target=update_db).start()
    # On démarre le serveur Flask sur le port 5000
    app.run(host='192.168.43.16', debug=False)