https://developers.redhat.com/blog/2020/08/26/connecting-external-clients-to-red-hat-amq-broker-on-red-hat-openshift#part_2__configuring_openshift



## Generate Certs

```
keytool -genkey -alias broker  -validity 365 -keyalg RSA -keystore broker.ks
keytool -export -alias broker -keystore broker.ks -file broker_cert
keytool -import -alias broker -keystore client.ts -file broker_cert
keytool -genkey -alias broker -keyalg RSA -keystore broker.ts

```

## Extract cert to connect to broker and create secret in redhat-ods-applications namespace
```
keytool -export -alias broker -keystore broker.ks -rfc -file public.cert

oc create secret generic mqtt-cert-secret --from-file=public.cert -n redhat-ods-applications
```

## Create secret with creds and certs in broker namespace
```
oc create secret generic mqtt-broker-mqtt-secret --from-file=broker.ks --from-literal=keyStorePassword=changeit --from-file=client.ts=broker.ts --from-literal=trustStorePassword=changeit
```

## Build broker

```
apiVersion: broker.amq.io/v1beta1
kind: ActiveMQArtemis
metadata:
  name: mqtt-broker
  namespace: battery-monitoring
spec:
  acceptors:
  - name: acc1
    protocols: MQTT
    port: 1883
    sslEnabled: true
    sslSecret: mqtt-broker-mqtt-secret
    expose: true
    verifyHost: false
  deploymentPlan:
    image: placeholder
    jolokiaAgentEnabled: false
    journalType: nio
    managementRBACEnabled: true
    messageMigration: false
    persistenceEnabled: true
    requireLogin: false
    size: 1
    storage:
      size: 4Gi
  adminUser: admin
  adminPassword: admin_access.redhat.com
  console:
    expose: true
```

## Configure Addresses
```
apiVersion: broker.amq.io/v2alpha1
kind: ActiveMQArtemisAddress
metadata:
  name: mqtt-broker
spec:
  addressName: batterytest
  queueName: batterytest
  routingType: anycast
```


## Test Connectivity
```
mosquitto_pub --insecure -d -L mqtts://admin:admin_access.redhat.com@mqtt-broker-acc1-0-svc-rte-battery-monitoring.apps.cluster.a-proof-of-concept.com:443/batterytest -m "this is a test" --insecure --cafile public.cert

mosquitto_sub --insecure -d -L mqtts://admin:admin_access.redhat.com@mqtt-broker-acc1-0-svc-rte-battery-monitoring.apps.cluster.a-proof-of-concept.com:443/batterytest  --insecure --cafile public.cert
```



