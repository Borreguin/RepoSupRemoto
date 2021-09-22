"""
Este script ejecuta la supervisión de sistema remoto, basada en las configuraciones del archivo:
    "Config.xlsx (excel_file)", hoja: sRemoto
con los campos:
    Activa	Prioridad	EMPRESA	Nombre	Tag	Expresion	Tiempo	Porcentaje_Disp	Protocolo

El script envía un mail a la lista: recipients
con el usuario: from_email = "sistemaremoto@cenace.org.ec"
anexando las imágenes definidas en: image_list

"""

import codecs  # Leer archivo HTML como un string
import datetime as dt
import os
import re
import traceback
import installer as ins
import matplotlib.colors as colors

# Librería de conexión con Pi-Server, # librería para envíar mail de supervisión
from flask_app.my_lib.PI_connection import pi_connect as p
from flask_app.my_lib.PI_connection.pi_connect import _time_range, _span
from flask_app.my_lib.SendMail import send_mail as send
from flask_app.my_lib import utils as u

""" Variables globales """
pi_svr = p.PIserver()
excel_file = "Config.xlsx"
# etiquetas de la hoja Config
lb_tag = "Tag"
lb_name = "Nombre"
lb_expression = "Expresion"
lb_tiempo_disponible = "Tiempo Disponibilidad en minutos"
lb_tiempo_indisponible = "Tiempo Indisponibilidad en minutos"
lb_risk = "Porcentaje de riesgo"
lb_per_dispo = "Porcentaje_Disp"
lb_state = "Estado"
lb_date = "Fecha"
lb_period = "Periodo"
lb_activa = "Activa"
lb_protocol = "Protocolo"
lb_prioridad = "Prioridad"
lb_filter = "Filter"
# Hojas a utilizar del archivo excel
sRemotoSheet = "sRemoto"
ColorSheet = "COLORES"

minutos_mes = 60 * 24 * 30
minutos_semana = 60 * 24 * 7
minutos_dia = 60 * 24

# HTML definitions
even_color = "#f2f2f2"

# estilos de las prioridades:
prioridad_styles = ["", 'style="vertical-align: top; text-align: center; background-color: rgb(255, 0, 0); font-weight: bold"; font-size: 10pt',
                    'style="vertical-align: top; text-align: center; background-color: rgb(255, 203, 0); font-weight: bold"; font-size: 10pt',
                    'style="vertical-align: top; text-align: center; background-color: rgb(255, 255, 102); font-weight: bold"; font-size: 10pt',
                    'style="vertical-align: top; text-align: center; background-color: rgb(255, 255, 255); font-weight: bold"; font-size: 10pt'  ]

criticidad = ["", "ALTO", "MEDIO", "BAJO", "NO CRÍTICO"]
criticidad_value = [0, 1, 0.67, 0.33, 0]

""" Configuraciones del script """
script_path = os.path.dirname(os.path.abspath(__file__))
html_template = os.path.join(script_path, "templates", "supervision_sist_remoto.html")
reporte_path = os.path.join(script_path, "reportes")
images_path = os.path.join(reporte_path, "images")
yyyy_mm_dd_hh_mm_ss = "%d-%m-%Y %H:%M:%S"
fmt_dd_mm_yyyy_hh_mm = "dd/MMM/yy HH:mm"
fmt_dd_mm_yy_ = "dd/MMM/yyyy"
time_range = None


