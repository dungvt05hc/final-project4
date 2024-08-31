from flask import Flask, request, render_template
import os
import random
import redis
import socket
import sys
import logging
from datetime import datetime
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.azure.metrics_exporter import MetricsExporter
from opencensus.trace import config_integration
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

# App Insights
INSTRUMENTATION_KEY = '1407ca61-284d-4186-b050-71d031b6a20a'

# Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(AzureLogHandler(connection_string=f'InstrumentationKey={INSTRUMENTATION_KEY}'))

# Metrics
exporter = MetricsExporter(connection_string=f'InstrumentationKey={INSTRUMENTATION_KEY}')

# Tracing
config_integration.trace_integrations(['logging', 'requests'])
tracer = Tracer(exporter=AzureExporter(connection_string=f'InstrumentationKey={INSTRUMENTATION_KEY}'), 
                sampler=ProbabilitySampler(1.0))

app = Flask(__name__)

# Requests Middleware
middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(connection_string=f'InstrumentationKey={INSTRUMENTATION_KEY}'),
    propagator=TraceContextPropagator(),
    sampler=ProbabilitySampler(1.0),
)

# Load configurations from environment or config file
app.config.from_pyfile('config_file.cfg')

if "VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']:
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

if "VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']:
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

if "TITLE" in os.environ and os.environ['TITLE']:
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

# Redis Connection
r = redis.Redis()

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1): r.set(button1, 0)
if not r.get(button2): r.set(button2, 0)

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':
        # Get current values
        vote1 = r.get(button1).decode('utf-8')
        vote2 = r.get(button2).decode('utf-8')

        # Trace votes
        with tracer.span(name="Cats Vote"):
            pass  # Just creating the span context

        with tracer.span(name="Dogs Vote"):
            pass  # Just creating the span context

        # Return index with values
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':

        if request.form['vote'] == 'reset':
            # Empty table and return results
            r.set(button1, 0)
            r.set(button2, 0)
            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}
            logger.info('Cats Vote', extra=properties)  # Log cat vote

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}
            logger.info('Dogs Vote', extra=properties)  # Log dog vote

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:
            # Insert vote result into DB
            vote = request.form['vote']
            r.incr(vote, 1)

            # Log specific events for Cats Vote and Dogs Vote
            if vote == button1:
                event_name = "Cats Vote"
            else:
                event_name = "Dogs Vote"

            # Log the event using Application Insights
            properties = {'custom_dimensions': {event_name: r.get(vote).decode('utf-8')}}
            logger.info(f'{event_name}', extra=properties)

            # Track the custom event in Application Insights
            telemetry_client = tracer.exporter.client
            telemetry_client.track_event(event_name, properties)

            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')

            # Return results
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # Use the statement below when running locally
    # app.run() 
    # Use the statement below before deployment to VMSS
    app.run(host='0.0.0.0', threaded=True, debug=True) # remote
