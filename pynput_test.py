import math

from pyautogui import size
from pynput import keyboard
from time import sleep
import threading

from pynput.keyboard import Key

import autopilot_utils
from Keyboard import Keyboard
from logger import setup_logger

running = False
logger = setup_logger("autopilot")

# Undock
def undock(keyboardT):
    logger.debug('undock')
    if autopilot_utils.ship()['status'] != "in_station":
        logger.error('undock=err1')
        raise Exception('undock error 1')
    send(keys['UI_Back'], repeat=10)
    send(keys['HeadLookReset'])
    send(keys['UI_Down'], hold=3)
    send(keys['UI_Select'])
    sleep(1)
    if not (autopilot_utils.ship()['status'] == "starting_undock" or autopilot_utils.ship()['status'] == "in_undock"):
        logger.error('undock=err2')
        raise Exception("undock error 2")
    send(keys['HeadLookReset'])
    send(keys['SetSpeedZero'], repeat=2)
    wait = 120
    for i in range(wait):
        sleep(1)
        if i > wait-1:
            logger.error('undock=err3')
            raise Exception('undock error 3')
        if autopilot_utils.ship()['status'] == "in_space":
            break
    logger.debug('undock=complete')
    return True

# Dock
def dock(keyboardT):
    logger.debug('dock')
    if autopilot_utils.ship()['status'] != "in_space":
        logger.error('dock=err1')
        raise Exception('dock error 1')
    tries = 3
    for i in range(tries):
        send(keys['UI_Back'], repeat=10)
        send(keys['HeadLookReset'])
        send(keys['UIFocus'], state=1)
        send(keys['UI_Left'])
        send(keys['UIFocus'], state=0)
        send(keys['CycleNextPanel'], repeat=2)
        send(keys['UI_Up'], hold=3)
        send(keys['UI_Right'])
        send(keys['UI_Select'])
        sleep(1)
        if autopilot_utils.ship()['status'] == "starting_dock" or autopilot_utils.ship()['status'] == "in_dock":
            break
        if i > tries-1:
            logger.error('dock=err2')
            raise Exception("dock error 2")
    send(keys['UI_Back'])
    send(keys['HeadLookReset'])
    send(keys['SetSpeedZero'], repeat=2)
    wait = 120
    for i in range(wait):
        sleep(1)
        if i > wait-1:
            logger.error('dock=err3')
            raise Exception('dock error 3')
        if autopilot_utils.ship()['status'] == "in_station":
            break
    send(keys['UI_Up'], hold=3)
    send(keys['UI_Down'])
    send(keys['UI_Select'])
    logger.debug('dock=complete')
    return True

# Align
def x_angle(point=None):
    if not point or point['x'] == 0:
        return None
    result = math.degrees(math.atan(point['y']/point['x']))
    if point['x'] > 0:
        return +90-result
    else:
        return -90-result

def align(keyboardT):
    logger.info('Starting Alignment')
    if not (autopilot_utils.ship()['status'] == 'in_supercruise' or autopilot_utils.ship()['status'] == 'in_space'):
        logger.error('align=err1')
        raise Exception('align error 1')

    logger.debug('align=speed 100')
    send(keys['SetSpeed100'])

    logger.info('Alignment Step: Avoid sun')
    while sun_percent() > 5:
        send(keys['PitchUpButton'], state=1)
    send(keys['PitchUpButton'], state=0)

    logger.info('Alignment Step: Find navpoint')
    off = get_navpoint_offset()
    while not off:
        send(keys['PitchUpButton'], state=1)
        off = get_navpoint_offset()
    send(keys['PitchUpButton'], state=0)

    logger.info('Alignment Step: Crude align')
    close = 3
    close_a = 18
    hold_pitch = 0.350
    hold_roll = 0.170
    ang = x_angle(off)
    while (off['x'] > close and ang > close_a) or (off['x'] < -close and ang < -close_a) or (off['y'] > close) or (off['y'] < -close):

        while (off['x'] > close and ang > close_a) or (off['x'] < -close and ang < -close_a):

            if off['x'] > close and ang > close:
                send(keys['RollRightButton'], hold=hold_roll)
            if off['x'] < -close and ang < -close:
                send(keys['RollLeftButton'], hold=hold_roll)

            if autopilot_utils.ship()['status'] == 'starting_hyperspace':
                return
            off = get_navpoint_offset(last=off)
            ang = x_angle(off)

        while (off['y'] > close) or (off['y'] < -close):

            if off['y'] > close:
                send(keys['PitchUpButton'], hold=hold_pitch)
            if off['y'] < -close:
                send(keys['PitchDownButton'], hold=hold_pitch)

            if autopilot_utils.ship()['status'] == 'starting_hyperspace':
                return
            off = get_navpoint_offset(last=off)

        off = get_navpoint_offset(last=off)
        ang = x_angle(off)

    logger.info('Alignment Step: Fine align')
    sleep(0.5)
    close = 50
    hold_pitch = 0.200
    hold_yaw = 0.400
    for i in range(5):
        new = get_destination_offset()
        if new:
            off = new
            break
        sleep(0.25)
    if not off:
        return
    while (off['x'] > close) or (off['x'] < -close) or (off['y'] > close) or (off['y'] < -close):

        if off['x'] > close:
            send(keys['YawRightButton'], hold=hold_yaw)
        if off['x'] < -close:
            send(keys['YawLeftButton'], hold=hold_yaw)
        if off['y'] > close:
            send(keys['PitchUpButton'], hold=hold_pitch)
        if off['y'] < -close:
            send(keys['PitchDownButton'], hold=hold_pitch)

        if autopilot_utils.ship()['status'] == 'starting_hyperspace':
            return

        for i in range(5):
            new = get_destination_offset()
            if new:
                off = new
                break
            sleep(0.25)
        if not off:
            return

    logger.info('Alignment Complete')

