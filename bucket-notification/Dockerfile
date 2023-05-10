FROM registry.access.redhat.com/ubi8/python-39:1-97
USER 0
WORKDIR /app
COPY requirements.txt /app
RUN chown -R 1001:0 ./
USER 1001
RUN pip install -r requirements.txt
COPY kubeflow_trigger.py /app
EXPOSE 8080
ENTRYPOINT [ "python" ]
CMD [ "kubeflow_trigger.py" ]