import requests
import sys
import os
import json
import time
import threading
from pysolar.solar import *
import datetime
import pytz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from rad_real import *
import numpy as np
from math import sqrt

#en caso de que no se pase ningun argumento por consola
if len(sys.argv) == 1:
	print("Set thing name as argument")
	sys.exit()

#si el argumento pasado no es un json se sale de script
try:
	parameters = json.loads(sys.argv[1])
	print(parameters['devices'])
	for device in parameters['devices']:
		print(parameters['devices'][device])
	if not isinstance(parameters["devices"], dict):
		print("No se ha metido la lista de devices")
		sys.exit()
except:
	print("Argumento no valido")
	sys.exit()

#conversion modelo a funcion dentro del script
modelos = {'cindex':'modeloCINDEX'}

#escenario
escenario = parameters['escenario']

#umbral
umbral = float(parameters['umbral'])

#datos obtener token
url_token = "https://access.bosch-iot-suite.com/token"
grant_type = "client_credentials"
client_id = "9c19c7bb-4355-48ed-b064-14f92fe6776e"
client_secret = "T2gApLVcdeaaL4cmJD-K-Ob6rB"
scope = "service:iot-things-eu-1:4a9df6cc-5ade-4293-928c-6e302b4f02d7_things/full-access"

#datos para csk
timezone = pytz.timezone(parameters['timezone'])

#urls radiacion en Bosch IoT Things %s sera cada device
url_radiacion_real_generic = "https://things.eu-1.bosch-iot-suite.com/api/2/things/tfm.iot:%s/features/nodo_real/properties"
url_radiacion_modelo_generic = "https://things.eu-1.bosch-iot-suite.com/api/2/things/tfm.iot:%s/features/modelo/properties"

token = None


#print("delay_seconds", delay_seconds)
#datos del intervalo
date_ini = timezone.localize(datetime.datetime.strptime(parameters['interval'][0], '%Y-%m-%d %H:%M:%S'))
date_final = timezone.localize(datetime.datetime.strptime(parameters['interval'][1], '%Y-%m-%d %H:%M:%S'))
delay_seconds = int(parameters['interval'][2])

#timeout para obtener de nuevo el token de autenticación 
timeout_token = 1200

#escoger el set de datos reales
data_real_dict = "data_real_" + parameters['interval'][0].replace(" ","__").replace(":","").replace("-","")[:-2] + "__" + parameters['interval'][1].split(" ")[-1].replace(":","")[:-2] + "__" + parameters['interval'][2]
data_real = eval(data_real_dict)


#funcion para obtener token de autenticacion
def getTokenAuthentication():
	global token

	thread_name = threading.current_thread().getName()

	headers = {
		'Accept': 'application/json',  
		'Content-Type': 'application/x-www-form-urlencoded'
	}

	data = {'grant_type':grant_type, 'client_id':client_id, 'client_secret':client_secret, 'scope':scope}

	#si hay un thread actualizando propiedades espera a que acabe
	for device in parameters['devices']:
		event_things_list[device].wait()

	#paralizar threads para que no hagan peticiones mientras se actualiza el token
	thread_token_event.clear()

	response = requests.post(url_token, headers=headers, data=data)

	data_string = response.content.decode('utf-8')
	data_dict = json.loads(data_string)

	token = data_dict['access_token']

	print(thread_name, "Actualizado token")

	#liberar threads para que hagan de nuevo peticiones
	thread_token_event.set()

	#crear nuevo timer para que vuelva a pedir token en un intervalo de tiempo dado
	threadToken = threading.Timer(timeout_token, getTokenAuthentication)
	threadToken.name = "ThreadToken"
	threadToken.start()


