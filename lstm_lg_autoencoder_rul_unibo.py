#!/usr/bin/env python
# coding: utf-8
# # RUL estimation UNIBO Powertools Dataset
import os
import time
from kfp import dsl, components
from kfp.components import InputPath, OutputPath
from kubernetes.client import V1Volume, V1EnvVar, V1PersistentVolumeClaimVolumeSource, V1SecretVolumeSource
from kfp_tekton.compiler import TektonCompiler
from kfp_tekton.compiler import pipeline_utils
from kfp_tekton.k8s_client_helper import env_from_secret
from typing import NamedTuple

#help="0 normal Training (default), 1 Bad Training, 2 Inference", default=0)
def load_trigger_data(data_file:str,bucket_details:str,file_destination:str):
    '''load data file passed from cloud event into relevant location'''
    import boto3
    import os
    import logging
    import zipfile

    endpoint_url = os.environ["s3_host"]
    aws_access_key_id = os.environ["s3_access_key"]
    aws_secret_access_key = os.environ["s3_secret_access_key"]
    logging.info("S3 creds %s %s %s ", endpoint_url, aws_access_key_id, aws_secret_access_key)
    logging.info("Trigger data bucket %s file %s ", bucket_details, data_file)


    s3_target = boto3.resource(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=None,
        config=boto3.session.Config(signature_version='s3v4'),
        verify=False
    )
    
    with open('/tmp/'+data_file, 'wb') as f:
        s3_target.meta.client.download_fileobj(bucket_details, data_file, f)
    
    with zipfile.ZipFile('/tmp/'+data_file, 'r') as zip_ref:
        zip_ref.extractall(file_destination)
    
    os.listdir(file_destination)
        
