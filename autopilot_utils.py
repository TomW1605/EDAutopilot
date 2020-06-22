import datetime
from datetime import datetime
import logging

import cv2
import numpy as np
import random as rand
from os import environ, listdir
from os.path import join, isfile, getmtime, abspath
import sys
from json import loads
from xml.etree.ElementTree import parse
from src.directinput import SCANCODE, PressKey, ReleaseKey
from time import sleep
from PIL import ImageGrab
import colorlog
from logger import setup_logger

logger = setup_logger("utils")

# Read ED logs
# Get latest log file
def get_latest_log(path_logs=None):
    """Returns the full path of the latest (most recent) elite log file (journal) from specified path"""
    if not path_logs:
        path_logs = environ['USERPROFILE']+"\Saved Games\Frontier Developments\Elite Dangerous"
    list_of_logs = [join(path_logs, f) for f in listdir(path_logs) if isfile(join(path_logs, f)) and f.startswith('Journal.')]
    if not list_of_logs:
        return None
    latest_log = max(list_of_logs, key=getmtime)
    return latest_log

logger.info('get_latest_log='+str(get_latest_log(PATH_LOG_FILES)))

# Extract ship info from log
def ship():
    """Returns a 'status' dict containing relevant game status information (state, fuel, ...)"""
    latest_log = get_latest_log(PATH_LOG_FILES)
    ship_status = {
        'time': (datetime.now()-datetime.fromtimestamp(getmtime(latest_log))).seconds,
        'status': None,
        'type': None,
        'location': None,
        'star_class': None,
        'target': None,
        'fuel_capacity': None,
        'fuel_level': None,
        'fuel_percent': None,
        'is_scooping': False,
    }
    # Read log line by line and parse data
    with open(latest_log, encoding="utf-8") as f:
        for line in f:
            log = loads(line)

            # parse data
            try:
                # parse ship status
                log_event = log['event']

                if log_event == 'StartJump':
                    ship_status['status'] = str('starting_'+log['JumpType']).lower()

                elif log_event == 'SupercruiseEntry' or log_event == 'FSDJump':
                    ship_status['status'] = 'in_supercruise'

                elif log_event == 'SupercruiseExit' or log_event == 'DockingCancelled' or (log_event == 'Music' and ship_status['status'] == 'in_undocking') or (log_event == 'Location' and log['Docked'] == False):
                    ship_status['status'] = 'in_space'

                elif log_event == 'Undocked':
                    ship_status['status'] = 'in_space'

                elif log_event == 'DockingRequested':
                    ship_status['status'] = 'starting_docking'

                elif log_event == "Music" and log['MusicTrack'] == "DockingComputer":
                    if ship_status['status'] == 'starting_undocking':
                        ship_status['status'] = 'in_undocking'
                    elif ship_status['status'] == 'starting_docking':
                        ship_status['status'] = 'in_docking'

                elif log_event == 'Docked':
                    ship_status['status'] = 'in_station'

                # parse ship type
                if log_event == 'LoadGame' or log_event == 'Loadout':
                    ship_status['type'] = log['Ship']

                # parse fuel
                if 'FuelLevel' in log and ship_status['type'] != 'TestBuggy':
                    ship_status['fuel_level'] = log['FuelLevel']
                if 'FuelCapacity' in log and ship_status['type'] != 'TestBuggy':
                    try:
                        ship_status['fuel_capacity'] = log['FuelCapacity']['Main']
                    except:
                        ship_status['fuel_capacity'] = log['FuelCapacity']
                if log_event == 'FuelScoop' and 'Total' in log:
                    ship_status['fuel_level'] = log['Total']
                if ship_status['fuel_level'] and ship_status['fuel_capacity']:
                    ship_status['fuel_percent'] = round((ship_status['fuel_level']/ship_status['fuel_capacity'])*100)
                else:
                    ship_status['fuel_percent'] = 10

                # parse scoop
                if log_event == 'FuelScoop' and ship_status['time'] < 10 and ship_status['fuel_percent'] < 100:
                    ship_status['is_scooping'] = True
                else:
                    ship_status['is_scooping'] = False

                # parse location
                if (log_event == 'Location' or log_event == 'FSDJump') and 'StarSystem' in log:
                    ship_status['location'] = log['StarSystem']
                if 'StarClass' in log:
                    ship_status['star_class'] = log['StarClass']

                # parse target
                if log_event == 'FSDTarget':
                    if log['Name'] == ship_status['location']:
                        ship_status['target'] = None
                    else:
                        ship_status['target'] = log['Name']
                elif log_event == 'FSDJump':
                    if ship_status['location'] == ship_status['target']:
                        ship_status['target'] = None

            # exceptions
            except Exception as trace:
                logger.exception("Exception occurred")
                print(trace)
    #     logger.debug('ship='+str(ship))
    return ship_status

