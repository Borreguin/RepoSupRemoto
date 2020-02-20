"""
Este script ejecuta la supervisión de sistema remoto, basada en las configuraciones del archivo:
    "Config.xlsx (excel_file)", hoja:




"""

# Librería de conexión con Pi-Server, # librería para envíar mail de supervisión
import traceback

from my_lib import pi_connect as p, sent_mail as send, util as u
import pandas as pd  # Librería de análisis de datos
import datetime as dt
import codecs  # Leer archivo HTML como un string
import os
import installer as ins
import sRemoto
import re

""" Variables globales """
pi_svr = p.PIserver()
excel_file = sRemoto.excel_file
reporte_path = sRemoto.reporte_path
script_path = os.path.dirname(os.path.abspath(__file__))
html_central_file = os.path.join(script_path, "templates", "supervision_prg_SCADA.html")
images_path = os.path.join(reporte_path, "images")
IccpSheet = "ICCP"
AGCSheet = "AGC"

time_range = None


def process_html_iccp(df, df_indisp, html_str):
    global reporte_path
    # realizando las sustituciones necesarias para llenar el formulario HTML:
    html_str = html_str.replace("(#no_ICCP)", str(len(df.index)))
    html_str = html_str.replace("(#no_ICCP_indisponible)", str(len(df_indisp)))
    f_text = df[u.lb_filter].iloc[0]
    mask = (df[sRemoto.lb_per_dispo] < 99.5) | (df[sRemoto.lb_state] == str(f_text))
    df_to_process = df[mask]
    state_str = str()
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
    return html_str


def bar(percentage):
    return f"<div class=\"meter\"> \n\t" \
           f"  <span style=\"width: {percentage * 0.75}%\"></span>  \n\t" \
           f"  <div style=\"float: right;\">{percentage}</div> \n" \
           f"</div>"


def populate_state_table(prioridad, name, state, p_disponibilidad):
    if state == "Up":
        state = "DISPONIBLE"
    elif state == "Down":
        state = "INDISPONIBLE"
    return f"<tr> <td id=\"prioridad_{prioridad}\"></td>  <td>{name}</td> <td>{state}</td> " \
           f"<td>{bar(p_disponibilidad)} </td> <td> </td> </tr> \n"


def process_agc_html(html_str: str, df: pd.DataFrame, df_hist: pd.DataFrame):
    str_tb = str()
    for ix in df.index:
        name = df[u.lb_name].loc[ix]
        tag = df[u.lb_tag].loc[ix]
        if tag not in df_hist.columns:
            continue
        df_hist[tag] = [str(x) for x in df_hist[tag]]
        state = df_hist[tag].iloc[-1]
        image_p = os.path.join(images_path, name + ".png")
        image_p_relative = "./images/" + name + ".png"
        u.generate_bar_estatus(series=df_hist[tag], fig_size=(12, 1), path_to_save=image_p)

        str_tb += f"<tr> <td> {name}</td>  <td> {state} </td> \n" \
                  f"\t <td><div><img alt=\"{name}\" " \
                  f"  src=\"{image_p_relative}\"> </div> \n" \
                  f"</td></tr> \n"

    html_str = html_str.replace("<!--Inicio: AGC_STATE-->", str_tb)
    return html_str


def run_process_for(time_range_to_run):
    global time_range
    time_range = time_range_to_run
    # recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]
    recipients = ["rsanchez@cenace.org.ec"]
    from_email = "sistemacentral@cenace.org.ec"
    image_list = ["cenace.jpg", "./images/Molino AGC.png"]
    # procesando el archivo html con campos de sRemoto, ya que la tabla UTR es similar:
    # Estado de UTRs:
    df, df_filter, df_indisp = u.process_excel_file(excel_file=excel_file, sheet_name=sRemoto.sRemotoSheet,
                                                    time_range_to_run=time_range_to_run)
    sRemoto.time_range = time_range_to_run  # definiendo periodo de supervisión
    sRemoto.html_remoto_file = html_central_file  # definiendo plantilla a utilizar
    str_html = sRemoto.process_html_file(df, df_filter, df_indisp)  # llenando la plantilla

    # procesando el archivo html con estado de enlaces ICCP:
    # Estado de ICCP:
    df, df_filter, df_indisp = u.process_excel_file(excel_file=excel_file, sheet_name=IccpSheet,
                                                    time_range_to_run=time_range_to_run)
    # procesando la información ICCP en el archivo ICCP:
    str_html = process_html_iccp(df, df_indisp, str_html)

    # procesando Modo del AGC:
    df, df_hist = u.get_history_from(excel_file=excel_file, sheet_name=AGCSheet, time_range=time_range_to_run)
    # html processing
    str_html = process_agc_html(str_html, df, df_hist)

    # encontrando imágenes en el archivo html
    regex = 'src=(".*(\\.jpg|\\.png)"){1}'
    image_list = re.findall(regex, str_html)
    image_list = [im[0].replace('"', '') for im in image_list]
    send.send_mail(str_html, "Supervisión Sistema Central " + dt.datetime.now().strftime("%d/%m/%Y"),
                   recipients, from_email, image_list)


if __name__ == "__main__":
    try:
        # Definiendo fecha de la supervisión
        yesterday = u.define_time_range_for_yesterday()
        run_process_for(yesterday)
    except Exception as e:
        print(traceback.format_exc())
        ins.installer()
