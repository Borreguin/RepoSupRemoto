"""
Este script contiene código que es útil para diferentes scripts en este proyecto

"""

import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.collections import PolyCollection
from my_lib import pi_connect as p
yyyy_mm_dd_hh_mm_ss = "%d-%m-%Y %H:%M:%S"
fmt_dd_mm_yyyy_hh_mm = "dd/MMM/yy HH:mm"
fmt_dd_mm_yyyy = "dd/MMM/yyyy"
fmt_dd_mm_yy_ = "dd_mmm_yyyy"
pi_svr = p.PIserver()

lb_tag = "Tag"
lb_name = "Nombre"
lb_expression = "Expresion"
lb_tiempo = "Tiempo"
lb_per_dispo = "Porcentaje_Disp"
lb_state = "Estado"
lb_date = "Fecha"
lb_period = "Periodo"
lb_activa = "Activa"
lb_protocol = "Protocolo"
lb_prioridad = "Prioridad"
lb_filter = "Filter"


def define_time_range_for_yesterday():
    tdy = dt.datetime.now().strftime(yyyy_mm_dd_hh_mm_ss)
    ytd = dt.datetime.now() - dt.timedelta(days=1)
    time_range = pi_svr.time_range(ytd, tdy)
    return time_range


def define_time_range_for_last_week():
    tdy = dt.datetime.now().strftime(yyyy_mm_dd_hh_mm_ss)
    wkt = dt.datetime.now() - dt.timedelta(days=7)
    time_range = pi_svr.time_range(wkt, tdy)
    return time_range


def process_excel_file(excel_file, sheet_name, time_range_to_run,
                       span=pi_svr.span("1d"), time_unit="di"):

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
            df.loc[[ix], lb_per_dispo] = round(value[tag_name][0]*100, 1)
            df.loc[[ix], lb_state] = str(pt.snapshot().Value)
            df.loc[[ix], lb_date] = str(pt.snapshot().Timestamp)
            df.loc[[ix], lb_period] = str(time_range_to_run).replace("00:00:00", "")

    df.sort_values(by=[lb_prioridad,  lb_per_dispo], inplace=True)
    mask = (df[lb_per_dispo] < 99.5)
    df_filter = df[mask].copy()
    filter_exp = df[lb_filter].iloc[0]
    df_indisp = df[df[lb_state] == f"{filter_exp}"].copy()
    df_filter.sort_values(by=[lb_prioridad,  lb_per_dispo], inplace=True)
    return df, df_filter, df_indisp


def get_history_from(excel_file, sheet_name, time_range, span=pi_svr.span("10 m")):
    # leyendo archivo Excel y filtrando aquellos que están activos:
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    df = df[df["Activa"] == "x"]
    df_hist = pd.DataFrame()
    tgs = list()
    for ix in df.index:
        # nombre de la tag
        tag_name = df[lb_tag].loc[ix]

        # pt es un PointTag que permitirá obtener datos del servidor
        # si pt.pt es None, entonces dicha tag no existe
        pt = p.PI_point(pi_svr, tag_name)
        if pt.pt is not None:
            # adjuntar el dataframe con la historia:
            tgs.append(tag_name)
            df_tag = pt.interpolated(time_range, span, numeric=False)
            df_hist = pd.concat([df_hist, df_tag], axis=1, sort=True)

    # filtrar solo tags existentes:
    df_hist = df_hist[tgs]

    return df, df_hist


def replace_block(from_label: str, to_label: str, html_str: str, to_replace: str):
    str_result = html_str
    from_index = html_str.find(from_label)
    to_index = html_str.find(to_label)
    if from_index > 0 and to_index > 0:
        str_result = html_str[:from_index] + to_replace + html_str[to_index:]
    return str_result


def save_html(html_str, path_html_to_save):
    # Guardar el archivo html en la carpeta reportes:
    try:
        Html_file = open(path_html_to_save, "w", encoding='utf-8')
        Html_file.write(html_str)
        Html_file.close()
    except Exception as e:
        print(e)


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


def get_state_translation(excel_path:str, sheet_name:str):
    columns = ["ESTADO", "SUSTITUCION"]
    try:
        df = pd.read_excel(excel_path, sheet_name)
        df = df[columns]
        state_dict = dict()
        for ste, clr in zip(list(df["ESTADO"]), list(df["SUSTITUCION"])):
            state_dict[ste] = clr
        return True, state_dict
    except Exception as e:
        print(e)
        return False, dict()


def get_translation(series: pd.Series, excel_path:str, sheet_name: str):
    success, dict_t = get_state_translation(excel_path, sheet_name)
    if not success:
        return series
    states = list(set(series))
    for st in states:
        if not st in dict_t.keys():
            continue
        replace = dict_t[st]
        series.replace(to_replace=st, value=replace, inplace=True)
    return series


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
