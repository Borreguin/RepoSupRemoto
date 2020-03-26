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
    handler = RotatingFileHandler(os.path.join(script_path, 'logs', 'weather.log'), maxBytes=500000, backupCount=3)
    # getLogger(__name__):   decorators loggers to file + werkzeug loggers to stdout
    # getLogger('werkzeug'): decorators loggers to file + nothing to stdout
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


if __name__ == "__main__":

    # Definiendo fecha de la supervisión
    yesterday = u.define_time_range_for_yesterday()

    # Ejecutando Reporte de Sistema Remoto
    try:
        sRemoto.run_process_for(yesterday)
    except Exception as e:
        msg = f"[{dt.datetime.now()}] Problema al correr Reporte de Sistema Remoto \n " + str(e) + "\n" \
              + traceback.format_exc()
        print(msg)
        logger.error(msg)

    # Ejecutando Reporte de Sistema Central
    try:
        sCentral.run_process_for(yesterday)
    except Exception as e:
        msg = f"[{dt.datetime.now()}] Problema al correr Reporte de Sistema Central \n " + str(e) + "\n" \
              + traceback.format_exc()
        print(msg)
        logger.error(msg)

    # Ejecutando Reporte de Auxiliares
    try:
        sAuxiliares.run_process_now()
    except Exception as e:
        print(traceback.format_exc())