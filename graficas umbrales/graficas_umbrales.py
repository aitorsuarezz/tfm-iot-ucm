import matplotlib.pyplot as plt
import os
import glob
import sys
import json
from matplotlib import colors as mcolors
from math import log
import numpy as np

from power_real import *
from power_isolated import *

#consumo energetico
cpu_power = 22.5 #mA
lpm_power = 11.6 #mA
tx_power = 150 #mA

V = 3.7 #V
tiempo = 38*60 #segundos

########################################

devices = ["device-01", "device-02", "device-03", "device-04", "device-05", "device-06", "device-07", "device-08", "device-09", "device-010", "device-011"]

colors_dev = {"device-01" : 'coral', "device-02" : 'yellow', "device-03" : 'cadetblue', "device-04" : 'darkmagenta', "device-05" : 'fuchsia', "device-06" : 'deepskyblue', "device-07" : 'magenta', "device-08" : 'steelblue', "device-09" : 'olive', "device-010" : 'saddlebrown', "device-011" : 'peru'}

colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)

# Sort colors by hue, saturation, value and name.
by_hsv = sorted((tuple(mcolors.rgb_to_hsv(mcolors.to_rgba(color)[:3])), name)
                for name, color in colors.items())
sorted_names = [name for hsv, name in by_hsv]

n_envios = 114

devices_2_axis = ["device-01", "device-08", "device-011"]

#argumento del script la fecha del escenario y la medicion en segundos
if len(sys.argv) == 1:
	print("Set date as argument")
	sys.exit()

name = str(sys.argv[1])


#grafica que muestra el porcenaje de envio con respecto al umbral
def generarGraficaEnvios():

	title = "Gráfica umbrales/envios fecha {}".format(name)

	fig, ax = plt.subplots()
	fig.subplots_adjust(bottom=0.3)

	umbrales_graf = ["0"] + umbrales

	for device in devices:
		plt.plot(umbrales_graf, envios[device], colors[colors_dev[device]], label=device)
	
	plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
	plt.title(title, loc='center')
	plt.xlabel("umbral")
	plt.ylabel("Porcentaje envios (%)")
	path_graf = "informes/graficas_" + name + "/umbrales_envios.png"
	plt.savefig(path_graf, bbox_inches="tight")
	plt.close()


#grafica que muestra el error cuadratico con respecto al umbral
def generarGraficaError():

	title = "Gráfica umbrales/error_cuad fecha {}".format(name)

	fig, ax = plt.subplots()
	fig.subplots_adjust(bottom=0.3)

	umbrales_graf = ["0"] + umbrales

	for device in devices:
		plt.plot(umbrales_graf, error_cuad_med[device], colors[colors_dev[device]], label=device)
	
	plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
	plt.title(title, loc='center')
	plt.xlabel("umbral")
	plt.ylabel("Error cuadrático medio")
	path_graf = "informes/graficas_" + name + "/umbrales_error_cua.png"
	plt.savefig(path_graf, bbox_inches="tight")
	plt.close()


#grafica que muestra el error y el envio con respecto al umbral
def generarGraficaTwoAxisY():

	title = "Gráfica umbrales/error_cuad fecha {}".format(name)

	fig, ax = plt.subplots()
	fig.subplots_adjust(bottom=0.3)

	ax2 = ax.twinx()

	umbrales_graf = ["0"] + umbrales

	for device in devices_2_axis:
		ax2.plot(umbrales_graf, error_cuad_med[device], colors[colors_dev[device]], linestyle="--", label=device)
		ax.plot(umbrales_graf, envios[device], colors[colors_dev[device]], label=device)
	
	ax.legend(bbox_to_anchor=(-0.12, 1), loc='upper right')
	ax2.legend(bbox_to_anchor=(1.12, 1), loc='upper left')
	plt.title(title, loc='center')
	ax.set_xlabel("umbral")
	ax2.set_ylabel("Error cuadrático medio")
	ax.set_ylabel("Porcentaje envios (%)")
	path_graf = "informes/graficas_" + name + "/umbrales_error_cua_envios.png"
	plt.savefig(path_graf, bbox_inches="tight")
	plt.close()


