# feed_thread.py

import threading
import time
import re
import datetime
from dobot_api import alarmAlarmJsonFile, DobotApiDashboard
from multi_terminal_gui import MultiTerminalGUI

# Locks for thread synchronization
feed_lock = threading.Lock()
error_lock = threading.Lock()

# Robot state variables (updated by GetFeed200ms thread)
robotMode = 0
algorithm_queue = 0
enableStatus_robot = 0
robotErrorState = False
posizione_attuale = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
angoli_attuali = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

def converti_feed_in_string(values):
    """
    Convert a list of angle values to a formatted string.
    """
    s = "[ "
    for angle in values:
        s += f"{angle:.3f}° "
    s += "]"
    return s

def GetFeed200ms(feedFour):
    """
    Thread function: continuously read feedback from the robot every 200ms.
    Updates global state variables with the latest values.
    """
    global robotMode, algorithm_queue, enableStatus_robot, robotErrorState, posizione_attuale, angoli_attuali
    while True:
        with feed_lock:
            feedInfo = feedFour.feedBackData()
            # Check for valid data
            if hex(feedInfo['test_value'][0]) == '0x123456789abcdef':
                robotMode = feedInfo['robot_mode'][0]
                algorithm_queue = feedInfo['run_queued_cmd'][0]
                enableStatus_robot = feedInfo['enable_status'][0]
                robotErrorState = feedInfo['error_status'][0]
                posizione_attuale = feedInfo['tool_vector_actual'][0]
                angoli_attuali = feedInfo['q_actual'][0]
        time.sleep(0.2)

def stampaFeed(gui: MultiTerminalGUI):
    """
    Thread function: prints the current robot status periodically.
    """
    while True:
        now_str = datetime.datetime.now().strftime("%H:%M:%S") + "\n"
        status_str = f"Robot Mode: {robotMode}\n"
        status_str += f"Robot Error State: {robotErrorState}\n"
        status_str += f"Enable Status: {enableStatus_robot}\n"
        status_str += f"Algorithm Queue: {algorithm_queue}\n"
        status_str += "Coordinate attuali: " + converti_feed_in_string(posizione_attuale) + "\n"
        status_str += "Angoli attuali: " + converti_feed_in_string(angoli_attuali) + "\n"
        gui.write_to_terminal(5, now_str + status_str)
        time.sleep(0.2)

def ClearRobotError(dashboard: DobotApiDashboard, gui: MultiTerminalGUI):
    """
    Thread function: monitors and clears robot errors if any.
    """
    global robotErrorState
    # Load error descriptions
    dataController, dataServo = alarmAlarmJsonFile()
    while True:
        error_lock.acquire()
        if robotErrorState:
            numbers = re.findall(r'-?\d+', dashboard.GetErrorID())
            numbers = [int(num) for num in numbers]
            if numbers and numbers[0] == 0:
                if len(numbers) > 1:
                    for i in numbers[1:]:
                        alarmState = False
                        if i == -2:
                            gui.write_to_terminal(4, f"Robot in collisione, ID: {i}")
                            alarmState = True
                        if alarmState:
                            continue
                        # Check controller errors
                        for item in dataController:
                            if i == item["id"]:
                                gui.write_to_terminal(4, f"Errore del controller, id: {i}, descrizione: {item['en']['description']}")
                                alarmState = True
                                break
                        if alarmState:
                            continue
                        # Check servo errors
                        for item in dataServo:
                            if i == item["id"]:
                                gui.write_to_terminal(4, f"Errore dei servomotori, id: {i}, descrizione: {item['en']['description']}")
                                break

                    # Prompt user to clear error
                    choose = input("Inserisci 1 per ripulire gli errori del robot e far ripartire: ")
                    if choose.strip() == "1":
                        dashboard.ClearError()
                        time.sleep(0.01)
                        dashboard.Continue()
        else:
            # If no error, continue execution when ready
            try:
                if int(enableStatus_robot) == 1 and int(algorithm_queue) == 0:
                    dashboard.Continue()
            except Exception:
                pass
        error_lock.release()
        time.sleep(3)
