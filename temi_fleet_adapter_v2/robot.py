#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""temi Robot Class

"""
import json
import re
import time
import uuid

from datetime import datetime

from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties


def now():
    """Return time in string format"""
    return datetime.now().strftime("%H:%M:%S")


def _on_status(client, userdata, msg):
    """Periodically updates the locations in map"""
    d = json.loads(msg.payload)
    userdata["locations"] = d["waypoint_list"]


def _on_battery(client, userdata, msg):
    print("[{}] [SUB] [BATTERY] {}".format(now(), json.loads(msg.payload)))
    d = json.loads(msg.payload)["batteryData"]

    split_string = re.split('[= , ( )]', d)
    userdata["battery"]["percentage"] = float(split_string[2]) / 100
    userdata["battery"]["is_charging"] = split_string[-2]


def _on_goto(client, userdata, msg):
    d = json.loads(msg.payload)
    userdata["goto"]["location"] = d["location"]
    userdata["goto"]["status"] = d["status"]


def _on_user(client, userdata, msg):
    print("[{}] [SUB] [USER] {}".format(now(), json.loads(msg.payload)))
    userdata["user"] = json.loads(msg.payload)


def _on_currentPosition(client, userdata, msg):
    print("[{}] [SUB] [CURRENT POSITION] {}".format(now(), json.loads(msg.payload)))
    split_response = re.split('[= , )]', str(msg.payload))
    userdata["currentPosition"] = {"x": float(split_response[1]),
                                   "y": float(split_response[4]),
                                   "yaw": float(split_response[7]),
                                   "tiltAngle": float(split_response[10])}


def _on_durationToDestination(client, userdata, msg):
    print("[{}] [SUB] [DURATION TO DESTINATION] {}".format(now(), json.loads(msg.payload)))
    userdata["durationToDestination"] = json.loads(msg.payload)


def _on_receiveTestConnection(client, userdata, msg):
    # print("[{}] [SUB] [TEST RECEIVE MESSAGE] {}".format(now(), msg.payload))
    t = 1


class Robot:
    """Robot Class"""

    def __init__(self, mqtt_client, temi_serial, silent=True):
        """Constructor"""
        self.client = mqtt_client
        self.id = temi_serial
        self.silent = silent
        self.successfulResponse = False

        # set user data
        # initialized default values for temi robot for location and current position
        self.state = {"locations": ["home base"], "battery": {},
                      "goto": {"location": "home base", "status": "complete"}, "user": {},
                      "currentPosition": {"x": 0.0, "y": 0.0, "yaw": 0.0, "tiltAngle": 50},
                      "durationToDestination": {'duration': 0.0}}
        self.client.user_data_set(self.state)

        # attach subscription callbacks
        self.client.message_callback_add(
            "temi/{}/status/info".format(temi_serial), _on_status
        )
        self.client.message_callback_add(
            "temi/{}/status/utils/battery".format(temi_serial), _on_battery
        )
        self.client.message_callback_add(
            "temi/{}/status/utils/currentPosition".format(temi_serial), _on_currentPosition
        )
        self.client.message_callback_add(
            "temi/{}/status/utils/durationToDestination".format(temi_serial), _on_durationToDestination
        )
        self.client.message_callback_add(
            "temi/{}/event/waypoint/goto".format(temi_serial), _on_goto
        )
        self.client.message_callback_add(
            "temi/{}/event/user/detection".format(temi_serial), _on_user
        )
        self.client.message_callback_add(
            "temi/{}/event/test/testConnection".format(temi_serial), _on_receiveTestConnection
        )

        # call method to initialize battery information
        self.getBatteryData()
        self.getCurrentPosition()
        time.sleep(1)

    def checkIfDockingCompleted(self):
        return self.state == "complete" and self.currentLocation == "home base"

    def navigationCompleted(self):
        return self.status == "complete"

    def stop(self):
        """Stop"""
        if not self.silent:
            print("[CMD] Stop")

        topic = "temi/" + self.id + "/command/move/stop"

        try:
            self.successfulResponse = False

            responseTopic = "temi/" + self.id + "/responseTopic/move/stop"
            requestId = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%M-%d %H:%M:%S")
            payload = json.dumps({"requestId": requestId, "responseTopic": responseTopic, "timestamp": timestamp})

            def stop_callback(client, userdata, msg):
                if json.loads(msg.payload)["requestId"] == requestId:
                    self.successfulResponse = True

            self.client.message_callback_add(
                responseTopic.format(self.id), stop_callback
            )

            # Generate message with response topic and correlation data
            print("[{}] [PUB] [STOP] {}".format(now(), payload))
            self.client.publish(topic, payload, qos=2)

            # Loop to check if a response is received
            # Will loop 5 times or until a response is received
            for _ in range(5):
                if not self.successfulResponse:
                    time.sleep(0.5)
                else:
                    print("[{}] [SUCCESS] Response received for request ID: {}, {}".format(now(), requestId, topic))
                    break

            if not self.successfulResponse:
                print("[{}] [ERROR] Response not received for request ID: {}, {}".format(now(), requestId, topic))

        except Exception as e:
            print("Exception received when stopping robot! ", e)

    def goToLocation(self, location_name):
        self.state["goto"]["location"] = location_name
        self.state["goto"]["status"] = "start"

        """Go to a saved location"""
        if not self.silent:
            print("[CMD] Go-To Location: {}".format(location_name))

        topic = "temi/" + self.id + "/command/waypoint/goToLocation"

        try:
            self.successfulResponse = False

            responseTopic = "temi/" + self.id + "/responseTopic/waypoint/goToLocation"
            requestId = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%M-%d %H:%M:%S")
            payload = json.dumps({"requestId": requestId, "location": location_name,
                                  "responseTopic": responseTopic, "timestamp": timestamp})

            def go_to_location_callback(client, userdata, msg):
                if json.loads(msg.payload)["requestId"] == requestId:
                    self.successfulResponse = True

            self.client.message_callback_add(
                responseTopic.format(self.id), go_to_location_callback
            )

            # Generate message with response topic and correlation data
            print("[{}] [PUB] [GO TO LOCATION] {}".format(now(), payload))
            self.client.publish(topic, payload, qos=2)

            # Loop to check if a response is received
            # Will loop 5 times or until a response is received
            for _ in range(5):
                if not self.successfulResponse:
                    time.sleep(0.5)
                else:
                    print("[{}] [SUCCESS] Response received for request ID: {}, {}".format(now(), requestId, topic))
                    break

            if not self.successfulResponse:
                print("[{}] [ERROR] Response not received for request ID: {}, {}".format(now(), requestId, topic))

        except Exception as e:
            print("Exception received when going to location! ", e)

    def goToPosition(self, x, y, yaw, tiltAngle=22):
        self.state["goto"]["location"] = "COORDINATES"
        self.state["goto"]["status"] = "start"

        """Go to a position"""
        if not self.silent:
            print("[CMD] Go-To Position:({}, {}), Angle = {} ".format(x, y, yaw))

        topic = "temi/" + self.id + "/command/waypoint/goToPosition"
        try:
            self.successfulResponse = False

            responseTopic = "temi/" + self.id + "/responseTopic/waypoint/goToPosition"
            requestId = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%M-%d %H:%M:%S")
            payload = json.dumps({"requestId": requestId, "x": x, "y": y, "yaw": yaw, "tiltAngle": tiltAngle,
                                  "responseTopic": responseTopic, "timestamp": timestamp})

            def go_to_position_callback(client, userdata, msg):
                if json.loads(msg.payload)["requestId"] == requestId:
                    self.successfulResponse = True

            self.client.message_callback_add(
                responseTopic.format(self.id), go_to_position_callback
            )

            # Generate message with response topic and correlation data
            print("[{}] [PUB] [GO TO POSITION] {}".format(now(), payload))
            self.client.publish(topic, payload, qos=2)

            # Loop to check if a response is received
            # Will loop 5 times or until a response is received
            for _ in range(5):
                if not self.successfulResponse:
                    time.sleep(0.5)
                else:
                    print("[{}] [SUCCESS] Response received for request ID: {}, {}".format(now(), requestId, topic))
                    break

            if not self.successfulResponse:
                print("[{}] [ERROR] Response not received for request ID: {}, {}".format(now(), requestId, topic))

        except Exception as e:
            print("Exception received when going to position! ", e)

    def getBatteryData(self):
        """Get Battery Data"""
        if not self.silent:
            print("[CMD] Get Battery Data")
        topic = "temi/" + self.id + "/command/getData/batteryData"

        try:
            self.successfulResponse = False

            responseTopic = "temi/" + self.id + "/responseTopic/getData/batteryData"
            requestId = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%M-%d %H:%M:%S")
            payload = json.dumps({"requestId": requestId, "responseTopic": responseTopic, "timestamp": timestamp})

            def get_battery_data_callback(client, userdata, msg):
                if json.loads(msg.payload)["requestId"] == requestId:
                    self.successfulResponse = True

            self.client.message_callback_add(
                responseTopic.format(self.id), get_battery_data_callback
            )

            # Generate message with response topic and correlation data
            print("[{}] [PUB] [BATTERY] {}".format(now(), payload))
            self.client.publish(topic, payload, qos=2)

            # Loop to check if a response is received
            # Will loop 5 times or until a response is received
            for _ in range(5):
                if not self.successfulResponse:
                    time.sleep(0.5)
                else:
                    print("[{}] [SUCCESS] Response received for request ID: {}, {}".format(now(), requestId, topic))
                    break

            if not self.successfulResponse:
                print("[{}] [ERROR] Response not received for request ID: {}, {}".format(now(), requestId, topic))

        except Exception as e:
            print("Exception received when getting battery data! ", e)

    def getCurrentPosition(self):
        """Get Current Position"""
        if not self.silent:
            print("[CMD] Current Position")

        topic = "temi/" + self.id + "/command/getData/currentPosition"

        try:
            self.successfulResponse = False

            responseTopic = "temi/" + self.id + "/responseTopic/getData/currentPosition"
            requestId = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%M-%d %H:%M:%S")
            payload = json.dumps({"requestId": requestId, "responseTopic": responseTopic, "timestamp": timestamp})

            def get_current_position_callback(client, userdata, msg):
                if json.loads(msg.payload)["requestId"] == requestId:
                    self.successfulResponse = True

            self.client.message_callback_add(
                responseTopic.format(self.id), get_current_position_callback
            )

            # Generate message with response topic and correlation data
            print("[{}] [PUB] [CURRENT POSITION] {}".format(now(), payload))
            self.client.publish(topic, payload, qos=2)

            # Loop to check if a response is received
            # Will loop 5 times or until a response is received
            for _ in range(5):
                if not self.successfulResponse:
                    time.sleep(0.5)
                else:
                    print("[{}] [SUCCESS] Response received for request ID: {}, {}".format(now(), requestId, topic))
                    break

            if not self.successfulResponse:
                print("[{}] [ERROR] Response not received for request ID: {}, {}".format(now(), requestId, topic))

        except Exception as e:
            print("Exception received when getting current position! ", e)

    def loadMap(self, mapName, x=0.0, y=0.0, yaw=0.0, tiltAngle=22):
        """Load Map: Will be loaded to position (0, 0) in new map by default if no position is specified"""
        if not self.silent:
            print("[CMD] Load New Map with Map Name = {} ".format(mapName))

        topic = "temi/" + self.id + "/command/getData/loadMap"

        try:
            self.successfulResponse = False

            responseTopic = "temi/" + self.id + "/responseTopic/getData/loadMap"
            requestId = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%M-%d %H:%M:%S")
            payload = json.dumps({"requestId": requestId, "mapName": mapName, "x": x, "y": y, "yaw": yaw,
                                  "tiltAngle": tiltAngle, "responseTopic": responseTopic, "timestamp": timestamp})

            def load_map_callback(client, userdata, msg):
                if json.loads(msg.payload)["requestId"] == requestId:
                    self.successfulResponse = True

            self.client.message_callback_add(
                responseTopic.format(self.id), load_map_callback
            )

            # Generate message with response topic and correlation data
            print("[{}] [PUB] [LOAD MAP] {}".format(now(), payload))
            self.client.publish(topic, payload, qos=2)

            # Loop to check if a response is received
            # Will loop 5 times or until a response is received
            for _ in range(5):
                if not self.successfulResponse:
                    time.sleep(0.5)
                else:
                    print("[{}] [SUCCESS] Response received for request ID: {}, {}".format(now(), requestId, topic))
                    break

            if not self.successfulResponse:
                print("[{}] [ERROR] Response not received for request ID: {}, {}".format(now(), requestId, topic))

        except Exception as e:
            print("Exception received when loading map! ", e)

    def rotate(self, angle):
        """Rotate"""
        if not self.silent:
            print("[CMD] Rotate: {} [deg]".format(angle))

        if angle != 0:
            topic = "temi/" + self.id + "/command/move/turn_by"
            payload = json.dumps({"angle": angle})

            self.client.publish(topic, payload, qos=0)

    def tilt(self, angle):
        """Tilt head (absolute angle)"""
        if not self.silent:
            print("[CMD] Tilt: {} [deg]".format(angle))

        topic = "temi/" + self.id + "/command/move/tilt"
        payload = json.dumps({"angle": angle})

        self.client.publish(topic, payload, qos=0)

    def follow(self):
        """Follow"""
        if not self.silent:
            print("[CMD] Follow")

        topic = "temi/" + self.id + "/command/follow/unconstrained"

        self.client.publish(topic, "{}", qos=1)

    def joystick(self, x, y):
        """Joystick"""
        if not self.silent:
            print("[CMD] Translate: {} {} [unitless]".format(x, y))

        topic = "temi/" + self.id + "/command/move/joystick"
        payload = json.dumps({"x": x, "y": y})

        self.client.publish(topic, payload, qos=0)

    def tts(self, text):
        # print(self.currentPosition)
        """Text-to-speech"""
        if not self.silent:
            print("[CMD] TTS: {}".format(text))

        topic = "temi/" + self.id + "/command/tts"
        payload = json.dumps({"utterance": text})

        self.client.publish(topic, payload, qos=1)

    def video(self, url):
        """Play video"""
        if not self.silent:
            print("[CMD] Play Video: {}".format(url))

        topic = "temi/" + self.id + "/command/media/video"
        payload = json.dumps({"url": url})

        self.client.publish(topic, payload, qos=1)

    def webview(self, url):
        """Show webview"""
        if not self.silent:
            print("[CMD] Show Webview: {}".format(url))

        topic = "temi/" + self.id + "/command/media/webview"
        payload = json.dumps({"url": url})

        self.client.publish(topic, payload, qos=1)

    @property
    def locations(self):
        """Return a list of locations"""
        if "locations" in self.state:
            return self.state["locations"]
        else:
            return []

    @property
    def status(self):
        if "status" in self.state["goto"]:
            return self.state["goto"]["status"]
        else:
            return None

    @property
    def currentLocation(self):
        if "location" in self.state["goto"]:
            return self.state["goto"]["location"]
        else:
            return None

    @property
    def battery(self):
        return self.state["battery"]

    @property
    def currentPosition(self):
        return self.state["currentPosition"]

    @property
    def durationToDestination(self):
        return self.state["durationToDestination"]

    @property
    def GOTO_START(self):
        return "start"

    @property
    def GOTO_ABORT(self):
        return "abort"

    @property
    def GOTO_GOING(self):
        return "going"

    @property
    def GOTO_COMPLETE(self):
        return "complete"

    @property
    def GOTO_CALCULATING(self):
        return "calculating"

    @property
    def GOTO_OBSTACLE(self):
        return "obstacle detected"