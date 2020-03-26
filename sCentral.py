"""
Este script ejecuta la supervisión de sistema remoto, basada en las configuraciones del archivo:
    "Config.xlsx (excel_file)", hoja:
con los campos:
    Activa	Prioridad	EMPRESA	Nombre	Tag	Expresion	Tiempo	Porcentaje_Disp	Protocolo

El script envía un mail a la lista: recipients
con el usuario: from_email = "sistemaremoto@cenace.org.ec"
anexando las imágenes definidas en: image_list

"""

import datetime as dt
import os
import re
import traceback
import pandas as pd  # Librería de análisis de datos
import installer as ins
import sRemoto
# Librería de conexión con Pi-Server, # librería para envíar mail de supervisión
from my_lib import pi_connect as p, send_mail as send, util as u

""" Variables globales """
pi_svr = p.PIserver()
excel_file = sRemoto.excel_file
# hojas a utilizar del archivo excel:
IccpSheet = "ICCP"
AGCSheet = "AGC"
SCentralSheet = "sCentral"
TranslateSheet = "TRADUCCION"
ColorSheet = "COLORES"
even_color = "#f2f2f2"

""" Configuraciones del script """
reporte_path = sRemoto.reporte_path
script_path = os.path.dirname(os.path.abspath(__file__))
html_central_file = os.path.join(script_path, "templates", "supervision_sist_central.html")
images_path = os.path.join(reporte_path, "images")
fmt_dd_mm_yy_ = u.fmt_dd_mm_yy_
time_range = None
minutos_dia = 60 * 24
criticidad = ["", "ALTO", "MEDIO", "BAJO", "NO CRÍTICO"]
prioridad_styles = ["", 'style="vertical-align: top; text-align: center; background-color: rgb(255, 0, 0); font-weight: bold"; font-size: 10pt',
                    'style="vertical-align: top; text-align: center; background-color: rgb(255, 203, 0); font-weight: bold"; font-size: 10pt',
                    'style="vertical-align: top; text-align: center; background-color: rgb(255, 255, 102); font-weight: bold"; font-size: 10pt',
                    'style="vertical-align: top; text-align: center; background-color: rgb(255, 255, 255); font-weight: bold"; font-size: 10pt'  ]


def process_html_iccp(df, df_indisp, df_hist, html_str):
    global reporte_path
    # realizando las sustituciones necesarias para llenar el formulario HTML:
    html_str = html_str.replace("(#no_ICCP)", str(len(df.index)))
    html_str = html_str.replace("(#no_ICCP_indisponible)", str(len(df_indisp)))
    df[sRemoto.lb_per_dispo] = [round(tiempo_disp/minutos_dia*100,1) for tiempo_disp in df[u.lb_tiempo]]
    mask = (df[sRemoto.lb_per_dispo] < 99.5) | (df[sRemoto.lb_state] == df[u.lb_filter])
    # mask = (df[sRemoto.lb_state] == str(f_text))
    df_to_process = df[mask]
    state_str = str()
    # LLenando la tabla de enlaces ICCP indisponibles AL MOMENTO
    for ix in df_to_process.index:
        name = df_to_process[u.lb_name].loc[ix]
        state = df_to_process[u.lb_state].loc[ix]
        prioridad = df_to_process[u.lb_prioridad].loc[ix]
        p_disponibilidad = df_to_process[u.lb_per_dispo].loc[ix]
        state_str += populate_state_table(prioridad, name, state, p_disponibilidad)

    if len(df_to_process.index) > 0:
        html_str = html_str.replace("<!--Inicio: ICCP_STATE-->", state_str)
    else:
        html_str = u.replace_block(from_label="<!-- INI:ICCP-->", to_label="<!-- END:ICCP-->",
                                   html_str=html_str, to_replace="")

    # Llenando la tabla de enlaces ICCP de mayor importancia:
    df = df[df[u.lb_prioridad] == 1]
    str_tb = str()
    for ix in df.index:
        name = df[u.lb_name].loc[ix]
        tag = df[u.lb_tag].loc[ix]
        if tag not in df_hist.columns:
            continue
        df_hist[tag] = [str(x) for x in df_hist[tag]]
        df_hist[tag] = u.get_translation(df_hist[tag], excel_path=excel_file, sheet_name=TranslateSheet)
        im_name = "rep_iccp_" + name + "_" + time_range.EndTime.ToString(fmt_dd_mm_yy_)
        image_p = os.path.join(images_path, im_name + ".png")
        image_p_relative = "./images/" + im_name + ".png"
        state = df_hist[tag].iloc[-1]
        _, color_map = u.get_state_colors(excel_path=excel_file, sheet_name=ColorSheet)
        u.generate_bar_estatus(series=df_hist[tag], fig_size=(15, 1), path_to_save=image_p, color_map=color_map)
        str_tb += f"<tr> <td> {name}</td>  <td>{state}</td>  \n" \
                  f"\t <td><div><img alt=\"{im_name}\" " \
                  f"  src=\"{image_p_relative}\"> </div> \n" \
                  f"</td></tr> \n"
    html_str = html_str.replace("<!--Inicio: ICCP_BARRAS-->", str_tb)
    return html_str


