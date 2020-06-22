import threading


run = False

def sleep(i):
    print(i)

def mainLoop():
    print("ready")
    while True:
        if run:
            print("running")
            sleep(1)

def startAutopilot():
    global run
    run = True

def stopAutopilot():
    global run
    run = False

def undock():
    wait = 120
    for i in range(wait):
        sleep(1)
        if not run:
            break

def dock():
    tries = 3
    for i in range(tries):
        sleep(1)
        if not run:
            break

    wait = 120
    for i in range(wait):
        sleep(1)
        if not run:
            break


class MainThread(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        while True:
            mainLoop()