#grafica que muestra el diagrama de barras de consumor energetico con respecto al umbral
def generarGraficaPowerRealPer():
	width = 0.5
	umbrales_graf = ["0"] + umbrales
	for device in devices_2_axis:
		title = "Gráfica {} consumos {}".format(name, device)
		fig, ax = plt.subplots()
		cpus = [power_real_all[device]["cpu"]]
		lpms = [power_real_all[device]["lpm"]]
		txs = [power_real_all[device]["tx"]]
		listens = [power_real_all[device]["listen"]]
		for umbral in umbrales:
			power_dict = "power_real_" + name + "__" + umbral.replace(".","")
			cpus.append(eval(power_dict)[device]["cpu"])
			lpms.append(eval(power_dict)[device]["lpm"])
			txs.append(eval(power_dict)[device]["tx"])
			listens.append(eval(power_dict)[device]["listen"])
		
		cpus = np.array(cpus)
		lpms = np.array(lpms)
		txs = np.array(txs)
		listens = np.array(listens)

		#calcular consumos

		cpus_power = cpus/100 * tiempo * cpu_power * V / 1000
		lpms_power = lpms/100 * tiempo * lpm_power * V / 1000
		txs_power = (txs+listens)/100 * tiempo * tx_power * V / 1000

		ax.bar(umbrales_graf, cpus_power, width, color='r', label='cpu')
		#ax.bar(umbrales_graf, lpms, width, color='g', label='lpm')
		ax.bar(umbrales_graf, txs_power, width, bottom=cpus_power, color='yellow', label='radio')
		ax.bar(umbrales_graf, lpms_power, width, bottom=cpus_power+txs_power, color='b', label='lpm')
		
		ax.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
		ax.set_xlabel("umbral")
		ax.set_ylabel("Consumo energético (J)")
		plt.title(title, loc='center')
		path_graf = "informes/graficas_" + name + "/consumos_" + device + ".png"
		plt.savefig(path_graf, bbox_inches="tight")
		plt.close()


#grafica que muestra linea de consumo radio real con respecto al umbral
def generarGraficaPowerTxReal():
	title = "Gráfica consumo aislado {}".format(name)
	umbrales_graf = ["0"] + umbrales

	fig, ax = plt.subplots()
	fig.subplots_adjust(bottom=0.3)
	
	for device in devices_2_axis:
		title = "Gráfica consumo real {} para {}".format(name, device)
		txs = [power_real_all[device]["tx"]]
		listens = [power_real_all[device]["listen"]]
		for umbral in umbrales:
			power_dict = "power_real_" + name + "__" + umbral.replace(".","")
			txs.append(eval(power_dict)[device]["tx"])
			listens.append(eval(power_dict)[device]["listen"])

		txs_power = (np.array(txs)+np.array(listens))/100 * tiempo * tx_power * V / 1000
	
		plt.plot(umbrales_graf, txs_power, 'r', linestyle="-.", label="radio")
	
		plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
		plt.title(title, loc='center')
		plt.xlabel("umbral")
		plt.ylabel("Consumo energético (J)")
		path_graf = "informes/graficas_" + name + "/consumo_real_tx_" + device + ".png"
		plt.savefig(path_graf, bbox_inches="tight")
		plt.close()


#grafica que muestra el consumo de envio aislado con respecto al umbral
def generarGraficaPowerIso():
	title = "Gráfica consumo aislado {}".format(name)
	umbrales_graf = ["0"] + umbrales

	fig, ax = plt.subplots()
	fig.subplots_adjust(bottom=0.3)
	
	txs = [power_isolated_all[device]["tx"]]
	for umbral in umbrales:
		power_dict = "power_isolated_" + name + "__" + umbral.replace(".","")
		txs.append(eval(power_dict)["device-01"]["tx"])

	txs_power = np.array(txs)/100 * tiempo * tx_power * V / 1000

	plt.plot(umbrales_graf, txs_power, 'r', linestyle="-.", label="tx")

	plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
	plt.title(title, loc='center')
	plt.xlabel("umbral")
	plt.ylabel("Consumo energético (J)")
	path_graf = "informes/graficas_" + name + "/consumo_aislado.png"
	plt.savefig(path_graf, bbox_inches="tight")
	plt.close()





#por cada escnario busca la carpeta de cada umbral para obtener los datos con los que generar las gráficas
folders = glob.glob("informes/" + name + "*")
#print(folders)

umbrales = []
for folder in folders:
	umbral = folder.split("__")[-1]
	umbrales.append(umbral)

umbrales.sort()

envios = {}
error_cuad_med = {}
porcentaje_error_medio = {}
for device in devices:
	envios[device] = [100]
	error_cuad_med[device] = [0]
	porcentaje_error_medio[device] = [0]

for umbral in umbrales:
	matching = [folder for folder in folders if umbral in folder]
	device_folders = glob.glob(matching[0] + "/*")
	for device in devices:
		matching = [device_folder for device_folder in device_folders if device in device_folder]
		report = glob.glob(matching[0] + "/report.txt")
		f = open(report[0], "r")
		json_report = json.loads(f.readline())
		envios[device].append(json_report['n_envios']/n_envios*100)
		error_cuad_med[device].append(json_report['err_cua_med'])
		porcentaje_error_medio[device].append(json_report['porcentaje_error'])

os.mkdir("informes/graficas_" + name)
generarGraficaEnvios()
generarGraficaError()
generarGraficaPorcentajeErrorMedio()
generarGraficaTwoAxisY()
generarGraficaPowerRealPer()
generarGraficaPowerIso()
generarGraficaPowerTxReal()