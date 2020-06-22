import logging
from dataclasses import dataclass, field
from os import environ, listdir
from os.path import join, isfile, getmtime
from time import sleep
from typing import List
from xml.etree.ElementTree import parse

import directinput_new
from EDKeyCodes import EDKeyCodes
from logger import setup_logger

@dataclass
class ModKey:
    EDKeyCode: str
    ScanCode: int

@dataclass
class InputKey:
    EDKeyCode: str = field(default="")
    ScanCode: int = field(default=0)
    mod: List[ModKey] = field(default_factory=list)


class Keyboard:

    required_keys = [
        'YawLeftButton',
        'YawRightButton',
        'RollLeftButton',
        'RollRightButton',
        'PitchUpButton',
        'PitchDownButton',
        'SetSpeedZero',
        'SetSpeed100',
        'HyperSuperCombination',
        'UIFocus',
        'UI_Up',
        'UI_Down',
        'UI_Left',
        'UI_Right',
        'UI_Select',
        'UI_Back',
        'CycleNextPanel',
        'HeadLookReset',
        'PrimaryFire',
        'SecondaryFire',
        'MouseReset'
    ]

    KEY_MOD_DELAY = 0.010
    KEY_DEFAULT_DELAY = 0.200
    KEY_REPEAT_DELAY = 0.100

    logger = setup_logger("keyboard")

    def __init__(self, cv_testing=False):
        self.cv_testing = cv_testing
        self.keys = self.get_bindings()
        for key in self.required_keys:
            try:
                self.logger.info('get_bindings: '+str(key)+' = '+str(self.keys[key]))
            except Exception as e:
                self.logger.warning(str("get_bindings: "+key+" = does not have a valid keyboard keybind.").upper())

    # Get latest keybinds file
    def get_latest_keybinds(self, path_bindings=None):
        if not path_bindings:
            path_bindings = environ['LOCALAPPDATA']+"\Frontier Developments\Elite Dangerous\Options\Bindings"
        list_of_bindings = [join(path_bindings, f) for f in listdir(path_bindings) if (isfile(join(path_bindings, f)) and join(path_bindings, f).endswith("binds"))]
        if not list_of_bindings:
            return None
        latest_bindings = max(list_of_bindings, key=getmtime)
        return latest_bindings

    def get_bindings(self, keysToObtain=None):
        """Returns a dict struct with the direct input equivalent of the necessary elite keybindings"""
        if keysToObtain is None:
            keysToObtain = self.required_keys
        inputKeys = {}

        latest_bindings = self.get_latest_keybinds()
        bindings_tree = parse(latest_bindings)
        bindings_root = bindings_tree.getroot()

        for item in bindings_root:
            if item.tag in keysToObtain:
                EDName = item.tag
                binding = InputKey()
                '''{
                    'EDKeyCode': None,
                    'VKCode': None,
                    'mod': []
                }'''

                # Check secondary (and prefer secondary)
                if item[1].attrib['Device'].strip() == "Keyboard":
                    binding.EDKeyCode = item[1].attrib['Key']
                    binding.ScanCode = EDKeyCodes[item[1].attrib['Key']]
                    for ii in range(len(item[1])):
                        binding.mod.append(ModKey(item[1][ii].attrib['Key'], EDKeyCodes[item[1][ii].attrib['Key']]))

                # Check primary
                elif item[0].attrib['Device'].strip() == "Keyboard":
                    binding.EDKeyCode = item[0].attrib['Key']
                    binding.ScanCode = EDKeyCodes[item[0].attrib['Key']]
                    for ii in range(len(item[0])):
                        binding.mod.append(ModKey(item[0][ii].attrib['Key'], EDKeyCodes[item[0][ii].attrib['Key']]))

                inputKeys[EDName] = binding

        if inputKeys == {}:
            return None
        else:
            return inputKeys

    # Direct input function
    # Send input
    def press(self, key: InputKey):
        if not self.cv_testing:
            if key is None:
                self.logger.warning('SEND=NONE !!!!!!!!')
                return

            self.logger.debug('press=key:'+str(key))
            for mod in key.mod:
                directinput_new.press_key(mod.ScanCode)
                sleep(self.KEY_MOD_DELAY)
            directinput_new.press_key(key.ScanCode)

    def release(self, key: InputKey):
        if not self.cv_testing:
            if key is None:
                self.logger.warning('SEND=NONE !!!!!!!!')
                return

            self.logger.debug('release=key:'+str(key))
            directinput_new.release_key(key.ScanCode)
            for mod in key.mod:
                directinput_new.release_key(mod.ScanCode)

    def tap(self, key: InputKey):
        if not self.cv_testing:
            if key is None:
                self.logger.warning('SEND=NONE !!!!!!!!')
                return

            self.logger.debug('tap=key:'+str(key))
            self.press(key)
            sleep(self.KEY_DEFAULT_DELAY)
            self.release(key)

    def hold(self, key: InputKey, hold: float):
        if not self.cv_testing:
            if key is None:
                self.logger.warning('SEND=NONE !!!!!!!!')
                return

            self.logger.debug('tap=key:'+str(key)+',hold:'+str(hold))
            self.press(key)
            sleep(hold if hold > self.KEY_DEFAULT_DELAY else self.KEY_DEFAULT_DELAY)
            self.release(key)

    def clear_input(self, to_clear=None):
        if not self.cv_testing:
            logging.info('---- CLEAR INPUT '+183*'-')
            self.tap(to_clear['SetSpeedZero'])
            self.tap(to_clear['MouseReset'])

            if to_clear is None:
                to_clear = self.keys

            for key_to_clear in to_clear.keys():
                if key_to_clear in self.keys:
                    self.release(to_clear[key_to_clear])
            logging.debug('clear_input')


if __name__ == "__main__":
    for i in list(range(3))[::-1]:
        print(i+1)
        sleep(1)
    print('press')

    keyboardTest = Keyboard()
    keyboardTest.tap(keyboardTest.keys['UI_Up'])