def even_row_style(c):
    if c % 2 == 1:
        return f'style="background-color: {even_color};"'
    return ""


def process_central_system(str_html):
    success_1, df, msg = u.read_excel(excel_file, sheet_name=SCentralSheet)
    success_2, dict_t = u.get_state_translation(excel_file, sheet_name=TranslateSheet)
    if not success_1 or not success_2:
        return False, msg

    df = df[df[u.lb_activa] == "x"]
    del df[u.lb_activa]
    str_tb = ""
    for c, ix in enumerate(df.index):
        str_tb += f"<tr {even_row_style(c)}>"
        for col in df.columns:
            value = df[col].loc[ix]
            if "SERVIDOR" not in col and "nan" not in str(value):
                tag_name = df[col].loc[ix]
                pt = p.PI_point(pi_svr, tag_name)
                if pt.pt is not None:
                    value = str(pt.current_value())
                    if value in dict_t.keys():
                        value = dict_t[value]
                if "spooling" == value:
                    snap = pt.snapshot()
                    value = str(snap.Value) + f" a partir de: {snap.Timestamp}"
            elif "nan" in str(value):
                value = ""

            if str(value) == "INDISPONIBLE" or "spooling a partir" in str(value):
                str_tb += f'<td style="background-color:#ff1a1a">{value}</td>'
            else:
                str_tb += f"<td>{value}</td>"
        str_tb += "</tr>\n"
    str_html = str_html.replace("<!--Inicio: CENTRAL_STATE-->", str_tb)
    return str_html


def bar(percentage):
    return f"<div class=\"meter\"> \n\t" \
           f"  <span style=\"width: {percentage * 0.75}%\"></span>  \n\t" \
           f"  <div style=\"float: right;\">{percentage} %</div> \n" \
           f"</div>"


def get_priority_style(priority):
    if 0 <= priority < len(prioridad_styles):
        return prioridad_styles[priority]
    return ""


def populate_state_table(prioridad, name, state, p_disponibilidad):
    if state == "Up":
        state = "DISPONIBLE"
    elif state == "Down":
        state = "INDISPONIBLE"
    to_put = ""
    if prioridad >= 0 and prioridad < len(criticidad):
        to_put = criticidad[prioridad]
    return f"<tr><td {get_priority_style(prioridad)}>{to_put}</td>  " \
           f"<td>{name}</td> <td>{state}</td> " \
           f"<td>{bar(p_disponibilidad)} </td> <td> </td> </tr> \n"