def process_html_file(df, df_filter, df_indisp, df_hist=None):
    global reporte_path
    global time_range
    # realizando las sustituciones necesarias para llenar el formulario HTML:
    html_str = codecs.open(html_template, 'r', 'utf-8').read()
    fecha = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_str = html_str.replace("(#dd/mm/yyyy)", fecha)
    html_str = html_str.replace("(#no_UTR)", str(len(df.index)))
    html_str = html_str.replace("(#no_UTR_indisponible)", str(len(df_indisp)))
    html_str = html_str.replace("(#ayer)", time_range.StartTime.ToString(fmt_dd_mm_yyyy_hh_mm))
    html_str = html_str.replace("(#hoy)", time_range.EndTime.ToString(fmt_dd_mm_yyyy_hh_mm))

    # llenando la tabla de REPORTE INSTANTANEO
    state_str = str()
    per_str = str()
    str_semanal = str()
    for c, ix in enumerate(df_indisp.index):
        prioridad = df_indisp[lb_prioridad].loc[ix]
        name = df_indisp[lb_name].loc[ix]
        state = df_indisp[lb_state].loc[ix]
        protocol = df_indisp[lb_protocol].loc[ix]
        state_str += populate_state_table(prioridad, name, protocol, state, c)

    if not df_filter.empty:
        # llenando la tabla de REPORTE DEL ÚLTIMO DÍA
        # calculo de la afectación a la disponibilidad mensual
        df_filter[lb_tiempo_indisponible] = [(minutos_dia - disp) for disp in df_filter[lb_tiempo_disponible]]
        # Riesgo = indisponibilidad x nivel de criticidad
        df_filter[lb_risk] = [get_risk_percentage(min_ind/minutos_mes, prioridad) for min_ind, prioridad in
                       zip(df_filter[lb_tiempo_indisponible], df_filter[lb_prioridad])]

        df_filter.sort_values(by=[lb_risk, lb_tiempo_indisponible], inplace=True, ascending=False)
        for c, ix in enumerate(df_filter.index):
            name = df_filter[lb_name].loc[ix]
            minutos_indisponibles = df_filter[lb_tiempo_indisponible].loc[ix]
            porcentaje_mensual_indisponibilidad = minutos_indisponibles/minutos_mes
            porcentaje_diario_indisponibilidad = minutos_indisponibles/minutos_dia
            porcentaje_disponibilidad = df_filter[lb_tiempo_disponible].loc[ix]/minutos_dia
            protocol = df_filter[lb_protocol].loc[ix]
            prioridad = df_filter[lb_prioridad].loc[ix]
            porcentaje_risk = get_risk_percentage(porcentaje_diario_indisponibilidad, prioridad)
            if minutos_indisponibles > 60:
                horas = int(minutos_indisponibles/60)
                minutos_indisponibles = "{:02d} h {:02d} m".format(horas, int(minutos_indisponibles-horas*60))
            else:
                minutos_indisponibles = "00 h {:02d} m".format(int(minutos_indisponibles))
            per_str += populate_disp_percentage(prioridad, name, protocol, minutos_indisponibles,
                                                porcentaje_disponibilidad, porcentaje_risk, c)

    # Cálculo semanal
    if df_hist is not None and not df_hist.empty:
        df_hist[lb_tiempo_indisponible] = [(minutos_semana - disp) for disp in df_hist[lb_tiempo_disponible]]
        # Riesgo = indisponibilidad x nivel de criticidad
        df_hist[lb_risk] = [get_risk_percentage(min_ind / minutos_mes, prioridad) for min_ind, prioridad in
                              zip(df_hist[lb_tiempo_indisponible], df_hist[lb_prioridad])]

        df_hist.sort_values(by=[lb_risk, lb_tiempo_indisponible], inplace=True, ascending=False)
        # filtrando aquellas que estan indisponibles:
        df_hist = df_hist[df_hist[lb_state] == df_hist[lb_filter]].copy()
        # filtrando aquellas cuya indisponibilidad supera los 4 días
        t_filter = 4*24*60
        df_hist = df_hist[df_hist[lb_tiempo_indisponible] > t_filter]
        period = df_hist[lb_period].iloc[0]
        html_str = html_str.replace("(#periodo_semanal)", period)

        for c, ix in enumerate(df_hist.index):
            name = df_hist[lb_name].loc[ix]
            tag_name = df_hist[lb_tag].loc[ix]
            protocol = df_hist[lb_protocol].loc[ix]
            prioridad = df_hist[lb_prioridad].loc[ix]
            porcentaje_mensual_indisponibilidad = df_hist[lb_tiempo_indisponible].loc[ix]/minutos_mes
            porcentaje_risk = get_risk_percentage(df_hist[lb_tiempo_indisponible].loc[ix]/minutos_semana, prioridad)
            porcentaje_disponibilidad = df_hist[lb_tiempo_disponible].loc[ix]/minutos_semana
            pt = p.PI_point(pi_svr, tag_name)
            str_week_time = str(df_hist[lb_period].loc[ix]).split("-")
            week_time_range = pi_svr.time_range(str_week_time[0], str_week_time[1])
            df_h = pt.interpolated(week_time_range, span=pi_svr.span("1h"), numeric=False)
            df_h[tag_name] = [str(x) for x in df_h[tag_name]]
            # creando las barras de estados:
            im_name = "rep_utr_" + name + "_" + time_range.EndTime.ToString(fmt_dd_mm_yy_)
            image_p = os.path.join(images_path, im_name + ".png")
            image_p_relative = "./images/" + im_name + ".png"
            _, color_map = u.get_state_colors(excel_path=excel_file, sheet_name=ColorSheet)
            u.generate_bar_estatus(series=df_h[tag_name], fig_size=(15, 1), path_to_save=image_p, color_map=color_map)
            str_semanal += populate_with_bars(name, protocol, porcentaje_disponibilidad,
                                              image_p_relative, porcentaje_risk, c)

    html_str = html_str.replace("<!--Inicio: UTR_STATE-->", state_str)
    html_str = html_str.replace("<!--Inicio: UTR_INDISPONIBLE-->", per_str)
    html_str = html_str.replace("<!--Inicio: UTR_SEMANAL-->", str_semanal)
    return html_str


