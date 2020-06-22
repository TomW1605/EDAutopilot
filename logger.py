import logging
import colorlog

def setup_logger(name=None):
    formatter = colorlog.ColoredFormatter('%(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s',  # %(filename)s:%(lineno)s
                                          log_colors={
                                              'DEBUG': 'fg_bold_cyan',
                                              'INFO': 'fg_bold_green',
                                              'WARNING': 'bg_bold_yellow,fg_bold_blue',
                                              'ERROR': 'bg_bold_red,fg_bold_white',
                                              'CRITICAL': 'bg_bold_red,fg_bold_yellow',
                                          }, secondary_log_colors={})

    colorlog.basicConfig(filename='autopilot.log', level=logging.DEBUG)

    logger = colorlog.getLogger(name=name)
    logger.setLevel(logging.DEBUG)

    handler = colorlog.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    #logger.debug('This is a DEBUG message. These information is usually used for troubleshooting')
    #logger.info('This is an INFO message. These information is usually used for conveying information')
    #logger.warning('some warning message. These information is usually used for warning')
    #logger.error('some error message. These information is usually used for errors and should not happen')
    #logger.critical('some critical message. These information is usually used for critical error, and will usually result in an exception.')
    # logging.info('\n'+200*'-'+'\n'+'---- AUTOPILOT DATA '+180*'-'+'\n'+200*'-')
    return logger
