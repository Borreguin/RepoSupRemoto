import argparse, os
import datetime as dt
import hashlib
import json
import traceback
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as colors
from matplotlib.collections import PolyCollection
import pandas as pd
import pickle as pkl
from flask_app.my_lib.PI_connection import pi_connect as p
from flask_app.my_lib.PI_connection.pi_connect import _span, _time_range
from flask_app.my_lib.Sistema_Remoto.sRemoto import pi_svr
yyyy_mm_dd_hh_mm_ss = "%d-%m-%Y %H:%M:%S"
fmt_dd_mm_yyyy_hh_mm = "dd/MMM/yy HH:mm"
fmt_dd_mm_yyyy = "dd/MMM/yyyy"
fmt_dd_mm_yy_ = "dd_MMM_yyyy"
fmt_yyyy="yyyy"
fmt_mm="MMM"


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
    time_range =_time_range(wkt, tdy)
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
                                        span=_span("1d"), time_unit="mi"):

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


def get_state_colors(excel_path:str, sheet_name:str):
    columns = ["ESTADO", "COLOR"]
    try:
        df = pd.read_excel(excel_path, sheet_name)
        df = df[columns]
        color_dict = dict()
        for ste, sus in zip(list(df["ESTADO"]), list(df["COLOR"])):
            color_dict[ste] = sus
        return True, color_dict
    except Exception as e:
        print(e)
        return False, dict()

def generate_bar_estatus(series: pd.Series, fig_size, path_to_save: str = None, color_map: dict = None):
    from matplotlib.patches import Patch
    plt.rcParams.update({'font.size': 24})
    states = list(set(series))
    # states.sort()
    ti_i = series.index[0]  # tiempo inicial del estado
    st_i = series[0]        # estado inicial
    data = list()
    for t, state in zip(series.index[1:], series):
        if st_i != state:
            data.append((ti_i, t, st_i))   # tiempo inicial, tiempo final, estado
            st_i = state
            ti_i = t
    data.append((ti_i, series.index[-1], st_i))
    cats = dict()
    color_mapping = dict()
    legend_elements = list()
    for ix, st in enumerate(states):
        cats[st] = 0
        if color_map is not None and st in color_map.keys():
            color_mapping[st] = color_map[st]
        else:
            color_mapping[st] = f"C{ix}"

        legend_elements.append(Patch(facecolor=color_mapping[st], label=st))

    verts = []
    colors = []
    for d in data:
        v = [(mdates.date2num(d[0]), cats[d[2]] - .05),
             (mdates.date2num(d[0]), cats[d[2]] + .05),
             (mdates.date2num(d[1]), cats[d[2]] + .05),
             (mdates.date2num(d[1]), cats[d[2]] - .05),
             (mdates.date2num(d[0]), cats[d[2]] - .05)]
        verts.append(v)
        colors.append(color_mapping[d[2]])

    bars = PolyCollection(verts, facecolors=colors)

    fig, ax = plt.subplots(figsize=fig_size)
    ax.add_collection(bars)

    days = mdates.DayLocator()
    days_fmt = mdates.DateFormatter('%d-%b')
    hours = mdates.HourLocator()
    hours_fmt = mdates.DateFormatter('%H')

    #ax.xaxis.set_major_locator(days)
    #ax.xaxis.set_minor_locator(hours)

    #ax.xaxis.set_major_formatter(days_fmt)
    #ax.xaxis.set_minor_formatter(hours_fmt)

    locator = mdates.AutoDateLocator(minticks=1)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(days_fmt)

    locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
    ax.xaxis.set_minor_locator(locator)
    ax.xaxis.set_minor_formatter(hours_fmt)


    ax.set_yticks([0])
    ax.set_yticklabels([""])

    lgd = ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1, 0.5))
    text = ax.text(0, 0, "", transform=ax.transAxes)
    ax.autoscale()
    if path_to_save is not None:
        try:
            fig.savefig(path_to_save, bbox_extra_artists=(lgd, text), bbox_inches='tight',
                        format="png", transparent=True, dpi=30)
            return True, fig
        except Exception as e:
            print(e)
            return False, fig
    else:
        return True, fig
