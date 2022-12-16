#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
THIS FILE IS FOR TESTING FUNCTIONALITY AND CONNECTION TO
MQTT BROKER AND TEMI.
RUN AS PYTHON SCRIPT, CANNOT USE IN ROS.
VSCODE USE
PYCHARM USE SCRIPT IN TEST FOLDER
"""


"""Sample script

"""


from connectpy import connect
from robot import Robot
import time
import yaml


# parameters
#find yaml file in configs folder
with open('configs/mqtt.yaml', "r") as stream:
    try:
        # parameters
        MQTT = yaml.safe_load(stream)
        MQTT_HOST = MQTT['HOST']
        MQTT_PORT = MQTT['PORT']
        MQTT_USER = MQTT['USERNAME']
        MQTT_PASSWORD = MQTT['PASSWORD']
        TEMI_SERIAL = MQTT['SERIAL']
    except yaml.YAMLError as exc:
        print(exc)

# connect to the MQTT broker
mqtt_client = connect(MQTT_HOST, MQTT_PORT,MQTT_USER,MQTT_PASSWORD)

# create robot object
robot = Robot(mqtt_client, TEMI_SERIAL)

# robot.tts("Hello World!")
# time.sleep(0.1)
# print('position', list(robot.currentPosition.values())[:3])
# print('battery', robot.battery['percentage'])

for n in range(1):
    robot.get_battery_data()
    time.sleep(2)

i = 0
while True:
    i += 1

# robot.goToLocation("sofa")
# time.sleep(1)
# robot.goToPosition(-2.8654, -14.0482, 1.0872)

# robot.goToPosition(2.1351, 7.9756, 0.8743)

# # print("navigationCompleted", robot.navigationCompleted())
# # print("checkIfDockingCompleted", robot.checkIfDockingCompleted())
#
# while robot.status != "complete":
#     continue
#
# print(robot.status)
# print(robot.currentLocation)
# print("navigationCompleted", robot.navigationCompleted())

# get_current_position will trigger skidjoy if robot isnt moving,
# otherwise currentPosition stores the last updated position
# robot.get_current_position()
# time.sleep(2)  # wait some time for action to complete
# print(robot.currentPosition)