def prep_data_train_model(data_path : str, epoch_count : int, parameter_data : OutputPath(), experiment_name : str, run_mode : int=0):
    """Preps the data for processing"""
    import numpy as np
    import pandas as pd
    import sys
    import pickle
    import logging
    from importlib import reload
    from tensorflow import keras
    from keras import layers, regularizers
    from keras.models import Model
    from keras import backend as K
    from keras.models import Sequential, Model
    from keras.layers import Dense, Dropout, Activation, TimeDistributed, Input, Concatenate
    from keras.optimizers import Adam
    from keras.layers import LSTM, Masking
    from data_processing.unibo_powertools_data import UniboPowertoolsData, CycleCols
    from data_processing.model_data_handler import ModelDataHandler
    from data_processing.prepare_rul_data import RulHandler
    sys.path.append(data_path)
    reload(logging)
    logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', level=logging.INFO, datefmt='%Y/%m/%d %H:%M:%S')
    #help="0 normal Training (default), 1 Bad Training, 2 Inference", default=0)

    # Normal Training
    if run_mode == 0:
        logging.info("Normal Training")
        train_names = [
        '000-DM-3.0-4019-S',#minimum capacity 1.48
        '001-DM-3.0-4019-S',#minimum capacity 1.81
        '002-DM-3.0-4019-S',#minimum capacity 2.06
        '009-DM-3.0-4019-H',#minimum capacity 1.41
        '010-DM-3.0-4019-H',#minimum capacity 1.44
        '014-DM-3.0-4019-P',#minimum capacity 1.7
        '015-DM-3.0-4019-P',#minimum capacity 1.76
        '016-DM-3.0-4019-P',#minimum capacity 1.56
        '017-DM-3.0-4019-P',#minimum capacity 1.29
        '007-EE-2.85-0820-S',#2.5
        '008-EE-2.85-0820-S',#2.49
        '042-EE-2.85-0820-S',#2.51
        '043-EE-2.85-0820-H',#2.31
        '040-DM-4.00-2320-S',#minimum capacity 3.75, cycles 188
        '018-DP-2.00-1320-S',#minimum capacity 1.82
        '036-DP-2.00-1720-S',#minimum capacity 1.91
        '037-DP-2.00-1720-S',#minimum capacity 1.84
        '038-DP-2.00-2420-S',#minimum capacity 1.854 (to 0)
        '050-DP-2.00-4020-S',#new 1.81
        '051-DP-2.00-4020-S',#new 1.866    
        ]
        test_names = [
        '003-DM-3.0-4019-S',#minimum capacity 1.84
        '011-DM-3.0-4019-H',#minimum capacity 1.36
        '013-DM-3.0-4019-P',#minimum capacity 1.6
        '006-EE-2.85-0820-S',# 2.621
        '044-EE-2.85-0820-H',# 2.43
        '039-DP-2.00-2420-S',#minimum capacity 1.93
        '041-DM-4.00-2320-S',#minimum capacity 3.76, cycles 190
            ]
        # epoch_count=270
    
    elif run_mode == 1: # POOR TRAINING
        logging.info("Poor Training")
        train_names = [
        '002-DM-3.0-4019-S',#minimum capacity 2.06
        '009-DM-3.0-4019-H',#minimum capacity 1.41
        '014-DM-3.0-4019-P',#minimum capacity 1.7
        '015-DM-3.0-4019-P',#minimum capacity 1.76
        '016-DM-3.0-4019-P',#minimum capacity 1.56
        '007-EE-2.85-0820-S',#2.5
        '008-EE-2.85-0820-S',#2.49
        '043-EE-2.85-0820-H',#2.31
        '040-DM-4.00-2320-S',#minimum capacity 3.75, cycles 188
        '018-DP-2.00-1320-S',#minimum capacity 1.82
        '036-DP-2.00-1720-S',#minimum capacity 1.91
        '050-DP-2.00-4020-S',#new 1.81
        ]

        test_names = [
        '003-DM-3.0-4019-S',#minimum capacity 1.84
        '011-DM-3.0-4019-H',#minimum capacity 1.36
        '013-DM-3.0-4019-P',#minimum capacity 1.6
        '006-EE-2.85-0820-S',# 2.621
        '044-EE-2.85-0820-H',# 2.43
        '039-DP-2.00-2420-S',#minimum capacity 1.93
        '041-DM-4.00-2320-S',#minimum capacity 3.76, cycles 190
        ]
        # epoch_count=40
    else: #INFERENCING
        logging.info("Inferencing")
        train_names = [
        '000-DM-3.0-4019-S'#minimum capacity 1.81
        ]
        test_names = [
        '003-DM-3.0-4019-S']

    # # Load Data

    dataset = UniboPowertoolsData(
        test_types=[],
        chunk_size=1000000,
        lines=[37, 40],
        charge_line=37,
        discharge_line=40,
        base_path=data_path
    )

    ################################################NOC
    dataset.prepare_data(train_names, test_names)
    dataset_handler = ModelDataHandler(dataset, [
        CycleCols.VOLTAGE,
        CycleCols.CURRENT,
        CycleCols.TEMPERATURE
    ])

    rul_handler = RulHandler()

    # # Data preparation

    capacity_tresholds = {
    3.0 : 2.7,#th 90% - min 2.1, 70%
    2.85 : 2.7,#th 94.7% - min 2.622, 92%
    2.0 : 1.93,#th 96.5% - min 1.93, 96.5%
    4.0 : 3.77,#th 94.2% - min 3.77 94.2%
    4.9 : 4.7,#th 95.9% - min 4.3, 87.7%
    5.0 : 4.5#th 90% - min 3.63, 72.6%
    }

    (train_x, train_y_soh, test_x, test_y_soh,
    train_battery_range, test_battery_range,
    time_train, time_test, current_train, current_test) = dataset_handler.get_discharge_whole_cycle_future(train_names, test_names, min_cycle_length=300)

    train_y = rul_handler.prepare_y_future(train_names, train_battery_range, train_y_soh, current_train, time_train, capacity_tresholds)
    test_y = rul_handler.prepare_y_future(test_names, test_battery_range, test_y_soh, current_test, time_test, capacity_tresholds)
    x_norm = rul_handler.Normalization()
    x_norm.fit(train_x)

    train_x = x_norm.normalize(train_x)
    test_x = x_norm.normalize(test_x)
    
    AUTOENCODER_WEIGHTS = '2023-02-09-15-50-22_autoencoder_gl_unibo_powertools'
    N_CYCLE = 500
    WARMUP_TRAIN = 15
    WARMUP_TEST = 30

    opt = keras.optimizers.Adam(learning_rate=0.0002)
    LATENT_DIM = 10

    class Autoencoder(Model):
        def __init__(self, latent_dim):
            super(Autoencoder, self).__init__()
            self.latent_dim = latent_dim

            encoder_inputs = layers.Input(shape=(train_x.shape[1], train_x.shape[2]))
            encoder_conv1 = layers.Conv1D(filters=8, kernel_size=10, strides=2, activation='relu', padding='same')(encoder_inputs)
            encoder_pool1 = layers.MaxPooling1D(5, padding='same')(encoder_conv1)
            encoder_conv2 = layers.Conv1D(filters=8, kernel_size=4, strides=1, activation='relu', padding='same')(encoder_pool1)
            encoder_pool2 = layers.MaxPooling1D(3, padding='same')(encoder_conv2)
            encoder_flat1 = layers.Flatten()(encoder_pool1)
            encoder_flat2 = layers.Flatten()(encoder_pool2)
            encoder_concat = layers.concatenate([encoder_flat1, encoder_flat2])
            encoder_outputs = layers.Dense(self.latent_dim, activation='relu')(encoder_concat)
            self.encoder = Model(inputs=encoder_inputs, outputs=encoder_outputs)

            decoder_inputs = layers.Input(shape=(self.latent_dim,))
            decoder_dense1 = layers.Dense(10*8, activation='relu')(decoder_inputs)
            decoder_reshape1 = layers.Reshape((10, 8))(decoder_dense1)
            decoder_upsample1 = layers.UpSampling1D(3)(decoder_reshape1)
            decoder_convT1 = layers.Conv1DTranspose(filters=8, kernel_size=4, strides=1, activation='relu', padding='same')(decoder_upsample1)
            decoder_upsample2 = layers.UpSampling1D(5)(decoder_convT1)
            decoder_convT2 = layers.Conv1DTranspose(filters=8, kernel_size=10, strides=2, activation='relu', padding='same')(decoder_upsample2)
            decoder_outputs = layers.Conv1D(3, kernel_size=3, activation='relu', padding='same')(decoder_convT2)
            self.decoder = Model(inputs=decoder_inputs, outputs=decoder_outputs)

        def call(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded

    autoencoder = Autoencoder(LATENT_DIM)

    autoencoder.compile(optimizer=opt, loss='mse', metrics=['mse', 'mae', 'mape', keras.metrics.RootMeanSquaredError(name='rmse')])
    autoencoder.encoder.summary()
    autoencoder.decoder.summary()
    autoencoder.load_weights(data_path + 'data/results/trained_model/%s/model' % AUTOENCODER_WEIGHTS)
    # compression
    train_x = autoencoder.encoder(train_x).numpy()
    test_x = autoencoder.encoder(test_x).numpy()
    logging.info("compressed train x shape {}".format(train_x.shape))
    logging.info("compressed test x shape {}".format(test_x.shape))
    test_x = test_x[:,~np.all(train_x == 0, axis=0)]#we need same column number of training
    train_x = train_x[:,~np.all(train_x == 0, axis=0)]
    logging.info("compressed train x shape without zero column {}".format(train_x.shape))
    logging.info("compressed test x shape without zero column {}".format(test_x.shape))

    x_norm = rul_handler.Normalization()
    x_norm.fit(train_x)
    train_x = x_norm.normalize(train_x)
    test_x = x_norm.normalize(test_x)
    train_x = rul_handler.battery_life_to_time_series(train_x, N_CYCLE, train_battery_range)
    test_x = rul_handler.battery_life_to_time_series(test_x, N_CYCLE, test_battery_range)
    train_x, train_y, train_battery_range, train_y_soh = rul_handler.delete_initial(train_x, train_y, train_battery_range, train_y_soh, WARMUP_TRAIN)
    test_x, test_y, test_battery_range, test_y_soh = rul_handler.delete_initial(test_x, test_y, test_battery_range, test_y_soh, WARMUP_TEST)

    # first one is SOH, we keep only RUL
    train_y = train_y[:,1]
    test_y = test_y[:,1]

    # # Y normalization
    y_norm = rul_handler.Normalization()
    y_norm.fit(train_y)
    train_y = y_norm.normalize(train_y)
    test_y = y_norm.normalize(test_y)  

    ## Only when training
    if run_mode != 2:
        opt = keras.optimizers.Adam(lr=0.000003)
        model = Sequential()
        model.add(Masking(input_shape=(train_x.shape[1], train_x.shape[2])))
        model.add(LSTM(128, activation='tanh',
                    return_sequences=True,
                    kernel_regularizer=regularizers.l2(0.0002)))
        model.add(LSTM(64, activation='tanh', return_sequences=False,
                    kernel_regularizer=regularizers.l2(0.0002)))
        model.add(Dense(64, activation='selu', kernel_regularizer=regularizers.l2(0.0002)))
        model.add(Dense(32, activation='selu', kernel_regularizer=regularizers.l2(0.0002)))
        model.add(Dense(1, activation='linear'))
        model.summary()

        model.compile(optimizer=opt, loss='huber', metrics=['mse', 'mae', 'mape', keras.metrics.RootMeanSquaredError(name='rmse')])

        history = model.fit(train_x, train_y, 
                                epochs=epoch_count, 
                                batch_size=32,
                                verbose=2,
                                validation_split=0.1
                            )
        model_path= data_path+'data/results/trained_model/%s.h5' % experiment_name

        model.save(model_path)
        logging.info("Model saved to %s",model_path)

        hist_df = pd.DataFrame(history.history)
        hist_csv_file = data_path+'data/results/trained_model/%s_history.csv' % experiment_name
        with open(hist_csv_file, mode='w') as f:
            hist_df.to_csv(f)

    data_store = [train_x, train_y, train_battery_range, train_y_soh, y_norm, test_x, test_y]

    with open(parameter_data, "b+w") as f:
        pickle.dump(data_store,f)

def model_upload_notify(data_path:str,paramater_data:InputPath(),experiment_name:str,model_bucket:str="battery-model-bucket"):
    """Upload model and notify"""
    import os  
    import logging
    from importlib import reload
    import pickle
    from datetime import datetime
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import json
    import random
    import boto3
    import zipfile 
    import tensorflow as tf
    from paho.mqtt import client as mqtt_client
    from tensorflow import keras
    from keras import layers, regularizers
    from keras import backend as K
    from keras.models import Sequential, Model
    from keras.layers import Dense, Dropout, Activation, TimeDistributed, Input, Concatenate
    from keras.optimizers import Adam
    from keras.layers import LSTM, Masking

    logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', level=logging.DEBUG, datefmt='%Y/%m/%d %H:%M:%S')

    broker_cert=os.getenv("mqtt_cert","/opt/certs/public.cert")
    broker=os.getenv("mqtt_broker","not set")
    port=os.getenv("mqtt_port","-1")
    topic="batterytest/modelupdate"
    logging.info("MQTT params Broker=%s Port=%s Topic=%s",broker,port,topic)

    f = open(paramater_data,"b+r")
    data_store = pickle.load(f)
    train_x=data_store[0]
    train_y=data_store[1]
    train_battery_range=data_store[2]
    train_y_soh=data_store[3]
    y_norm=data_store[4]
    test_x=data_store[5]
    test_y=data_store[6]

    model = keras.models.load_model(data_path +'data/results/trained_model/%s.h5' % experiment_name)
    model.summary(expand_nested=True)

    logging.info("Training mode")
    results = model.evaluate(test_x, test_y, return_dict = True)
    logging.info(results)
    max_rmse = 0
    for index in range(test_x.shape[0]):
        result = model.evaluate(np.array([test_x[index, :, :]]), np.array([test_y[index]]), return_dict = True, verbose=0)
        max_rmse = max(max_rmse, result['rmse'])
        
    logging.info("Max rmse: {}".format(max_rmse))

    train_predictions = model.predict(train_x)
    train_y = y_norm.denormalize(train_y)
    train_predictions = y_norm.denormalize(train_predictions)
    a = 0
    for b in train_battery_range:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=train_y_soh[a:b], y=train_predictions[a:b,0],
                            mode='lines', name='predicted'))
        fig.add_trace(go.Scatter(x=train_y_soh[a:b], y=train_y[a:b],
                            mode='lines', name='actual'))
        fig.update_layout(title='Results on training',
                        xaxis_title='SoH Capacity',
                        yaxis_title='Remaining Ah until EOL',
                        xaxis={'autorange':'reversed'},
                        width=1400,
                    height=600)
        # fig.show()
        output_image = data_path+'data/results/trained_model/%s.png' % experiment_name
        fig.write_image(output_image,format='png')
        
        output_image = data_path+'data/results/trained_model/%s.png' % experiment_name
        
    endpoint_url=os.environ["s3_host"]
    aws_access_key_id=os.environ["s3_access_key"]
    aws_secret_access_key=os.environ["s3_secret_access_key"]
    logging.info("S3 creds %s %s %s ",endpoint_url,aws_access_key_id, aws_secret_access_key)
    logging.info("Uploading model to %s file %s ",model_bucket,experiment_name)
