import socket
import sys
import time
import paho.mqtt.publish as publish
import pytz
import datetime
import json

#'{"interval" : ["2011-05-01 16:00:00", "2011-05-01 16:45:00"], "timezone" : "US/Hawaii"}'

if len(sys.argv) == 1:
    print("Set thing name as argument")
    sys.exit()

try:
    parameters = json.loads(sys.argv[1])
except:
    print("Argumento no valido")
    sys.exit()

#variables
LOCALHOST = "aaaa::1"
LOCAL_PORT = 5678
MQTT_HOST = "mqtt.bosch-iot-hub.com"
MQTT_PORT = 8883
topic = "telemetry"

#credenciales digital twins iot hub
credentials = [{"username":"tfm.iot_device-01@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-01"},
{"username":"tfm.iot_device-02@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-02"},
{"username":"tfm.iot_device-03@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-03"},
{"username":"tfm.iot_device-04@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-04"},
{"username":"tfm.iot_device-05@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-05"},
{"username":"tfm.iot_device-06@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-06"},
{"username":"tfm.iot_device-07@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-07"},
{"username":"tfm.iot_device-08@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-08"},
{"username":"tfm.iot_device-09@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-09"},
{"username":"tfm.iot_device-010@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-010"},
{"username":"tfm.iot_device-011@t4a9df6cc5ade4293928c6e302b4f02d7_hub","password":"device-011"}]

timezone = pytz.timezone(parameters['timezone'])

date_ini = timezone.localize(datetime.datetime.strptime(parameters['interval'][0], '%Y-%m-%d %H:%M:%S'))
date_final = timezone.localize(datetime.datetime.strptime(parameters['interval'][1], '%Y-%m-%d %H:%M:%S'))

cert = "/home/aitor/iothub.crt"


def getMoteId(address):
    ip = address[0]
    if ip[-1] == "a":
        ip = ip[:-1] + "10"
    elif ip[-1] == "b":
        ip = ip[:-1] + "11"
    elif ip[-1] == "c":
        ip = ip[:-1] + "12"
    return int(ip.split(":")[-1]) -1 #(el nodo 1 es el router de borde)

def getCredentials(mote_id):
    return credentials[mote_id-1]


# Create a UDP socket
sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

# Bind the socket to the port
server_address = (LOCALHOST, LOCAL_PORT)
print('starting up on {} port {}'.format(*server_address))
sock.bind(server_address)

while date_ini < date_final:
    ts_ini = time.time()
    print('\nwaiting to receive message')
    data, address = sock.recvfrom(4096)
    
    mote_id = getMoteId(address)
    auth = getCredentials(mote_id)

    ts_diff = time.time() - ts_ini
    date_ini += datetime.timedelta(seconds=int(ts_diff))
    payload = '{"topic":"tfm.iot/device-0' + str(mote_id) + '/things/twin/commands/modify","path":"/features/nodo_real","value":{"properties":{"cindex": ' + str(float(data)) + ', "timestamp": "' + date_ini.strftime("%Y-%m-%d %H:%M:%S") + '"}}}'
    print(payload)
  
    #enviar mediante mqtt al nodo virtual
    publish.single(topic, payload=payload, hostname=MQTT_HOST, port=MQTT_PORT, auth=auth, tls={'ca_certs':cert})
    print("MQTT PUBLICADO: ",data)