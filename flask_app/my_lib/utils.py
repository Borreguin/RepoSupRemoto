import argparse, os
import datetime as dt
import hashlib
import json
import traceback

import pandas as pd
import pickle as pkl
from flask_app.my_lib.Sistema_Remoto.sRemoto import pi_svr
yyyy_mm_dd_hh_mm_ss = "%d-%m-%Y %H:%M:%S"
fmt_dd_mm_yyyy_hh_mm = "dd/MMM/yy HH:mm"
fmt_dd_mm_yyyy = "dd/MMM/yyyy"
fmt_dd_mm_yy_ = "dd_MMM_yyyy"


lb_tag = "Tag"
lb_name = "Nombre"
lb_expression = "Expresion"
lb_tiempo = "Tiempo Disponibilidad en minutos"
lb_per_dispo = "Porcentaje_Disp"
lb_state = "Estado"
lb_date = "Fecha"
lb_period = "Periodo"
lb_activa = "Activa"
lb_protocol = "Protocolo"
lb_prioridad = "Prioridad"
lb_filter = "Filter"


script_path = os.path.dirname(os.path.abspath(__file__))
def valid_date(s):
    try:
        if isinstance(s,dt.datetime):
            return s
        return dt.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "El parámetro: '{0}' no es una fecha válida, (formato YYYY-MM-DD).".format(s)
        raise argparse.ArgumentTypeError(msg)

def valid_date_h_m_s(s):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        msg = "El parámetro: '{0}' no es una fecha válida, (formato YYYY-MM-DD).".format(s)
        raise argparse.ArgumentTypeError(msg)

def get_dates_by_default():
    today = dt.datetime.now()
    today = dt.datetime(year=today.year, month=today.month, day=today.day)
    end_date = today
    if today.day > 1:
        ini_date = today - dt.timedelta(days=today.day-1)
    else:
        yesterday = today - dt.timedelta(days=1)
        ini_date = yesterday - dt.timedelta(days=yesterday.day - 1)
    return ini_date, end_date


def get_last_day():
    today = dt.datetime.now()
    today = dt.datetime(year=today.year, month=today.month, day=today.day)
    yesterday = today - dt.timedelta(days=1)
    return yesterday, today

def define_time_range_for_date(date:dt.datetime):
    ytd = date - dt.timedelta(days=1)
    time_range = pi_svr.time_range(ytd, date)
    return time_range
def define_time_range_for_yesterday():
    tdy = dt.datetime.now().strftime(yyyy_mm_dd_hh_mm_ss)
    ytd = dt.datetime.now() - dt.timedelta(days=1)
    time_range = pi_svr.time_range(ytd, tdy)
    return time_range

def define_time_range_for_this_week(tdy=None):
    if tdy is None:
        tdy = dt.datetime.now().strftime(yyyy_mm_dd_hh_mm_ss)
    wkt = dt.datetime.now() - dt.timedelta(days=7)
    time_range = pi_svr.time_range(wkt, tdy)
    return time_range

def check_date(s):
    success, date = check_date_yyyy_mm_dd(s)
    if success:
        return success, date
    success, date = check_date_yyyy_mm_dd_hh_mm_ss(s)
    if success:
        return success, date


def check_date_yyyy_mm_dd(s):
    try:
        return True, dt.datetime.strptime(s, "%Y-%m-%d")
    except Exception as e:
        return False, str(e)


def check_date_yyyy_mm_dd_hh_mm_ss(s):
    try:
        return True, dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return False, str(e)

def get_block(from_label: str, to_label: str, html_str: str):
    str_result = str()
    from_index = html_str.find(from_label)
    to_index = html_str.find(to_label)
    if from_index > 0 and to_index > 0:
        str_result = html_str[from_index + len(from_label): to_index]
    return str_result


def replace_block(from_label: str, to_label: str, html_str: str, to_replace: str):
    str_result = html_str
    from_index = html_str.find(from_label)
    to_index = html_str.find(to_label)
    if from_index > 0 and to_index > 0:
        str_result = html_str[:from_index] + to_replace + html_str[to_index:]
        str_result = str_result.replace(to_label, "")
    return str_result


def save_html(html_str, path_html_to_save):
    # Guardar el archivo html en la carpeta reportes:
    try:
        Html_file = open(path_html_to_save, "w", encoding='utf-8')
        Html_file.write(html_str)
        Html_file.close()
    except Exception as e:
        print(e)

def process_avalability_from_excel_file(excel_file, sheet_name, time_range_to_run,
                                        span=pi_svr.span("1d"), time_unit="mi"):

    # leyendo archivo Excel y filtrando aquellos que están activos:
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    df = df[df["Activa"] == "x"]
    df[lb_tiempo] = [0 for ix in df.index]  # iniciando la columna lb_tiempo con 0
    df[lb_state] = ["" for ix in df.index]  # iniciando la columna lb_state con vacío

    for ix in df.index:
        # nombre de la tag
        tag_name = df[lb_tag].loc[ix]
        # expresión a tomar en cuenta:
        expression = df[lb_expression].loc[ix]
        # expression = f"'{tag_name}' = \"{exp}\""

        # pt es un PointTag que permitirá obtener datos del servidor
        # si pt.pt es None, entonces dicha tag no existe
        pt = p.PI_point(pi_svr, tag_name)
        if pt.pt is not None:
            value = pt.time_filter(time_range_to_run, expression, span, time_unit)
            df.loc[[ix], lb_tiempo] = value[tag_name][0]
            df.loc[[ix], lb_state] = str(pt.snapshot().Value)
            df.loc[[ix], lb_date] = str(pt.snapshot().Timestamp)
            df.loc[[ix], lb_period] = str(time_range_to_run).replace("00:00:00", "")
    df.sort_values(by=[lb_prioridad, lb_tiempo], inplace=True)
    return df