#
    s3_target = boto3.resource('s3',
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=None,
        config=boto3.session.Config(signature_version='s3v4'),
        verify=False
    )

    with zipfile.ZipFile('/tmp/'+experiment_name+'.zip', mode="w") as myzip:
        myzip.write(data_path +'data/results/trained_model/%s.h5' % experiment_name)
    
    with open('/tmp/'+experiment_name+'.zip', 'rb') as f:
        s3_target.meta.client.upload_fileobj(f,model_bucket, experiment_name+".zip")
        
    client = mqtt_client.Client(client_id="model_upload_notify", userdata=None, transport="tcp")
    client.enable_logger(logger=logging)
    client.tls_set(ca_certs=broker_cert)
    client.tls_insecure_set(True)
    client.username_pw_set('admin', 'admin_access.redhat.com')
    client.connect(host='mqtt-broker-acc1-0-svc.battery-monitoring.svc', port=1883)

    payload={
        "url": "http://rook-ceph-rgw-ceph-object-store-openshift-storage.apps.cluster.a-proof-of-concept.com/",
        "bucket": model_bucket,
        "file":  experiment_name+".h5",
        "timestamp": datetime.timestamp(datetime.now()),
        "app_id": "modelbuildpipeline"
    }

    jsonmsg = json.dumps(payload)
    ret = client.publish(topic,payload=jsonmsg,qos=1) 
    status = ret[0]
    if status == 0:
        logging.info(f"Send new model notification `{jsonmsg}` to topic `{topic}`")
    else:
        logging.info(f"Failed to send new model notification to topic {topic}")        
                
