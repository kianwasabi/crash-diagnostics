# Copyright (c) 2022 Robert Bosch GmbH and Microsoft Corporation
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""A sample skeleton vehicle app."""

import asyncio
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import signal
import random
# from flask import Flask, request, send_file
# from flask_cors import CORS
import os


from vehicle import Vehicle, vehicle  # type: ignore
from velocitas_sdk.util.log import (  # type: ignore
    get_opentelemetry_log_factory,
    get_opentelemetry_log_format,
)
from velocitas_sdk.vdb.reply import DataPointReply
from velocitas_sdk.vehicle_app import VehicleApp, subscribe_topic

# Configure the VehicleApp logger with the necessary log config and level.
logging.setLogRecordFactory(get_opentelemetry_log_factory())
logging.basicConfig(format=get_opentelemetry_log_format())
logging.getLogger().setLevel("DEBUG")
logger = logging.getLogger(__name__)
GET_SPEED_REQUEST_TOPIC = "sampleapp/getSpeed"
GET_SPEED_RESPONSE_TOPIC = "sampleapp/getSpeed/response"
DATABROKER_SUBSCRIPTION_TOPIC_SPEED = "sampleapp/currentSpeed"
# GET_CRASHED_REQUEST_TOPIC = "sampleapp/getCrashed"
# GET_CRASHED_RESPONSE_TOPIC = "sampleapp/getCrashed/response"
DATABROKER_SUBSCRIPTION_TOPIC_CRASHED = "sampleapp/crashed"

# Configure the crash diagnostic logger (shoutout @Lagavulin9)
SPEED_LOG_PATH = "logs/vehicle/crash_diagnostic/"
SPEED_LOGGER_NAME = "speed"
SPEED_LOG_FORMAT = "%(asctime)s [%(name)s] - %(message)s"
os.makedirs(os.path.dirname(SPEED_LOG_PATH), exist_ok=True)
for file in os.listdir(SPEED_LOG_PATH):
    os.remove(SPEED_LOG_PATH + file)
speedLogHandler = TimedRotatingFileHandler(
    filename=SPEED_LOG_PATH+SPEED_LOGGER_NAME+".log",
    when="s", 
    interval=10, 
    backupCount=5, 
    encoding="UTF-8")
speedLogHandler.setFormatter(logging.Formatter(SPEED_LOG_FORMAT))
speedLogHandler.suffix = '%H-%M-%S'
speedLogHandler.extMatch
loggerCrashDiagnosticSpeed = logging.getLogger(SPEED_LOGGER_NAME)
loggerCrashDiagnosticSpeed.addHandler(speedLogHandler)
loggerCrashDiagnosticSpeed.setLevel("INFO")

# Flask server for crash diagnostic report
# Flask_app = Flask(__name__)
# CORS(Flask_app, resources={r"/*": {"origins": "*"}})
# DOMAIN = "https://localhost:4000"
# ENDPOINT = "api/crash_diagnostic_report"

class SampleApp(VehicleApp):
    """
    Sample skeleton vehicle app.

    The skeleton subscribes to a getSpeed MQTT topic
    to listen for incoming requests to get
    the current vehicle speed and publishes it to
    a response topic.

    It also subcribes to the VehicleDataBroker
    directly for updates of the
    Vehicle.Speed signal and publishes this
    information via another specific MQTT topic
    """

    def __init__(self, vehicle_client: Vehicle):
        # SampleApp inherits from VehicleApp.
        super().__init__()
        self.Vehicle = vehicle_client

    async def random_vehicle_crash(self):
        crashed = random.random() < 0.01
        if (crashed):
            return True
        return False

    # @Flask_app.route(ENDPOINT, methods=['GET'])
    # async def send_crash_diagnostic_report(self):        
    #     res_data = {"crashed ": }
    #     response = make_response(jsonify(res_data))

    async def on_start(self):
        """Run when the vehicle app starts"""
        # This method will be called by the SDK when the connection to the
        # Vehicle DataBroker is ready.
        # Here you can subscribe for the Vehicle Signals update (e.g. Vehicle Speed).
        await self.Vehicle.Speed.subscribe(self.on_speed_change)
        await self.Vehicle.Speed.subscribe(self.on_crashed_change)

    async def on_speed_change(self, data: DataPointReply):
        """The on_speed_change callback, this will be executed when receiving a new
        vehicle signal updates."""
        # Get the current vehicle speed value from the received DatapointReply.
        # The DatapointReply containes the values of all subscribed DataPoints of
        # the same callback.
        vehicle_speed = data.get(self.Vehicle.Speed).value

        # save received value to logger
        loggerCrashDiagnosticSpeed.info("vehicle_speed %s", vehicle_speed)

        # - Publishes current speed to MQTT Topic 
        # (i.e. DATABROKER_SUBSCRIPTION_TOPIC_SPEED).
        await self.publish_event(
            DATABROKER_SUBSCRIPTION_TOPIC_SPEED,
            json.dumps({"speed": vehicle_speed}),
        )

    async def on_crashed_change(self, data: DataPointReply):
        vehicle_crashed = await self.random_vehicle_crash()
        if vehicle_crashed: 
            await self.publish_event(
                DATABROKER_SUBSCRIPTION_TOPIC_CRASHED,
                json.dumps({"crashed ": vehicle_crashed}),
            )

    @subscribe_topic(GET_SPEED_REQUEST_TOPIC)
    async def on_get_speed_request_received(self, data: str) -> None:
        """The subscribe_topic annotation is used to subscribe for incoming
        PubSub events, e.g. MQTT event for GET_SPEED_REQUEST_TOPIC.
        """

        # Use the logger with the preferred log level (e.g. debug, info, error, etc)
        logger.debug(
            "PubSub event for the Topic: %s -> is received with the data: %s",
            GET_SPEED_REQUEST_TOPIC,
            data,
        )

        # Getting current speed from VehicleDataBroker using the DataPoint getter.
        vehicle_speed = (await self.Vehicle.Speed.get()).value
        # Do anything with the speed value.
        # Example:
        # - Publishes the vehicle speed to MQTT topic (i.e. GET_SPEED_RESPONSE_TOPIC).
        await self.publish_event(
            GET_SPEED_RESPONSE_TOPIC,
            json.dumps(
                {
                    "result": {
                        "status": 0,
                        "message": f"""Current Speed = {vehicle_speed}""",
                    },
                }
            ),
        )

    # @subscribe_topic(GET_CRASHED_REQUEST_TOPIC)
    # async def on_get_crashed_request_received(self, data: str) -> None:
    #     # Use the logger with the preferred log level (e.g. debug, info, error, etc)
    #     logger.debug(
    #         "PubSub event for the Topic: %s -> is received with the data: %s",
    #         GET_SPEED_REQUEST_TOPIC,
    #         data,
    #     )

    #     random_vehicle_crash = await self.random_vehicle_crash()

    #     # Publishes to MQTT topic 
    #     await self.publish_event(
    #         GET_CRASHED_RESPONSE_TOPIC,
    #         json.dumps(
    #             {
    #                 "result": {
    #                     "status": 0,
    #                     "message": f"""Current Speed = {random_vehicle_crash}""",
    #                 },
    #             }
    #         ),
    #     )



async def main():
    """Main function"""
    logger.info("Starting SampleApp...")
    # Constructing SampleApp and running it.
    vehicle_app = SampleApp(vehicle)
    await vehicle_app.run()
    await app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(signal.SIGTERM, LOOP.stop)
LOOP.run_until_complete(main())
LOOP.close()
