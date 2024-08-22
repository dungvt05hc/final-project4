# Pull the base image
FROM tiangolo/uwsgi-nginx-flask:python3.10
# Install depndencies 
RUN pip install redis
RUN pip install opencensus==0.11.4
RUN pip install opencensus-ext-azure==1.1.13
RUN pip install opencensus-ext-flask==0.8.2
RUN pip install opencensus-ext-logging==0.1.0
RUN pip install flask==2.3.3
# Copy the content of the current directory to the /app of the container
ADD . /app
