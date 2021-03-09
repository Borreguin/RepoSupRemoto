# Version Final: 5 Agosto 2020

import logging
import os
import datetime as dt
import traceback
from logging.handlers import RotatingFileHandler
import sCentral
import sRemoto
import sAuxiliares
from my_lib import util as u
logger = None

script_path = os.path.dirname(os.path.abspath(__file__))


def init_logger():
    global logger
    # maxBytes to small number, in order to demonstrate the generation of multiple log files (backupCount).
    handler = RotatingFileHandler(os.path.join(script_path, 'logs', 'mensajes.log'), maxBytes=500000, backupCount=3)
    # getLogger(__name__):   decorators loggers to file + werkzeug loggers to stdout
    # getLogger('werkzeug'): decorators loggers to file + nothing to stdout
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


if __name__ == "__main__":

    init_logger()
    # Definiendo fecha de la supervisión
    yesterday = u.define_time_range_for_yesterday()
    msg = "Empezando el proceso de reporte"
    logger.info(msg)
    # Ejecutando Reporte de Sistema Remoto
    try:
        success, msg = sRemoto.run_process_for(yesterday)
        logger.info(msg)
    except Exception as e:
        msg = f"[{dt.datetime.now()}] Problema al correr Reporte de Sistema Remoto \n " + str(e) + "\n" \
              + traceback.format_exc()
        print(msg)
        logger.error(msg)

    # Ejecutando Reporte de Sistema Central
    try:
        success, msg = sCentral.run_process_for(yesterday)
        logger.info(msg)
    except Exception as e:
        msg = f"[{dt.datetime.now()}] Problema al correr Reporte de Sistema Central \n " + str(e) + "\n" \
              + traceback.format_exc()
        print(msg)
        logger.error(msg)

    # Ejecutando Reporte de Auxiliares
    try:
        success, msg = sAuxiliares.run_process_now()
        logger.info(msg)
    except Exception as e:
        msg = f"[{dt.datetime.now()}] Problema al correr Reporte de Sistemas Auxiliares \n " + str(e) + "\n" \
              + traceback.format_exc()
        print(msg)
        logger.error(msg)
