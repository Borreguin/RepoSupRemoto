"""
Este script ejecuta la supervisión de sistema remoto, basada en las configuraciones del archivo:
    "Config.xlsx (excel_file)", hoja: sRemoto
con los campos:
    Activa	Prioridad	EMPRESA	Nombre	Tag	Expresion	Tiempo	Porcentaje_Disp	Protocolo

El script envía un mail a la lista: recipients
con el usuario: from_email = "sistemaremoto@cenace.org.ec"
anexando las imágenes definidas en: image_list

"""



# Librería de conexión con Pi-Server, # librería para envíar mail de supervisión
import re
import traceback

from my_lib import pi_connect as p, sent_mail as send, util as u
import pandas as pd                       #Librería de análisis de datos
import datetime as dt
import codecs                               # Leer archivo HTML como un string
import os
import installer as ins

""" Variables globales """
pi_svr = p.PIserver()
lb_tag = "Tag"
lb_name = "Nombre"
lb_expression = "Expresion"
lb_tiempo = "Tiempo"
lb_per_dispo = "Porcentaje_Disp"
excel_file = "Config.xlsx"
lb_state = "Estado"
lb_date = "Fecha"
lb_period = "Periodo"
lb_activa = "Activa"
lb_protocol = "Protocolo"
lb_prioridad = "Prioridad"
sRemotoSheet = "sRemoto"

script_path = os.path.dirname(os.path.abspath(__file__))
html_remoto_file = os.path.join(script_path, "templates", "supervision_sist_remoto.html")
reporte_path = os.path.join(script_path, "reportes")
images_path = os.path.join(reporte_path, "images")
yyyy_mm_dd_hh_mm_ss = u.yyyy_mm_dd_hh_mm_ss
fmt_dd_mm_yyyy_hh_mm = u.fmt_dd_mm_yyyy_hh_mm
fmt_dd_mm_yy_ = u.fmt_dd_mm_yy_
time_range = None


def process_html_file(df, df_filter, df_indisp):
    global reporte_path
    global time_range
    # realizando las sustituciones necesarias para llenar el formulario HTML:
    html_str = codecs.open(html_remoto_file, 'r', 'utf-8').read()
    fecha = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_str = html_str.replace("(#dd/mm/yyyy)", fecha)
    html_str = html_str.replace("(#no_UTR)", str(len(df.index)))
    html_str = html_str.replace("(#no_UTR_indisponible)", str(len(df_indisp)))
    html_str = html_str.replace("(#ayer)", time_range.StartTime.ToString(fmt_dd_mm_yyyy_hh_mm))
    html_str = html_str.replace("(#hoy)", time_range.EndTime.ToString(fmt_dd_mm_yyyy_hh_mm))

    state_str = str()
    for ix in df_indisp.index:
        prioridad = df_indisp[lb_prioridad].loc[ix]
        name = df_indisp[lb_name].loc[ix]
        state = df_indisp[lb_state].loc[ix]
        protocol = df_indisp[lb_protocol].loc[ix]
        state_str += populate_state_table(prioridad, name, protocol, state)

    per_str = str()
    df_filter["minutes"] = (1-df_filter[lb_per_dispo]/100)*24*60
    for ix in df_filter.index:
        name = df_filter[lb_name].loc[ix]
        percentage = df_filter[lb_per_dispo].loc[ix]
        protocol = df_filter[lb_protocol].loc[ix]
        prioridad = df_filter[lb_prioridad].loc[ix]
        minutes = df_filter["minutes"].loc[ix]
        if minutes > 60:
            horas = int(minutes/60)
            minutes = "{:02d} h {:02d} m".format(horas, int(minutes-horas*60))
        else:
            minutes = "00 h {:02d} m".format(int(minutes))
        per_str += populate_disp_percentage(prioridad, name, protocol, minutes, percentage)

    html_str = html_str.replace("<!--Inicio: UTR_STATE-->", state_str)
    html_str = html_str.replace("<!--Inicio: UTR_INDISPONIBLE-->", per_str)

    return html_str


def populate_state_table(prioridad, name, protocol, state):
    return f"<tr> <td id=\"prioridad_{prioridad}\"></td>  <td>{name}</td> <td>{protocol}</td> <td>{state}</td></tr> \n\t"


def populate_disp_percentage(prioridad, name, protocol, minutes, percentage):
    return f"<tr> <td id=\"prioridad_{prioridad}\"></td>  <td>{name}</td> <td>{protocol}</td> <td>{minutes}</td> " \
           f"<td>{bar(percentage)} </td> </tr> \n\t"


def bar(percentage):
    return f"<div class=\"meter\"> \n\t" \
           f"  <span style=\"width: {percentage*0.75}%\"></span>  \n\t" \
           f"  <div style=\"float: right;\">{percentage}</div> \n" \
           f"</div>"


def run_process_for(time_range_to_run):
    global time_range
    global reporte_path
    time_range = time_range_to_run
    # calculando estado de UTRs:
    df, df_filter, df_indisp = u.process_excel_file(excel_file=excel_file, sheet_name=sRemotoSheet,
                                                    time_range_to_run=time_range_to_run)
    # recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]
    recipients = ["rsanchez@cenace.org.ec"]
    from_email = "sistemaremoto@cenace.org.ec"

    # llenando el template con datos
    str_html = process_html_file(df, df_filter, df_indisp)

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


if __name__ == "__main__":
    try:
        # Definiendo fecha de la supervisión
        yesterday = u.define_time_range_for_yesterday()
        run_process_for(yesterday)
    except Exception as e:
        print(traceback.format_exc())
        ins.installer()