# Jump
def jump(keyboardT):
    logger.info('Starting Jump')
    tries = 3
    for i in range(tries):
        logger.debug('jump=try:'+str(i))
        if not (autopilot_utils.ship()['status'] == 'in_supercruise' or autopilot_utils.ship()['status'] == 'in_space'):
            logger.error('jump=err1')
            raise Exception('not ready to jump')
        sleep(0.5)
        logger.info('Charging FSD')
        send(keys['HyperSuperCombination'], hold=1)
        sleep(16)
        if autopilot_utils.ship()['status'] != 'starting_hyperspace':
            logger.info('Trajectory Misaligned. Jump Failed. Retrying Alignment')
            send(keys['HyperSuperCombination'], hold=1)
            sleep(2)
            align()
        else:
            logger.info('Jump in Progress')
            while autopilot_utils.ship()['status'] != 'in_supercruise':
                sleep(1)
            logger.debug('jump=speed 0')
            send(keys['SetSpeedZero'])
            logger.info('Jump Complete')
            return True
    logger.error('jump=err2')
    raise Exception("jump failure")

# Refuel
def refuel(keyboardT, refuel_threshold=40):
    logger.debug('refuel')
    scoopable_stars = ['F', 'O', 'G', 'K', 'B', 'A', 'M']
    if autopilot_utils.ship()['status'] != 'in_supercruise':
        logger.error('refuel=err1')
        return False

    if autopilot_utils.ship()['fuel_percent'] < refuel_threshold and autopilot_utils.ship()['star_class'] in scoopable_stars:
        logger.info('Starting Refuel')
        send(keys['SetSpeed100'])
        sleep(4)
        logger.info('Refuel in Progress')
        send(keys['SetSpeedZero'], repeat=3)
        while not autopilot_utils.ship()['fuel_percent'] == 100:
            sleep(1)
        logger.info('Refuel Complete')
        return True
    elif autopilot_utils.ship()['fuel_percent'] >= refuel_threshold:
        logger.info('Refuel not Needed')
        return False
    elif autopilot_utils.ship()['star_class'] not in scoopable_stars:
        logger.info('Refuel Needed, Unsuitable Star')
        return False
    else:
        return False

# Discovery scanner
scanner = 1

def set_scanner(state):
    global scanner
    scanner = state
    logger.debug('set_scanner='+str(scanner))

def get_scanner():
    from dev_tray import STATE
    return STATE

# Position
def position(keyboardT, refueled_multiplier=1):
    logger.debug('position')
    scan = 2  # get_scanner()
    if scan == 1:
        logger.info('Scanning')
        send(keys['PrimaryFire'], state=1)
    elif scan == 2:
        logger.info('Scanning')
        send(keys['SecondaryFire'], state=1)
    else:
        logger.info('Scanning Disabled')
    send(keys['PitchUpButton'], state=1)
    sleep(5)
    send(keys['PitchUpButton'], state=0)
    send(keys['SetSpeed100'])
    send(keys['PitchUpButton'], state=1)
    while sun_percent() > 3:
        sleep(1)
    sleep(5)
    send(keys['PitchUpButton'], state=0)
    sleep(5*refueled_multiplier)
    if scan == 1:
        logger.info('Scanning Complete')
        send(keys['PrimaryFire'], state=0)
    elif scan == 2:
        logger.info('Scanning Complete')
        send(keys['SecondaryFire'], state=0)
    logger.debug('position=complete')
    return True

def autopilot():
    global running
    
    while not running:
        sleep(1)

    logger.info('---- AUTOPILOT START '+179*'-')

    keyboardT = Keyboard()

    while running:
        undock(keyboardT)
        '''
        logger.debug('get_latest_log='+str(get_latest_log(PATH_LOG_FILES)))
        logger.debug('ship='+str(autopilot_utils.ship()))
        while autopilot_utils.ship()['target']:
            if autopilot_utils.ship()['status'] == 'in_space' or autopilot_utils.ship()['status'] == 'in_supercruise':
                # logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT ALIGN '+179*'-'+'\n'+200*'-')
                logger.info('---- AUTOPILOT ALIGN '+179*'-')
                align()
                # logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT JUMP '+180*'-'+'\n'+200*'-')
                logger.info('---- AUTOPILOT JUMP '+180*'-')
                jump()
                # logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT REFUEL '+178*'-'+'\n'+200*'-')
                logger.info('---- AUTOPILOT REFUEL '+178*'-')
                refueled = refuel()
                # logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT POSIT '+179*'-'+'\n'+200*'-')
                logger.info('---- AUTOPILOT SCAN '+180*'-')
                if refueled:
                    position(refueled_multiplier=4)
                else:
                    position(refueled_multiplier=1)
        send(keys['SetSpeedZero'])
        # logger.info('\n'+200*'-'+'\n'+'---- AUTOPILOT END '+181*'-'+'\n'+200*'-')
        logger.info('---- AUTOPILOT END '+181*'-')
        '''


def autopilotThread():
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
    while True:
        autopilot()


threading.Thread(target=autopilotThread, name='EDAutopilot').start()

def on_press(key):
    global running
    if key == Key.page_up:
        print("page up pressed")
        print("starting")
        running = True
    elif key == Key.page_down:
        print("page down pressed")
        print("stopping")
        running = False


# Collect events until released
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