def populate_with_bars(name, protocol, percentage, image_scr, porcentaje_risk, c=0):
    return f"<tr {even_row_style(c)} > " \
           f" <td {get_color_for_risk(porcentaje_risk)}> {int(porcentaje_risk)} %</td> " \
           f" <td>{name}</td> " \
           f" <td>{protocol}</td> <td>{round(percentage*100, 1)} %</td> " \
           f"\t <td><div><img alt=\"{image_scr}\" src=\"{image_scr}\"> </div> \n" \
                  f"</td></tr> \n"


def populate_state_table(prioridad, name, protocol, state, c=0):
    to_put = ""
    if prioridad >= 0 and prioridad < len(criticidad):
        to_put = criticidad[prioridad]
    return f"<tr {even_row_style(c)} > <td {get_priority_style(prioridad)}>{to_put}</td>  " \
           f"<td>{name}</td> <td>{protocol}</td> <td>{state}</td></tr> \n\t"


def populate_disp_percentage(prioridad, name, protocol, minutes, porcentaje_indisponibilidad, porcentaje_risk, c=0):

    return f"<tr {even_row_style(c)} >  " \
           f" <td {get_color_for_risk(porcentaje_risk)}> {int(porcentaje_risk)} %</td> " \
           f" <td>{name}</td> <td>{protocol}</td> <td>{minutes}</td> " \
           f"<td>{bar(porcentaje_indisponibilidad)}</td> </tr> \n\t"


def get_color_for_risk(porcentaje_risk):
    color_lst = [(0, 'white'), (0.33, 'yellow'), (0.67, 'orange'), (1, 'red')]
    cmap = colors.LinearSegmentedColormap.from_list("risk_scale", color_lst)
    c_val = cmap(porcentaje_risk / 100)
    return f'style="background-color: ' \
           f'rgb({str(int(c_val[0]*255))},{str(int(c_val[1]*255))},{str(int(c_val[2]*255))})"'



def bar(percentage):
    return f"<div class=\"meter\"> \n\t" \
           f"  <span style=\"width: {percentage*0.75*100}%\"></span>  \n\t" \
           f"  <div style=\"float: right;\">{round(percentage*100,1)}%</div> \n" \
           f"</div>"


def even_row_style(c):
    if c % 2 == 1:
        return f'style="background-color: {even_color};"'
    return ""


def get_priority_style(priority):
    if 0 <= priority < len(prioridad_styles):
        return prioridad_styles[priority]
    return ""


def get_criticidad(prioridad):
    if prioridad >= 0 and prioridad < len(criticidad):
        return criticidad[prioridad]
    return ""


def get_risk_percentage(porcentaje_indisponibilidad, prioridad):
    value = 0
    if prioridad > 0 and prioridad < len(criticidad_value):
        value = criticidad_value[prioridad]
    return round(porcentaje_indisponibilidad * value * 100, 1)


def run_process_for(time_range_to_run,recipients,from_email):
    global time_range
    global reporte_path
    # definiendo tiempo del reporte:
    ini_date,end_date = time_range_to_run
    time_range=_time_range(ini_date,end_date)
    # definiendo tiempo del reporte una semana atrás:
    week_time_range = u.define_time_range_for_this_week(end_date)

    # definiendo configuraciones para mail:
    # recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]

    # calculando estado de UTRs:
    df = u.process_avalability_from_excel_file(excel_file=excel_file, sheet_name=sRemotoSheet,
                                                                     time_range_to_run=time_range_to_run,
                                                                     span=_span("1d"),
                                                                     time_unit="mi")

    # procesando información de una semana:
    df_hist = u.process_avalability_from_excel_file(excel_file=excel_file, sheet_name=sRemotoSheet,
                                                          time_range_to_run=week_time_range,
                                                          span=_span("7d"),
                                                          time_unit="mi")

    # filtrando aquellas que se encuentran indisponibles:
    df_indisp = df[df[lb_state] == df[lb_filter]]

    # filtrando aquellas cuya indisponibilidad sea superior a 3.6 horas:
    df_filter = df[df[lb_tiempo_disponible] <= (24*60-3.6*60)].copy()

    # llenando el template con datos
    str_html = process_html_file(df, df_filter, df_indisp, df_hist)

    # guardando el reporte en la carpeta reportes
    reporte_path = os.path.join(reporte_path, f"sistema_remoto_{time_range_to_run.EndTime.ToString(fmt_dd_mm_yy_)}.html")
    u.save_html(str_html, reporte_path)

    # encontrando imágenes en el archivo html para anexarlas
    # al momento del envío:
    regex = 'src=(".*(\\.jpg|\\.png)"){1}'
    image_list = re.findall(regex, str_html)
    image_list = [im[0].replace('"', '') for im in image_list]

    send.send_mail(str_html, "Supervisión Sistema Remoto " + dt.datetime.now().strftime("%d/%m/%Y"),
                   recipients, from_email, image_list)
    return True, f"[{dt.datetime.now()}]El reporte de sistema remoto ha sido enviado existosamente a: {recipients}"



