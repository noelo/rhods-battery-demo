
# Ceph Notification setup


```
object-store->bucket(noc-test)->notification->topic(noc-test-topic)->k8s_svc(ceph-bucket-source-svc)->CephSource(ceph-bucket-source)->knative_service(bucket-handler)->kfp_api->experiment->run
```

# Build and push image
```
podman build -t python-app .
podman tag localhost/python-app quay.io/noeloc/bucket-notification-handler
podman push quay.io/noeloc/bucket-notification-handler
```

# Setup Knative sink
```
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: bucket-handler
spec:
  template:
    spec:
      containers:
      - name: event-handler
        image: quay.io/noeloc/bucket-notification-handler:latest
        env:
          - name: KFP_API
            value: http://ds-pipeline.redhat-ods-applications.svc.cluster.local:8888
          - name: KFP_NAME
            value: "test name"
```

# Setup Ceph Source
```
apiVersion: sources.knative.dev/v1alpha1
kind: CephSource
metadata:
  name: ceph-bucket-source
spec:
  port: "8080"
  sink:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: bucket-handler
```

# Setup Service
```
apiVersion: v1
kind: Service
metadata:
  name: ceph-bucket-source-svc
spec:
  selector:
    eventing.knative.dev/sourceName: ceph-bucket-source
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
```

## Create Bucket 
```
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: noc-test
  labels:
    app-owner: noc-test
spec:
  bucketName: noc-test
  storageClassName: object
```

## Get the CephObjectStore name and endpoint
```
oc get CephObjectStore -n openshift-storage ceph-object-store -o yaml
apiVersion: ceph.rook.io/v1
kind: CephObjectStore
metadata:
  annotations:
.
.
  name: ceph-object-store
  namespace: openshift-storage
.
.
spec:
.
.
  endpoints:
    insecure:
    - http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
    secure: []
  info:
    endpoint: http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
```

## Extract secret values
```
kubectl get secret noc-test -o go-template='{{range $k,$v := .data}}{{printf "%s: " $k}}{{if not $v}}{{$v}}{{else}}{{$v | base64decode}}{{end}}{{"\n"}}{{end}}'
```

## Instantiate AWS cli pod
```
apiVersion: v1
kind: Pod 
metadata:
  name: aws-cli-runner
spec:
  containers:
    - name: aws-cli
      image: quay.io/ylifshit/aws-cli
```
## Exec into pod
```
kubectl exec -it aws-cli-runner -- bash
```

## Configure AWS environment
```
aws configure set default.sns.signature_version s3v4
aws configure 
```

When using the _aws configure_ command use the secret values extracted above as _Access Key and Secret Access Key_ and set the region to _ceph-object-store_

## Create the notification topic
```
 aws --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080 sns create-topic --name=noc-test-topic --attributes='{"push-endpoint": "http://ceph-bucket-source-svc.battery-monitoring.svc.cluster.local"}'
```

## Topic admin
```
aws sns list-topics --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080

aws sns delete-topic --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080 --topic-arn "arn:aws:sns:ceph-object-store::noc-test-topic"
```


## Create the bucket notification 
```
 aws --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080 s3api put-bucket-notification-configuration --bucket noc-test --notification-configuration='{"TopicConfigurations": [{"Id": "notif2", "TopicArn": "arn:aws:sns:default::noc-test-topic", "Events": []}]}'
```

## Notification Admin
```
aws --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080 s3api put-bucket-notification-configuration --bucket noc-test --notification-configuration='{}'

aws s3api get-bucket-notification --bucket noc-test --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
```

## Configure the KFP name in the handler 
```
kn service update bucket-handler --env KFP_NAME=fdt
kn service update bucket-handler --env KFP_API=http://ds-pipeline.redhat-ods-applications.svc.cluster.local:8888
kn service update bucket-handler --image quay.io/noeloc/bucket-notification-handler:latest
```


```
[root@aws-cli-runner /]# aws sns list-topics --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
{
    "Topics": [
        {
            "TopicArn": "arn:aws:sns:ceph-object-store::noc-test-topic"
        },
        {
            "TopicArn": "arn:aws:sns:ceph-object-store::vehicle-data"
        }
    ]
}


[root@aws-cli-runner /]# aws sns get-topic-attributes --topic-arn arn:aws:sns:ceph-object-store::vehicle-data --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
{
    "Attributes": {
        "User": "",
        "Name": "vehicle-data",
        "EndPoint": "{\"EndpointAddress\":\"http://vehicle-data-ceph-source-svc.battery-monitoring.svc.cluster.local\",\"EndpointArgs\":\"Attributes.entry.1.key=push-endpoint&Attributes.entry.1.value=http://vehicle-data-ceph-source-svc.battery-monitoring.svc.cluster.local&Version=2010-03-31&push-endpoint=http://vehicle-data-ceph-source-svc.battery-monitoring.svc.cluster.local\",\"EndpointTopic\":\"vehicle-data\",\"HasStoredSecret\":\"false\",\"Persistent\":\"false\"}",
        "TopicArn": "arn:aws:sns:ceph-object-store::vehicle-data",
        "OpaqueData": ""
    }
}



[root@aws-cli-runner /]# aws sns get-topic-attributes --topic-arn arn:aws:sns:ceph-object-store::noc-test-topic --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
{
    "Attributes": {
        "User": "",
        "Name": "noc-test-topic",
        "EndPoint": "{\"EndpointAddress\":\"http://ceph-bucket-source-svc.battery-monitoring.svc.cluster.local\",\"EndpointArgs\":\"Attributes.entry.1.key=push-endpoint&Attributes.entry.1.value=http://ceph-bucket-source-svc.battery-monitoring.svc.cluster.local&Version=2010-03-31&push-endpoint=http://ceph-bucket-source-svc.battery-monitoring.svc.cluster.local\",\"EndpointTopic\":\"noc-test-topic\",\"HasStoredSecret\":\"false\",\"Persistent\":\"false\"}",
        "TopicArn": "arn:aws:sns:ceph-object-store::noc-test-topic",
        "OpaqueData": ""
    }
}



[root@aws-cli-runner /]# aws s3api get-bucket-notification-configuration --bucket noc-test --endpoint-url http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080
{
    "TopicConfigurations": [
        {
            "Id": "notif2",
            "TopicArn": "arn:aws:sns:ceph-object-store::noc-test-topic",
            "Events": [
                "s3:ObjectCreated:*",
                "s3:ObjectRemoved:*"
            ]
        }
    ]
}
```
