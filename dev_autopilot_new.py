#!/usr/bin/env python
# coding: utf-8

# References
# Useful docs / articles / etc
#   
#   1 - [A Python wrapper around AHK](https://pypi.org/project/ahk/)
# 
#   2 - [OpenCV on Wheels](https://pypi.org/project/opencv-python/)
# 
#   3 - [Autopilot for Elite Dangerous using OpenCV and thoughts on CV enabled bots in visual-to-keyboard loop](https://networkgeekstuff.com/projects/autopilot-for-elite-dangerous-using-opencv-and-thoughts-on-cv-enabled-bots-in-visual-to-keyboard-loop/)
#   
#   4 - [Using PyInstaller to Easily Distribute Python Applications](https://realpython.com/pyinstaller-python/)
#   
#   5 - [Direct Input to a Game - Python Plays GTA V](https://pythonprogramming.net/direct-input-game-python-plays-gta-v/)
#   
#   6 - [Cross-platform GUI automation for human beings](https://pyautogui.readthedocs.io/en/latest/index.html)

# Imports
import datetime
import math
import random as rand
import sys
import threading
from datetime import datetime
from json import loads
from os import environ, listdir
from os.path import join, isfile, getmtime, abspath
from time import sleep
from xml.etree.ElementTree import parse
from matplotlib import pyplot as plt

import colorlog
import cv2  # see reference 2
import numpy as np
from PIL import ImageGrab
from pyautogui import size  # see reference 6

#import autopilot_utils
from Keyboard import Keyboard
from logger import setup_logger