# OpenCV
# Get screen
def get_screen(x_left, y_top, x_right, y_bot):
    screen = np.array(ImageGrab.grab(bbox=(x_left, y_top, x_right, y_bot)))
    screen = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
    return screen

# HSV slider tool
def callback(x):
    pass

def hsv_slider(bandw=False):
    cv2.namedWindow('image')

    iTop = 0
    iBottom = SCREEN_HEIGHT

    iLeft = 0
    iRight = SCREEN_WIDTH

    # create trackbars for frame
    cv2.createTrackbar('Top', 'image', iTop, SCREEN_HEIGHT, callback)
    cv2.createTrackbar('Bottom', 'image', iBottom, SCREEN_HEIGHT, callback)

    cv2.createTrackbar('Left', 'image', iLeft, SCREEN_WIDTH, callback)
    cv2.createTrackbar('Right', 'image', iRight, SCREEN_WIDTH, callback)

    ilowH = 0
    ihighH = 179

    ilowS = 0
    ihighS = 255
    ilowV = 0
    ihighV = 255

    # create trackbars for color change
    cv2.createTrackbar('lowH', 'image', ilowH, 179, callback)
    cv2.createTrackbar('highH', 'image', ihighH, 179, callback)

    cv2.createTrackbar('lowS', 'image', ilowS, 255, callback)
    cv2.createTrackbar('highS', 'image', ihighS, 255, callback)

    cv2.createTrackbar('lowV', 'image', ilowV, 255, callback)
    cv2.createTrackbar('highV', 'image', ihighV, 255, callback)

    while True:
        # grab the frame
        frame = get_screen(iLeft, iTop, iRight, iBottom)
        if bandw:
            frame = equalize(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        iTop = cv2.getTrackbarPos('Top', 'image')
        iBottom = cv2.getTrackbarPos('Bottom', 'image')

        iLeft = cv2.getTrackbarPos('Left', 'image')
        iRight = cv2.getTrackbarPos('Right', 'image')

        if iTop >= iBottom:
            iTop = iBottom-1

        if iLeft >= iRight:
            iLeft = iRight-1

        # get trackbar positions
        ilowH = cv2.getTrackbarPos('lowH', 'image')
        ihighH = cv2.getTrackbarPos('highH', 'image')
        ilowS = cv2.getTrackbarPos('lowS', 'image')
        ihighS = cv2.getTrackbarPos('highS', 'image')
        ilowV = cv2.getTrackbarPos('lowV', 'image')
        ihighV = cv2.getTrackbarPos('highV', 'image')

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([ilowH, ilowS, ilowV])
        higher_hsv = np.array([ihighH, ihighS, ihighV])
        mask = cv2.inRange(hsv, lower_hsv, higher_hsv)

        frame = cv2.bitwise_and(frame, frame, mask=mask)

        # show thresholded image
        cv2.imshow('image', frame)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break

# Equalization
def equalize(image=None, testing=False):
    while True:
        if testing:
            img = get_screen((5/16)*SCREEN_WIDTH, (5/8)*SCREEN_HEIGHT, (2/4)*SCREEN_WIDTH, (15/16)*SCREEN_HEIGHT)
        else:
            img = image.copy()
        # Load the image in greyscale
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # create a CLAHE object (Arguments are optional).
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_out = clahe.apply(img_gray)
        if testing:
            cv2.imshow('Equalized', img_out)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            break
    return img_out

# Filter bright
def filter_bright(image=None, testing=False):
    while True:
        if testing:
            img = get_screen((5/16)*SCREEN_WIDTH, (5/8)*SCREEN_HEIGHT, (2/4)*SCREEN_WIDTH, (15/16)*SCREEN_HEIGHT)
        else:
            img = image.copy()
        equalized = equalize(img)
        equalized = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)
        equalized = cv2.cvtColor(equalized, cv2.COLOR_BGR2HSV)
        filtered = cv2.inRange(equalized, np.array([0, 0, 215]), np.array([0, 0, 255]))
        if testing:
            cv2.imshow('Filtered', filtered)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            break
    return filtered

