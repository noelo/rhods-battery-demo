import random

from paho.mqtt import client as mqtt_client
import json

import boto3
import time
import logging
import string
from threading import Thread
from queue import Queue

broker = 'mqtt-broker-acc1-0-svc-rte-battery-monitoring.apps.cluster.a-proof-of-concept.com'
port = 443
topic = "batterytest/#"
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'
sendclient_id= f'python-sendmqtt-{random.randint(0, 100)}'
username = 'admin'
password = 'admin_access.redhat.com'
certificate="C:/Users/wscha_000/public.crt"
VIN="123456"
directory="C:/Users/wscha_000/"

secret_key = 'MMKatTz6wJnFU2AKKbrVxCpSqrRvkivAqKcPeA1Z'
access_key = 'RyDhFiO8U9iIbXk4XMCa'

def sendprocess(queue):
    topic="batterytest/statusupdate"
    send_client=connect_mqtt(sendclient_id)
    while True:
        item=queue.get()
        sendinfo(send_client,topic,item[0],item[1],item[2])

def remove_non_ascii(a_str):
    ascii_chars = set(string.printable)

    return ''.join(
        filter(lambda x: x in ascii_chars, a_str)
    )

def sendinfo(client,topic,VIN,status,message):
    #filter out all non printable 
    VIN=remove_non_ascii(VIN)
    status=remove_non_ascii(status)
    message=remove_non_ascii(message)
    #make the dict
    sendmsg={
        "VIN": VIN,
        "timestamp": time.time(),
        "Status": status,
        "Message": message
    }
    jsonmsg = json.dumps(sendmsg)
    result=client.publish(topic,str(sendmsg))
    status = result[0]
    if status == 0:
        print(f"Send `{jsonmsg}` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")




def on_message(client, userdata, msg):
    print(msg.topic)
    if msg.topic=="batterytest/modelupdate": 
        payload=msg.payload.decode()
        try:
            update = json.loads(payload)
        except Exception as e:
            queue.put([VIN,"NOTOK",e])
            return
        if update['VIN'] != VIN:
            queue.put([VIN,"NOTOK","ERROR: VIN is not matching"])
            return 
        session=boto3.session.Session()
        s3_url="https://"+update["url"]
        try:
            s3_client=session.client(service_name='s3',aws_access_key_id=access_key,aws_secret_access_key=secret_key,endpoint_url=s3_url)
        except Exception as e:
            queue.put([VIN,"NOTOK",e])
            return
        filename=directory+"Modelupdatefile_"+ time.strftime("%Y%m%d-%H%M%S")
        logging.info("Start Download: "+time.strftime("%Y%m%d-%H%M%S")+ " File " + update['file'] + " to " + filename)
        try:    
            with open(filename,"wb") as data:
                s3_client.download_fileobj(update['bucket'],update['file'] , data)
        except Exception as e:
            queue.put([VIN,"NOTOK",e])
            return
        logging.info("End Download: "+ time.strftime("%Y%m%d-%H%M%S"))
        queue.put([VIN,"OK",""])
    elif msg.topic=="batterytest/newmodel":
        print
    else:
        print("Error: Topic unnknown")



def connect_mqtt(client_id) -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.tls_set(ca_certs=certificate)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def subscribe(client: mqtt_client):
  #  def on_message(client, userdata, msg):
  #      print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(topic)
    client.on_message = on_message


def run():
    send=Thread(target=sendprocess, args=(queue,))
    send.start()
    client = connect_mqtt(client_id)
    subscribe(client)
    client.loop_forever()

if __name__ == '__main__':
    queue=Queue()
    run()