def model_inference(data_path:str,paramater_data:InputPath(),experiment_name:str,vin:str="12345"):
    """Evaluate the model"""
    import os  
    import logging
    from importlib import reload
    import pickle
    import time
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import json
    import random
    import tensorflow as tf
    from paho.mqtt import client as mqtt_client
    from tensorflow import keras
    from keras import layers, regularizers
    from keras import backend as K
    from keras.models import Sequential, Model
    from keras.layers import Dense, Dropout, Activation, TimeDistributed, Input, Concatenate
    from keras.optimizers import Adam
    from keras.layers import LSTM, Masking

    reload(logging)
    logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', level=logging.INFO, datefmt='%Y/%m/%d %H:%M:%S')

    broker=os.getenv("mqtt_broker","not set")
    port=os.getenv("mqtt_port","-1")
    broker_cert=os.getenv("mqtt_cert","/opt/certs/public.cert")
    topic="batterytest/batterymonitoring"
    logging.info("MQTT params Broker=%s Port=%s Topic=%s",broker,port,topic)
    
    f = open(paramater_data,"b+r")
    data_store = pickle.load(f)
    train_x=data_store[0]
    train_y=data_store[1]
    y_norm=data_store[4]
    
    model = keras.models.load_model(data_path +'data/results/trained_model/%s.h5' % experiment_name)
    model.summary(expand_nested=True)

    logging.info("Inferencing mode")

    train_predictions = model.predict(train_x)
    train_y = y_norm.denormalize(train_y)
    train_predictions = y_norm.denormalize(train_predictions)
    y=train_predictions[0,0]

    payload={
        "VIN": vin,
        "Battery Lifetime AH": str(y), 
        "Timestamp": str(time.time())
    }
    
    
    jsonmsg = json.dumps(payload)    
    client = mqtt_client.Client(client_id="model_inference", userdata=None, transport="tcp")
    client.enable_logger(logger=logging)
    client.tls_set(ca_certs=broker_cert)
    client.tls_insecure_set(True)
    client.username_pw_set('admin', 'admin_access.redhat.com')
    client.connect(host='mqtt-broker-acc1-0-svc.battery-monitoring.svc', port=1883)    
    
    result=client.publish(topic,jsonmsg,qos=1)
    status = result[0]
    if status == 0:
        logging.info(f"Send `{jsonmsg}` to topic `{topic}`")
    else:
        logging.info(f"Failed to send message to topic {topic}")  
       