class Autopilot(threading.Thread):
    run = False

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def start(self):
        self.autopilot()

    def startAutopilot(self):
        print("starting")
        self.run = True

    def stopAutopilot(self):
        print("stopping")
        self.run = False

    # Constants
    RELEASE = 'v19.05.15-alpha-18'
    PATH_LOG_FILES = None
    PATH_KEYBINDINGS = None
    KEY_MOD_DELAY = 0.010
    KEY_DEFAULT_DELAY = 0.200
    KEY_REPEAT_DELAY = 0.100
    FUNCTION_DEFAULT_DELAY = 0.500
    SCREEN_WIDTH, SCREEN_HEIGHT = size()
    BIG_SCREEN = True if SCREEN_WIDTH == 3840 else False

    logger = setup_logger("autopilot")

    logger.info('---- AUTOPILOT DATA '+180*'-')
    logger.info('RELEASE='+str(RELEASE))
    logger.info('PATH_LOG_FILES='+str(PATH_LOG_FILES))
    logger.info('PATH_KEYBINDINGS='+str(PATH_KEYBINDINGS))
    logger.info('KEY_MOD_DELAY='+str(KEY_MOD_DELAY))
    logger.info('KEY_DEFAULT_DELAY='+str(KEY_DEFAULT_DELAY))
    logger.info('KEY_REPEAT_DELAY='+str(KEY_REPEAT_DELAY))
    logger.info('FUNCTION_DEFAULT_DELAY='+str(FUNCTION_DEFAULT_DELAY))
    logger.info('SCREEN_WIDTH='+str(SCREEN_WIDTH))
    logger.info('SCREEN_HEIGHT='+str(SCREEN_HEIGHT))

    # Autopilot routines

    # Undock
    def undock(self):
        self.logger.debug('undock')
        if autopilot_utils.ship()['status'] != "in_station":
            self.logger.error('undock=err1')
            raise Exception('undock error 1')
        self.send(self.keys['UI_Back'], repeat=10)
        self.send(self.keys['HeadLookReset'])
        self.send(self.keys['UI_Down'], hold=3)
        self.send(self.keys['UI_Select'])
        sleep(1)
        if not (autopilot_utils.ship()['status'] == "starting_undock" or autopilot_utils.ship()['status'] == "in_undock"):
            self.logger.error('undock=err2')
            raise Exception("undock error 2")
        self.send(self.keys['HeadLookReset'])
        self.send(self.keys['SetSpeedZero'], repeat=2)
        wait = 120
        for i in range(wait):
            sleep(1)
            if i > wait-1:
                self.logger.error('undock=err3')
                raise Exception('undock error 3')
            if autopilot_utils.ship()['status'] == "in_space":
                break
        self.logger.debug('undock=complete')
        return True

    # Dock
    def dock(self):
        self.logger.debug('dock')
        if autopilot_utils.ship()['status'] != "in_space":
            self.logger.error('dock=err1')
            raise Exception('dock error 1')
        tries = 3
        for i in range(tries):
            self.send(self.keys['UI_Back'], repeat=10)
            self.send(self.keys['HeadLookReset'])
            self.send(self.keys['UIFocus'], state=1)
            self.send(self.keys['UI_Left'])
            self.send(self.keys['UIFocus'], state=0)
            self.send(self.keys['CycleNextPanel'], repeat=2)
            self.send(self.keys['UI_Up'], hold=3)
            self.send(self.keys['UI_Right'])
            self.send(self.keys['UI_Select'])
            sleep(1)
            if autopilot_utils.ship()['status'] == "starting_dock" or autopilot_utils.ship()['status'] == "in_dock":
                break
            if i > tries-1:
                self.logger.error('dock=err2')
                raise Exception("dock error 2")
        self.send(self.keys['UI_Back'])
        self.send(self.keys['HeadLookReset'])
        self.send(self.keys['SetSpeedZero'], repeat=2)
        wait = 120
        for i in range(wait):
            sleep(1)
            if i > wait-1:
                self.logger.error('dock=err3')
                raise Exception('dock error 3')
            if autopilot_utils.ship()['status'] == "in_station":
                break
        self.send(self.keys['UI_Up'], hold=3)
        self.send(self.keys['UI_Down'])
        self.send(self.keys['UI_Select'])
        self.logger.debug('dock=complete')
        return True

    # Align
    def x_angle(self, point=None):
        if not point or point['x'] == 0:
            return None
        result = math.degrees(math.atan(point['y']/point['x']))
        if point['x'] > 0:
            return +90-result
        else:
            return -90-result

    def align(self):
        self.logger.info('Starting Alignment')
        if not (autopilot_utils.ship()['status'] == 'in_supercruise' or autopilot_utils.ship()['status'] == 'in_space'):
            self.logger.error('align=err1')
            raise Exception('align error 1')

        self.logger.debug('align=speed 100')
        self.send(self.keys['SetSpeed100'])

        self.logger.info('Alignment Step: Avoid sun')
        while self.sun_percent() > 5:
            self.send(self.keys['PitchUpButton'], state=1)
        self.send(self.keys['PitchUpButton'], state=0)

        self.logger.info('Alignment Step: Find navpoint')
        off = self.get_navpoint_offset()
        while not off:
            self.send(self.keys['PitchUpButton'], state=1)
            off = self.get_navpoint_offset()
        self.send(self.keys['PitchUpButton'], state=0)

        self.logger.info('Alignment Step: Crude align')
        close = 3
        close_a = 18
        hold_pitch = 0.350
        hold_roll = 0.170
        ang = self.x_angle(off)
        while (off['x'] > close and ang > close_a) or (off['x'] < -close and ang < -close_a) or (off['y'] > close) or (off['y'] < -close):

            while (off['x'] > close and ang > close_a) or (off['x'] < -close and ang < -close_a):

                if off['x'] > close and ang > close:
                    self.send(self.keys['RollRightButton'], hold=hold_roll)
                if off['x'] < -close and ang < -close:
                    self.send(self.keys['RollLeftButton'], hold=hold_roll)

                if autopilot_utils.ship()['status'] == 'starting_hyperspace':
                    return
                off = self.get_navpoint_offset(last=off)
                ang = self.x_angle(off)

            while (off['y'] > close) or (off['y'] < -close):

                if off['y'] > close:
                    self.send(self.keys['PitchUpButton'], hold=hold_pitch)
                if off['y'] < -close:
                    self.send(self.keys['PitchDownButton'], hold=hold_pitch)

                if autopilot_utils.ship()['status'] == 'starting_hyperspace':
                    return
                off = self.get_navpoint_offset(last=off)

            off = self.get_navpoint_offset(last=off)
            ang = self.x_angle(off)

        self.logger.info('Alignment Step: Fine align')
        sleep(0.5)
        close = 50
        hold_pitch = 0.200
        hold_yaw = 0.400
        for i in range(5):
            new = self.get_destination_offset()
            if new:
                off = new
                break
            sleep(0.25)
        if not off:
            return
        while (off['x'] > close) or (off['x'] < -close) or (off['y'] > close) or (off['y'] < -close):

            if off['x'] > close:
                self.send(self.keys['YawRightButton'], hold=hold_yaw)
            if off['x'] < -close:
                self.send(self.keys['YawLeftButton'], hold=hold_yaw)
            if off['y'] > close:
                self.send(self.keys['PitchUpButton'], hold=hold_pitch)
            if off['y'] < -close:
                self.send(self.keys['PitchDownButton'], hold=hold_pitch)

            if autopilot_utils.ship()['status'] == 'starting_hyperspace':
                return

            for i in range(5):
                new = self.get_destination_offset()
                if new:
                    off = new
                    break
                sleep(0.25)
            if not off:
                return

        self.logger.info('Alignment Complete')

    # Jump
    def jump(self):
        self.logger.info('Starting Jump')
        tries = 3
        for i in range(tries):
            self.logger.debug('jump=try:'+str(i))
            if not (autopilot_utils.ship()['status'] == 'in_supercruise' or autopilot_utils.ship()['status'] == 'in_space'):
                self.logger.error('jump=err1')
                raise Exception('not ready to jump')
            sleep(0.5)
            self.logger.info('Charging FSD')
            self.send(self.keys['HyperSuperCombination'], hold=1)
            sleep(16)
            if autopilot_utils.ship()['status'] != 'starting_hyperspace':
                self.logger.info('Trajectory Misaligned. Jump Failed. Retrying Alignment')
                self.send(self.keys['HyperSuperCombination'], hold=1)
                sleep(2)
                self.align()
            else:
                self.logger.info('Jump in Progress')
                while autopilot_utils.ship()['status'] != 'in_supercruise':
                    sleep(1)
                self.logger.debug('jump=speed 0')
                self.send(self.keys['SetSpeedZero'])
                self.logger.info('Jump Complete')
                return True
        self.logger.error('jump=err2')
        raise Exception("jump failure")

    # Refuel
    def refuel(self, refuel_threshold=40):
        self.logger.debug('refuel')
        scoopable_stars = ['F', 'O', 'G', 'K', 'B', 'A', 'M']
        if autopilot_utils.ship()['status'] != 'in_supercruise':
            self.logger.error('refuel=err1')
            return False

        if autopilot_utils.ship()['fuel_percent'] < refuel_threshold and autopilot_utils.ship()['star_class'] in scoopable_stars:
            self.logger.info('Starting Refuel')
            self.send(self.keys['SetSpeed100'])
            sleep(4)
            self.logger.info('Refuel in Progress')
            self.send(self.keys['SetSpeedZero'], repeat=3)
            while not autopilot_utils.ship()['fuel_percent'] == 100:
                sleep(1)
            self.logger.info('Refuel Complete')
            return True
        elif autopilot_utils.ship()['fuel_percent'] >= refuel_threshold:
            self.logger.info('Refuel not Needed')
            return False
        elif autopilot_utils.ship()['star_class'] not in scoopable_stars:
            self.logger.info('Refuel Needed, Unsuitable Star')
            return False
        else:
            return False

    # Discovery scanner
    scanner = 1

    def set_scanner(self, state):
        global scanner
        scanner = state
        self.logger.debug('set_scanner='+str(scanner))

    def get_scanner(self):
        from dev_tray import STATE
        return STATE

    # Position
    def position(self, refueled_multiplier=1):
        self.logger.debug('position')
        scan = 2  # get_scanner()
        if scan == 1:
            self.logger.info('Scanning')
            self.send(self.keys['PrimaryFire'], state=1)
        elif scan == 2:
            self.logger.info('Scanning')
            self.send(self.keys['SecondaryFire'], state=1)
        else:
            self.logger.info('Scanning Disabled')
        self.send(self.keys['PitchUpButton'], state=1)
        sleep(5)
        self.send(self.keys['PitchUpButton'], state=0)
        self.send(self.keys['SetSpeed100'])
        self.send(self.keys['PitchUpButton'], state=1)
        while self.sun_percent() > 3:
            sleep(1)
        sleep(5)
        self.send(self.keys['PitchUpButton'], state=0)
        sleep(5*refueled_multiplier)
        if scan == 1:
            self.logger.info('Scanning Complete')
            self.send(self.keys['PrimaryFire'], state=0)
        elif scan == 2:
            self.logger.info('Scanning Complete')
            self.send(self.keys['SecondaryFire'], state=0)
        self.logger.debug('position=complete')
        return True

    # Autopilot main

    # status reference
    #
    # 'in-station'
    #
    # 'in-supercruise'
    #
    # 'in-space'
    #
    # 'starting-undocking'
    #
    # 'in-undocking'
    #
    # 'starting-docking'
    #
    # 'in-docking'

    def autopilot(self):
        while True:
            # self.logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT START '+179*'-'+'\n'+200*'-')
            while not self.run:
                sleep(1)

            self.logger.info('---- AUTOPILOT START '+179*'-')

            keyboard = Keyboard()

            while self.run:
                for i in list(range(3))[::-1]:
                    if not self.run:
                        return
                    print(i+1)
                    sleep(1)
                print('press')

                keyboard.tap(keyboard.keys['UI_Up'])

            '''
            self.logger.debug('get_latest_log='+str(self.get_latest_log(self.PATH_LOG_FILES)))
            self.logger.debug('ship='+str(autopilot_utils.ship()))
            while autopilot_utils.ship()['target']:
                if autopilot_utils.ship()['status'] == 'in_space' or autopilot_utils.ship()['status'] == 'in_supercruise':
                    # self.logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT ALIGN '+179*'-'+'\n'+200*'-')
                    self.logger.info('---- AUTOPILOT ALIGN '+179*'-')
                    self.align()
                    # self.logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT JUMP '+180*'-'+'\n'+200*'-')
                    self.logger.info('---- AUTOPILOT JUMP '+180*'-')
                    self.jump()
                    # self.logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT REFUEL '+178*'-'+'\n'+200*'-')
                    self.logger.info('---- AUTOPILOT REFUEL '+178*'-')
                    refueled = self.refuel()
                    # self.logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT POSIT '+179*'-'+'\n'+200*'-')
                    self.logger.info('---- AUTOPILOT SCAN '+180*'-')
                    if refueled:
                        self.position(refueled_multiplier=4)
                    else:
                        self.position(refueled_multiplier=1)
            self.send(self.keys['SetSpeedZero'])
            # self.logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT END '+181*'-'+'\n'+200*'-')
            self.logger.info('---- AUTOPILOT END '+181*'-')
            '''
