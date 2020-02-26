import traceback

import sCentral
import sRemoto
from my_lib import util as u

if __name__ == "__main__":

    # Definiendo fecha de la supervisión
    yesterday = u.define_time_range_for_yesterday()

    # Ejecutando Reporte de Sistema Remoto
    try:
        sRemoto.run_process_for(yesterday)
    except Exception as e:
        print(traceback.format_exc())

    # Ejecutando Reporte de Sistema Central
    try:
        sCentral.run_process_for(yesterday)
    except Exception as e:
        print(traceback.format_exc())