load_trigger_data_op= components.create_component_from_func(
    load_trigger_data, base_image='quay.io/noeloc/batterybase',
    packages_to_install=['boto3'])

prep_train_data_op= components.create_component_from_func(
    prep_data_train_model, base_image='quay.io/noeloc/batterybase')

upload_model_op= components.create_component_from_func(
    model_upload_notify, base_image='quay.io/noeloc/batterybase',packages_to_install=['kaleido','paho-mqtt','boto3'])

prep_inference_data_op= components.create_component_from_func(
    prep_data_train_model, base_image='quay.io/noeloc/batterybase')

inference_model_op= components.create_component_from_func(
    model_inference, base_image='quay.io/noeloc/batterybase',packages_to_install=['kaleido','paho-mqtt'])


@dsl.pipeline(
  name='batterytest-pipeline',
  description='battery pipeline demo'
)
def batterytest_pipeline(file_obj:str, src_bucket:str,VIN="412356"):
    '''Download files from s3, train, inference'''
    print("Params",file_obj, src_bucket)
    vol = V1Volume(
        name='batterydatavol',
        persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
            claim_name='batterydata',)
        )    
    mqttcert = V1Volume(
        name='mqttcert',
        secret=V1SecretVolumeSource(
            secret_name='mqtt-cert-secret')
        )
    experiment = "lstm_autoencoder_rul_unibo_powertools"
    file_destination = "/opt/data/pitstop/data/unibo-powertools-dataset/unibo-powertools-dataset/"    
    experiment_name = time.strftime("%Y-%m-%d-%H-%M-%S") + '_' + experiment
  
    trigger_data = load_trigger_data_op(file_obj, src_bucket,file_destination)
    trigger_data.add_pvolumes({"/opt/data/pitstop/": vol})
    trigger_data.add_env_variable(V1EnvVar(name='s3_host', value='http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080'))
    trigger_data.add_env_variable(env_from_secret('s3_access_key', 's3-secret', 'AWS_ACCESS_KEY_ID'))
    trigger_data.add_env_variable(env_from_secret('s3_secret_access_key', 's3-secret', 'AWS_SECRET_ACCESS_KEY'))

    res = prep_train_data_op(data_path="/opt/data/pitstop/",epoch_count=2,experiment_name=experiment_name,run_mode=0).after(trigger_data)
    res.add_pvolumes({"/opt/data/pitstop": vol})

    inform_result = upload_model_op(data_path="/opt/data/pitstop/",paramater_data=res.outputs["parameter_data"],experiment_name=experiment_name)
    inform_result.add_pvolumes({"/opt/data/pitstop": vol})
    inform_result.add_pvolumes({"/opt/certs/": mqttcert})
    inform_result.add_env_variable(V1EnvVar(name='mqtt_broker', value='mqtt-broker-acc1-0-svc.battery-monitoring.svc'))
    inform_result.add_env_variable(V1EnvVar(name='mqtt_port', value='1883'))
    inform_result.add_env_variable(V1EnvVar(name='mqtt_cert', value='/opt/certs/public.cert'))
    inform_result.add_env_variable(V1EnvVar(name='s3_host', value='http://rook-ceph-rgw-ceph-object-store.openshift-storage.svc:8080'))
    inform_result.add_env_variable(env_from_secret('s3_access_key', 'battery-model-bucket', 'AWS_ACCESS_KEY_ID'))
    inform_result.add_env_variable(env_from_secret('s3_secret_access_key', 'battery-model-bucket', 'AWS_SECRET_ACCESS_KEY'))
        
    inference_prep = prep_inference_data_op(data_path="/opt/data/pitstop/",epoch_count=2,experiment_name=experiment_name,run_mode=2).after(inform_result)
    inference_prep.add_pvolumes({"/opt/data/pitstop": vol})
   
    inference_result = inference_model_op(data_path="/opt/data/pitstop/",paramater_data=inference_prep.outputs["parameter_data"],experiment_name=experiment_name,vin=VIN)
    inference_result.add_pvolumes({"/opt/data/pitstop": vol})
    inference_result.add_pvolumes({"/opt/certs/": mqttcert})
    inference_result.add_env_variable(V1EnvVar(name='mqtt_broker', value='mqtt-broker-acc1-0-svc.battery-monitoring.svc'))
    inference_result.add_env_variable(V1EnvVar(name='mqtt_port', value='1883'))
    inference_result.add_env_variable(V1EnvVar(name='mqtt_cert', value='/opt/certs/public.cert'))

if __name__ == '__main__':
    os.environ.setdefault("DEFAULT_STORAGE_CLASS","managed-csi")
    os.environ.setdefault("DEFAULT_ACCESSMODES","ReadWriteOnce")
    os.environ.setdefault("DEFAULT_STORAGE_SIZE","10Gi")
    compiler = TektonCompiler()
    pipeline_conf = pipeline_utils.TektonPipelineConf()
    pipeline_conf.add_pipeline_annotation("tekton.dev/track_artifact", 'true')
    pipeline_conf.set_ttl_seconds_after_finished(30)
    compiler.produce_taskspec = False
    compiler.compile(batterytest_pipeline, __file__.replace('.py', '.yaml'),tekton_pipeline_conf=pipeline_conf)