#funcion para cada thread de cada device
def threadFunction(device, model, date_ini, date_final):
	#autocompletar urls con device correspondiente
	url_radiacion_real =  url_radiacion_real_generic % device
	url_radiacion_modelo = url_radiacion_modelo_generic % device
	date = date_ini

	#dependiendo si el escenario es simulado o no necesitamos estas variables iniciales
	if escenario in "simulado":
		cindex = 0.0
		index = 0

	#mientras dure el intervalo de tiempo dado
	while date < date_final:

		irad = 0.0
		date += datetime.timedelta(seconds=delay_seconds)

		#si el escenario es real obtener medidas de los gemelos virtuales y ejecutar el modelo
		if escenario in "real":
			#
			time.sleep(delay_seconds)
			#si se esta pidiendo token nuevo esperar a que termine
			thread_token_event.wait()

			headers = {
				'Accept': 'application/json',
				'Content-Type': 'application/json',
				'Authorization': "Bearer " + token
			}

			#evitar pedir token mientras se hace una request a things
			event_things_list[device].clear()

			rad_real = requests.get(url_radiacion_real, headers=headers)
	
			#ejecutar modelo y actualizar la radiacion
			irad_model, date_cindex = eval(model)(rad_real, device, date)
			irad = round(irad_model,3)

			response = requests.put(url_radiacion_modelo + "/radiacion", headers=headers, data=str(irad))
			response = requests.put(url_radiacion_modelo + "/timestamp", headers=headers, data='"' + date.strftime("%Y-%m-%d %H:%M:%S") + '"')

			#comprobar si ha variado cindex y anotarlo como cambio si procede
			contarNumeroEnviosNodo(date_cindex, device)

		#si el escenario es simulado obtener calcular todo dentro del mismo script
		elif escenario in "simulado":

			cindex, irad = modeloSimulacion(data_real[device][index], cindex, date, device)
			index += 1

		#anadir radiacion modelo y hora en una tupla al array para luego representar
		rad_hora[device].append((date.replace(tzinfo=None), irad))

		#print(rad_hora[device])

		print("Radiacion modelo", device, "es:", irad, "con timestamp", date.strftime("%Y-%m-%d %H:%M:%S"))

		#permitir pedir token si fuese necesario
		event_things_list[device].set()


####################################### funciones modelos #######################################


#modelo para ejecutar en tiempo real
def modeloCINDEX(data, device, date):
	#data contiene cindex y timestamp

	rad_real_str = data.content.decode('utf-8')
	rad_real_json = json.loads(rad_real_str)

	cindex = rad_real_json['cindex']
	timestamp = rad_real_json['timestamp']

	print("El cindex", device, "es:", cindex, "con timestamp", timestamp)

	altitude = get_altitude(float(parameters['devices'][device][0]), float(parameters['devices'][device][1]), date)
	radiacion = radiation.get_radiation_direct(date, altitude)

	print("RADIACION CSK:", radiacion, "date:", date)

	rad_cindex = radiacion * cindex

	return rad_cindex, timestamp

#el modelo de simulacion ejecuta tanto la parte del nodo real como del thread del gemelo virtual
def modeloSimulacion(rad_real, cindex_ant, date, device):
	cindex = cindex_ant

	altitude = get_altitude(float(parameters['devices'][device][0]), float(parameters['devices'][device][1]), date)
	rad_csk = radiation.get_radiation_direct(date, altitude)

	current_cindex = rad_real/rad_csk

	diff = abs(cindex_ant-current_cindex)

	if diff > umbral or cindex_ant == 0.0:
		cindex = current_cindex
		n_envios[device] += 1

	print(n_envios)

	print("El cindex", device, "es:", cindex)

	altitude = get_altitude(float(parameters['devices'][device][0]), float(parameters['devices'][device][1]), date)
	radiacion = radiation.get_radiation_direct(date, altitude)

	rad_cindex = round(radiacion * cindex, 3)

	return cindex, rad_cindex

####################################### funciones estudio ######################################