# Filter sun
def filter_sun(image=None, testing=False):
    while True:
        if testing:
            hsv = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
        else:
            hsv = image.copy()
        # converting from BGR to HSV color space
        hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)
        # filter Elite UI orange
        filtered = cv2.inRange(hsv, np.array([0, 100, 240]), np.array([180, 255, 255]))
        if testing:
            cv2.imshow('Filtered', filtered)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            break
    return filtered

# Filter orange
def filter_orange(image=None, testing=False):
    while True:
        if testing:
            hsv = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
        else:
            hsv = image.copy()
        # converting from BGR to HSV color space
        hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)
        # filter Elite UI orange
        filtered = cv2.inRange(hsv, np.array([0, 130, 123]), np.array([25, 235, 220]))
        if testing:
            cv2.imshow('Filtered', filtered)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            break
    return filtered

# Filter orange2
def filter_orange2(image=None, testing=False):
    while True:
        if testing:
            hsv = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
        else:
            hsv = image.copy()
        # converting from BGR to HSV color space
        hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)
        # filter Elite UI orange
        filtered = cv2.inRange(hsv, np.array([15, 220, 220]), np.array([30, 255, 255]))
        if testing:
            cv2.imshow('Filtered', filtered)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            break
    return filtered

# Filter blue
def filter_blue(image=None, testing=False):
    while True:
        if testing:
            hsv = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
        else:
            hsv = image.copy()
        # converting from BGR to HSV color space
        hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)
        # filter Elite UI orange
        filtered = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 100, 255]))
        if testing:
            cv2.imshow('Filtered', filtered)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            break
    return filtered

# Get sun
def sun_percent():
    screen = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
    filtered = filter_sun(screen)
    white = np.sum(filtered == 255)
    black = np.sum(filtered != 255)
    result = white/black
    return result*100

# Target body
def has_target_body_keypoint_matching(testing=True):
    target_template = cv2.imread(resource_path("templates/target.png"), cv2.IMREAD_GRAYSCALE)
    # target_template = cv2.imread(resource_path("templates/dest.png"))
    while True:
        screen = get_screen((0/40)*SCREEN_WIDTH, (17/40)*SCREEN_HEIGHT, (14/40)*SCREEN_WIDTH, (40/40)*SCREEN_HEIGHT)
        equalized = equalize(screen)

        # screen = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
        # equalized = filter_orange2(screen)

        orb = cv2.ORB_create(nfeatures=50000, fastThreshold=1, edgeThreshold=5, patchSize=5)

        kp1, des1 = orb.detectAndCompute(target_template, None)
        kp2, des2 = orb.detectAndCompute(equalized, None)

        if des1 is not None and des2 is not None:
            bf = cv2.BFMatcher(cv2.NORM_L1, crossCheck=False)

            matches = bf.match(des1, des2)

            matches = sorted(matches, key=lambda x: x.distance)

            good = []
            for m in matches:
                if m.distance == 0:
                    good.append(m)
            print(len(good))

            if testing:
                match = cv2.drawMatches(target_template, kp1, equalized, kp2, good, None, flags=2)
                # match = cv2.drawKeypoints(equalized, kp2, None, (0, 0, 255), flags=2)
                # plt.imshow(match), plt.show()
                cv2.imshow('Target Match', match)
                cv2.imshow('Target Mask', equalized)
                cv2.waitKey(1)

