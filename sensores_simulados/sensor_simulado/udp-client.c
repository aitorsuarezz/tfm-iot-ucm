#include "contiki.h"
#include "net/ip/uip.h"
#include "net/ipv6/uip-ds6.h"
#include "net/ip/uip-udp-packet.h"
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include "client_measures.h"
#include "sys/energest.h"
#include <math.h>

#define UDP_CLIENT_PORT 8765
#define UDP_SERVER_PORT 5678

#define UDP_EXAMPLE_ID  190

#define DEBUG DEBUG_PRINT
#include "net/ip/uip-debug.h"


#define PERIOD 20

#define SEND_INTERVAL		(PERIOD * CLOCK_SECOND)
#define MAX_PAYLOAD_LEN		30

static struct uip_udp_conn *client_conn;
static uip_ipaddr_t server_ipaddr;

/*---------------------------------------------------------------------------*/
PROCESS(udp_client_process, "UDP client process");
AUTOSTART_PROCESSES(&udp_client_process);

/*---------------------------------------------------------------------------*/
static void getEnergestTimes(void)
{

  uint32_t all_cpu, all_lpm, all_transmit, all_listen;

  energest_flush(); //actualizar los tiempos de energest
  all_cpu = energest_type_time(ENERGEST_TYPE_CPU);
  all_lpm = energest_type_time(ENERGEST_TYPE_LPM);
  all_transmit = energest_type_time(ENERGEST_TYPE_TRANSMIT);
  all_listen = energest_type_time(ENERGEST_TYPE_LISTEN);


  printf("{\"cpu\":%lu, \"lpm\":%lu, \"tx\":%lu, \"listen\":%lu}\n",
  all_cpu, all_lpm, all_transmit, all_listen);
}

/*---------------------------------------------------------------------------*/
static int readMeasure(float *measure, float *measure_csk, int num)
{

  if (num > SIZE_ARR)
  {
    printf("Error al obtener medida");
    return -1;
  }

  int index = num--;

  *measure = (float)(measures[index]);
  *measure_csk = (float)(measures_csk[index]);

  return 1;

}

/*---------------------------------------------------------------------------*/
static bool cindex_model(float measure, float measure_csk, float *cindex) 
{
  float current_cindex, diff;

  current_cindex = measure/measure_csk;

  diff = fabs(*cindex - current_cindex);

  if ((diff > umbral) || (*cindex == 0.0)) {
    printf("DIFF MAYOR\n");
    *cindex = current_cindex;
    return true;
  }

  return false;
}
/*---------------------------------------------------------------------------*/

static void
send_packet()
{
  static int seq_id = 0;
  char buf[MAX_PAYLOAD_LEN];
  float measure, measure_csk;
  static float cindex = 0.0;
  int dec;
  float frac;

  if (readMeasure(&measure, &measure_csk, seq_id++) == -1)
  {
    return;
  }

  if (cindex_model(measure, measure_csk, &cindex)) {

    dec = cindex;
    frac = cindex - dec;

    //seq_id++;
    sprintf(buf, "%d.%03u", dec, (unsigned int)(frac*1000));
    PRINTF("cindex: %s\n", buf);
    uip_udp_packet_send(client_conn, buf, strlen(buf));
  }
}
/*---------------------------------------------------------------------------*/

static void
set_global_address(void)
{
  uip_ipaddr_t ipaddr;

  uip_ip6addr(&ipaddr, 0xaaaa, 0, 0, 0, 0, 0, 0, 0);
  uip_ds6_set_addr_iid(&ipaddr, &uip_lladdr);
  uip_ds6_addr_add(&ipaddr, 0, ADDR_AUTOCONF);
  uip_ip6addr(&server_ipaddr, 0xaaaa, 0, 0, 0, 0, 0, 0, 0x0001);

}
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(udp_client_process, ev, data)
{
  static struct etimer periodic;

  PROCESS_BEGIN();

  PROCESS_PAUSE();

  set_global_address();
  
  PRINTF("UDP client process started\n");

  /* new connection with remote host */
  client_conn = udp_new(&server_ipaddr, UIP_HTONS(UDP_SERVER_PORT), NULL); 
  
  if(client_conn == NULL) {
    PRINTF("No UDP connection available, exiting the process!\n");
    PROCESS_EXIT();
  }

  udp_bind(client_conn, UIP_HTONS(UDP_CLIENT_PORT)); 

  PRINTF("Created a connection with the server ");
  PRINT6ADDR(&client_conn->ripaddr);
  PRINTF(" local/remote port %u/%u\n",
	UIP_HTONS(client_conn->lport), UIP_HTONS(client_conn->rport));

  energest_init(); //iniciar el energest
  while(1) {
    etimer_set(&periodic, SEND_INTERVAL);
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&periodic));
    send_packet();//enviar medicion si procede
    getEnergestTimes();//imprimir mediciones energest
  }

  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
