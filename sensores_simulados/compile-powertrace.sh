#!/bin/sh

echo $1
echo $2

cd /home/aitor/contiki-3.0/examples/powertrace-sensor_simulado/
rm -f devices/*

for i in 1 2 3 4 5 6 7 8 9 10 11
do
	make clean
	export CFLAGS="-D$1 -D_NODO${i}_ -D$2"; make example-powertrace.z1 TARGET=z1
	cp -f example-powertrace.z1 devices/powertrace-${i}.z1
done