def has_target_body(testing=True):
    target_template = cv2.imread(resource_path("templates/target.png"), cv2.IMREAD_GRAYSCALE)
    target_width, target_height = target_template.shape[::-1]
    while True:
        screen = get_screen((0/40)*SCREEN_WIDTH, (17/40)*SCREEN_HEIGHT, (14/40)*SCREEN_WIDTH, (40/40)*SCREEN_HEIGHT)
        equalized = equalize(screen)
        match = cv2.matchTemplate(equalized, target_template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.2
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
        pt = (0, 0)
        print(max_val)
        if max_val >= threshold:
            pt = max_loc
        if testing:
            cv2.rectangle(screen, (pt[0], pt[1]), (pt[0]+target_width, pt[1]+target_height), (0, 0, 255), 2)
            loc = np.where(match >= threshold)
            pts = tuple(zip(*loc[::-1]))
            match = cv2.cvtColor(match, cv2.COLOR_GRAY2RGB)
            for p in pts:
                cv2.circle(match, p, 1, (0, 0, 255), 1)
            cv2.circle(match, pt, 5, (0, 255, 0), 3)
            cv2.imshow('Target Found', screen)
            cv2.imshow('Target Mask', equalized)
            cv2.imshow('Target Match', match)
            cv2.waitKey(1)

# Get compass image
def get_compass_image(testing=True):
    if BIG_SCREEN:
        compass_template = cv2.imread(resource_path("templates/compass_large.png"), cv2.IMREAD_GRAYSCALE)
    else:
        compass_template = cv2.imread(resource_path("templates/compass_small.png"), cv2.IMREAD_GRAYSCALE)
    compass_width, compass_height = compass_template.shape[::-1]
    doubt = 10
    screen = get_screen((4/16)*SCREEN_WIDTH, (10/16)*SCREEN_HEIGHT, (8/16)*SCREEN_WIDTH, (16/16)*SCREEN_HEIGHT)
    equalized = equalize(screen)
    match = cv2.matchTemplate(equalized, compass_template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.2
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
    pt = (doubt, doubt)
    if max_val >= threshold:
        pt = max_loc
    compass_image = screen[pt[1]-doubt: pt[1]+compass_height+doubt, pt[0]-doubt: pt[0]+compass_width+doubt].copy()
    if testing:
        cv2.rectangle(screen, (pt[0]-doubt, pt[1]-doubt), (pt[0]+(compass_width+doubt), pt[1]+(compass_height+doubt)), (0, 0, 255), 2)
        loc = np.where(match >= threshold)
        pts = tuple(zip(*loc[::-1]))
        match = cv2.cvtColor(match, cv2.COLOR_GRAY2RGB)
        for p in pts:
            cv2.circle(match, p, 1, (0, 0, 255), 1)
        cv2.circle(match, pt, 5, (0, 255, 0), 3)
        cv2.imshow('Compass Found', screen)
        cv2.imshow('Compass Mask', equalized)
        cv2.imshow('Compass Match', match)
        cv2.waitKey(1)
    return compass_image, compass_width+(2*doubt), compass_height+(2*doubt)

# Get navpoint offset
same_last_count = 0
last_last = {'x': 1, 'y': 100}

def get_navpoint_offset(testing=True, last=None):
    global same_last_count, last_last
    if BIG_SCREEN:
        navpoint_template = cv2.imread(resource_path("templates/navpoint_large.png"), cv2.IMREAD_GRAYSCALE)
    else:
        navpoint_template = cv2.imread(resource_path("templates/navpoint_small.png"), cv2.IMREAD_GRAYSCALE)
    navpoint_width, navpoint_height = navpoint_template.shape[::-1]
    compass_image, compass_width, compass_height = get_compass_image()
    filtered = filter_blue(compass_image)
    # filtered = filter_bright(compass_image)
    match = cv2.matchTemplate(filtered, navpoint_template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.5
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
    pt = (0, 0)
    if max_val >= threshold:
        pt = max_loc
    final_x = (pt[0]+((1/2)*navpoint_width))-((1/2)*compass_width)
    final_y = ((1/2)*compass_height)-(pt[1]+((1/2)*navpoint_height))
    if testing:
        cv2.rectangle(compass_image, pt, (pt[0]+navpoint_width, pt[1]+navpoint_height), (0, 0, 255), 2)
        loc = np.where(match >= threshold)
        pts = tuple(zip(*loc[::-1]))
        match = cv2.cvtColor(match, cv2.COLOR_GRAY2RGB)
        for p in pts:
            cv2.circle(match, p, 1, (0, 0, 255), 1)
        cv2.circle(match, pt, 5, (0, 255, 0), 3)
        cv2.imshow('Navpoint Found', compass_image)
        cv2.imshow('Navpoint Mask', filtered)
        cv2.imshow('Navpoint Match', match)
        cv2.waitKey(1)
    if pt == (0, 0):
        if last:
            if last == last_last:
                same_last_count = same_last_count+1
            else:
                last_last = last
                same_last_count = 0
            if same_last_count > 5:
                same_last_count = 0
                if rand.random() < .9:
                    result = {'x': 1, 'y': 100}
                else:
                    result = {'x': 100, 'y': 1}
            else:
                result = last
        else:
            result = None
    else:
        result = {'x': final_x, 'y': final_y}
    logger.debug('get_navpoint_offset='+str(result))
    return result

# Get destination offset
def get_destination_offset(testing=False):
    if BIG_SCREEN:
        destination_template = cv2.imread(resource_path("templates/destination_large.png"), cv2.IMREAD_GRAYSCALE)
    else:
        destination_template = cv2.imread(resource_path("templates/destination_small.png"), cv2.IMREAD_GRAYSCALE)
    destination_width, destination_height = destination_template.shape[::-1]
    width = (1/3)*SCREEN_WIDTH
    height = (1/3)*SCREEN_HEIGHT
    screen = get_screen((1/3)*SCREEN_WIDTH, (1/3)*SCREEN_HEIGHT, (2/3)*SCREEN_WIDTH, (2/3)*SCREEN_HEIGHT)
    filtered = filter_orange2(screen)
    match = cv2.matchTemplate(filtered, destination_template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.2
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
    pt = (0, 0)
    if max_val >= threshold:
        pt = max_loc
    final_x = (pt[0]+((1/2)*destination_width))-((1/2)*width)
    final_y = ((1/2)*height)-(pt[1]+((1/2)*destination_height))
    pt2 = (int(final_x), int(final_y))
    print(pt2)
    if testing:
        cv2.rectangle(screen, pt, (pt[0]+destination_width, pt[1]+destination_height), (0, 0, 255), 2)
        loc = np.where(match >= threshold)
        pts = tuple(zip(*loc[::-1]))
        match = cv2.cvtColor(match, cv2.COLOR_GRAY2RGB)
        for p in pts:
            cv2.circle(match, p, 1, (0, 0, 255), 1)
        cv2.circle(match, pt, 5, (0, 255, 0), 3)
        cv2.circle(screen, pt, 5, (0, 255, 0), 3)
        cv2.imshow('Destination Found', screen)
        cv2.imshow('Destination Mask', filtered)
        cv2.imshow('Destination Match', match)
        cv2.waitKey(1)
    if pt == (0, 0):
        result = None
    else:
        result = {'x': final_x, 'y': final_y}
    logger.debug('get_destination_offset='+str(result))
    return result

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = abspath(".")

    return join(base_path, relative_path)