def contarNumeroEnviosNodo(date, device):

	if date != "":
		date_nodo_real = timezone.localize(datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S'))

		if date_nodo_real > dates_devices[device]:
			n_envios[device] += 1
			dates_devices[device] = date_nodo_real

	print(n_envios)

def generarGraficaCompararRadiaciones(device):

	x = [i[0] for i in rad_hora[device]]
	y = [i[1] for i in rad_hora[device]]

	title = "Gráfica radiaciones de {} fecha {} con umbral {}".format(device, x[0].strftime("%d-%m-%Y"), umbral)

	fig, ax = plt.subplots()
	formatter = mdates.DateFormatter("%H:%M")
	ax.xaxis.set_major_formatter(formatter)

	fig.subplots_adjust(bottom=0.3)
	plt.plot(x, y, "-b" ,label = "modelo")
	plt.plot(x, data_real[device], "-r" ,label = "real")
	plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
	plt.title(title, loc='center')
	plt.xlabel("Hora(hh:mm)")
	plt.ylabel("Radiación (W/m2)")
	path_graf = main_path + "/" + device + "/" + "comp_radiaciones.png"
	plt.savefig(path_graf, bbox_inches="tight")
	plt.close()

def generarGraficaError(device):
	x = [i[0] for i in rad_hora[device]]
	y = list(np.absolute(np.array([i[1] for i in rad_hora[device]]) - np.array(data_real[device])))

	title = "Error radiación de {} fecha {} con umbral {}".format(device, x[0].strftime("%d-%m-%Y"), umbral)

	fig, ax = plt.subplots()
	formatter = mdates.DateFormatter("%H:%M")
	ax.xaxis.set_major_formatter(formatter)

	fig.subplots_adjust(bottom=0.3)
	plt.plot(x, y, "-r" ,label = "error")
	plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
	plt.title(title, loc='center')
	plt.xlabel("Hora(hh:mm)")
	plt.ylabel("Radiación (W/m2)")
	path_graf = main_path + "/" + device + "/" + "diff_error_radiacion.png"
	plt.savefig(path_graf, bbox_inches="tight")
	plt.close()


def error_cuadratico_medio(device):
	error_cua_med = 0

	errors = np.power(np.array([i[1] for i in rad_hora[device]]) - np.array(data_real[device]),2)
	
	error_cua_med = sqrt(np.sum(errors)/errors.size)

	porcentajes_error = error_cua_med/np.array(data_real[device])

	porcentaje_max = np.amax(porcentajes_error)*100

	porcentaje_error_med = np.sum(porcentajes_error)/porcentajes_error.size*100

	print("El error cuadrático medio es:", error_cua_med)
	print("El porcentaje de error medio es:", porcentaje_error_med)
	print("El porcentaje de error máximo es:", porcentaje_max)

	return error_cua_med, porcentaje_error_med, porcentaje_max

def generar_reporte(device):
	error, porcentaje_med, porcentaje_max = error_cuadratico_medio(device)
	file = main_path + "/" + device + "/" + "report.txt"
	report = {"n_envios" : n_envios[device], "err_cua_med" : round(error,3), "porcentaje_error": round(porcentaje_med,3), "porcentaje_max": round(porcentaje_max,3)}
	report = json.dumps(report)
	with open(file, 'w') as f:
		f.write(str(report))
		f.close()

########################################### main ##############################################

#crear directorio para guardar graficas e informe
# fecha__horaini__horafin__intervalo_umbral
main_path = "./informes/" + date_ini.strftime("%Y%m%d") + "__" + date_ini.strftime("%H%M") + "__" + date_final.strftime("%H%M") + "__" + str(delay_seconds) + "__" + str(umbral)
os.mkdir(main_path)

#eventos entre threads
thread_token_event = threading.Event()

#crear un evento por device
event_things_list = {}
for device in parameters['devices']:
	e = threading.Event()
	event_things_list[device] = e
	e.set()

#thread para conseguir el token y ponemos a True el evento para que haga la request de primeras
#thread_thing_event.set()
threadToken = threading.Timer(0, getTokenAuthentication)
threadToken.name = "ThreadToken"
threadToken.start()

#crear threads para cada device
thread_devices = [] #lista con cada thread generado
n_envios = {} #diccionario con dispositivos y numero de envios
dates_devices = {} #diccionario con el datetime en el que va cada thread
rad_hora = {} #diccionario que guarda los datos calculados por cada thread
diff_rad_hora = {} #diccionario que guarda diferencia entre radiaciones por cada thread
for device in parameters['devices']:
	os.mkdir(main_path + "/" + device)
	n_envios[device] = 0
	rad_hora[device] = []
	diff_rad_hora[device] = []
	dates_devices[device] = date_ini
	t = threading.Thread(name=device, target=threadFunction, args=(device, modelos[parameters['model']], date_ini, date_final))
	thread_devices.append(t)

#iniciar todos los threads
for thread in thread_devices:
	thread.start()

#esperar a que todos los threads terminen
for thread in thread_devices:
	thread.join()

for device in parameters['devices']:
	generarGraficaCompararRadiaciones(device)
	generarGraficaError(device)
	generar_reporte(device)