def process_agc_html(html_str: str, df: pd.DataFrame, df_hist: pd.DataFrame):
    str_tb = str()
    for ix in df.index:
        name = df[u.lb_name].loc[ix]
        tag = df[u.lb_tag].loc[ix]
        if tag not in df_hist.columns:
            continue
        df_hist[tag] = [str(x) for x in df_hist[tag]]
        df_hist[tag] = u.get_translation(df_hist[tag], excel_path=excel_file, sheet_name=TranslateSheet)
        state = df_hist[tag].iloc[-1]
        im_name = "rep_agc_" + name + "_" + time_range.EndTime.ToString(fmt_dd_mm_yy_)
        image_p = os.path.join(images_path, im_name + ".png")
        image_p_relative = "./images/" + im_name + ".png"
        _, color_map = u.get_state_colors(excel_path=excel_file, sheet_name=ColorSheet)
        u.generate_bar_estatus(series=df_hist[tag], fig_size=(15, 1), path_to_save=image_p, color_map=color_map)

        str_tb += f"<tr> <td> {name}</td>  <td> {state} </td> \n" \
                  f"\t <td><div><img alt=\"{im_name}\" " \
                  f"  src=\"{image_p_relative}\"> </div> \n" \
                  f"</td></tr> \n"

    html_str = html_str.replace("<!--Inicio: AGC_STATE-->", str_tb)
    return html_str


def run_process_for(time_range_to_run):
    global time_range
    global reporte_path
    time_range = time_range_to_run
    recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]
    # recipients = ["rsanchez@cenace.org.ec", "jenriquez@cenace.org.ec", "anarvaez@cenace.org.ec"]
    recipients = ["rsanchez@cenace.org.ec"]
    from_email = "sistemacentral@cenace.org.ec"

    # procesando el archivo html con campos de sRemoto, ya que la tabla UTR es similar:
    # Estado de UTRs:
    df = u.process_avalability_from_excel_file(excel_file=excel_file, sheet_name=sRemoto.sRemotoSheet,
                                                                     time_range_to_run=time_range_to_run)

    # filtrando aquellas que están indisponibles:
    df_filter = df[df[u.lb_state] == df[u.lb_filter]].copy()
    sRemoto.time_range = time_range_to_run  # definiendo periodo de supervisión
    sRemoto.html_template = html_central_file  # definiendo plantilla a utilizar
    str_html = sRemoto.process_html_file(df, df_filter, df_filter)  # llenando la plantilla

    # procesando el archivo html con estado de enlaces ICCP:
    # Estado de ICCP:
    df = u.process_avalability_from_excel_file(excel_file=excel_file, sheet_name=IccpSheet,
                                                                     time_range_to_run=time_range_to_run)

    _, df_hist = u.get_history_from(excel_file=excel_file, sheet_name=IccpSheet, time_range=time_range)
    df_indisp = df[df[u.lb_state] == df[u.lb_filter]]

    # procesando la información ICCP en el archivo ICCP:
    str_html = process_html_iccp(df, df_indisp, df_hist, str_html)

    # procesando Modo del AGC:
    df, df_hist = u.get_history_from(excel_file=excel_file, sheet_name=AGCSheet, time_range=time_range_to_run)
    # html processing
    str_html = process_agc_html(str_html, df, df_hist)

    # procesando Sistema Central:
    str_html = process_central_system(str_html)

    # encontrando imágenes en el archivo html y enviando el reporte por correo electrónico
    regex = 'src=(".*(\\.jpg|\\.png)"){1}'
    image_list = re.findall(regex, str_html)
    image_list = [im[0].replace('"', '') for im in image_list]
    send.send_mail(str_html, "Supervisión Sistema Central " + dt.datetime.now().strftime("%d/%m/%Y"),
                   recipients, from_email, image_list)

    # guardando el reporte en la carpeta reportes
    reporte_path = os.path.join(reporte_path,
                                f"sistema_central_{time_range_to_run.EndTime.ToString(fmt_dd_mm_yy_)}.html")
    u.save_html(str_html, reporte_path)


if __name__ == "__main__":
    try:
        # Definiendo fecha de la supervisión
        yesterday = u.define_time_range_for_yesterday()
        run_process_for(yesterday)
    except Exception as e:
        print(traceback.format_exc())
        ins.installer()
