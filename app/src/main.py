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

# flake8: noqa: E501,B950 line too long
import asyncio
import json
import logging
import signal

from sdv.util.log import (  # type: ignore
    get_opentelemetry_log_factory,
    get_opentelemetry_log_format,
)
from sdv.vdb.reply import DataPointReply
from sdv.vehicle_app import VehicleApp
from vehicle import Vehicle, vehicle  # type: ignore

# Configure the VehicleApp logger with the necessary log config and level.
logging.setLogRecordFactory(get_opentelemetry_log_factory())
logging.basicConfig(format=get_opentelemetry_log_format())
logging.getLogger().setLevel("DEBUG")
logger = logging.getLogger(__name__)


class AutoAdjustTempApp(VehicleApp):
    """Velocitas App for autoAdjustTemp."""

    def __init__(self, vehicle_client: Vehicle):
        super().__init__()
        self.Vehicle = vehicle_client
        self.hmiPresetTemp = None
        self.currentFanSpeed = None

    async def on_start(self):
        logger.info("HMI: Set desired temp: 25")
        await self.Vehicle.Cabin.HVAC.Station.Row1.Left.Temperature.set(25)
        logger.info("default fan speed: 50")
        await self.Vehicle.Cabin.HVAC.Station.Row1.Left.FanSpeed.set(50)

    
        await self.Vehicle.Cabin.HVAC.AmbientAirTemperature.subscribe(self.on_AmbientAirTemperature_changed)

    async def on_AmbientAirTemperature_changed(self, data: DataPointReply):
        AmbientAirTemperature = data.get(self.Vehicle.Cabin.HVAC.AmbientAirTemperature).value
        logger.info("on_AmbientAirTemperature_changed !!!")
        self.hmiPresetTemp = (await self.Vehicle.Cabin.HVAC.Station.Row1.Left.Temperature.get()).value
        if AmbientAirTemperature > (self.hmiPresetTemp + 1):
            self.currentFanSpeed = (await self.Vehicle.Cabin.HVAC.Station.Row1.Left.FanSpeed.get()).value
            if self.currentFanSpeed > 80:
                self.currentFanSpeed = 90
            else:
                self.currentFanSpeed = self.currentFanSpeed + 10
            await self.Vehicle.Cabin.HVAC.Station.Row1.Left.FanSpeed.set(self.currentFanSpeed)
        elif AmbientAirTemperature < (self.hmiPresetTemp - 1):
            self.currentFanSpeed = (await self.Vehicle.Cabin.HVAC.Station.Row1.Left.FanSpeed.get()).value
            if self.currentFanSpeed < 20:
                self.currentFanSpeed = 10
            else:
                self.currentFanSpeed = self.currentFanSpeed - 10
            await self.Vehicle.Cabin.HVAC.Station.Row1.Left.FanSpeed.set(self.currentFanSpeed)
        else:
            await self.Vehicle.Cabin.HVAC.Station.Row1.Left.FanSpeed.set(10)
        await asyncio.sleep(1)


async def main():
    logger.info("Starting AutoAdjustTempApp...")
    vehicle_app = AutoAdjustTempApp(vehicle)
    await vehicle_app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(signal.SIGTERM, LOOP.stop)
LOOP.run_until_complete(main())
LOOP.close()
