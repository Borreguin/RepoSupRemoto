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

# Librería de conexión con Pi-Server, # librería para envíar mail de supervisión
from my_lib import pi_connect as p, send_mail as send, util as u

""" Variables globales """
pi_svr = p.PIserver()
excel_file = "Config.xlsx"
# etiquetas de la hoja Config
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
# Hojas a utilizar del archivo excel
sRemotoSheet = "sRemoto"
ColorSheet = "COLORES"

""" Configuraciones del script """
script_path = os.path.dirname(os.path.abspath(__file__))
html_remoto_file = os.path.join(script_path, "templates", "supervision_sist_remoto.html")
reporte_path = os.path.join(script_path, "reportes")
images_path = os.path.join(reporte_path, "images")
yyyy_mm_dd_hh_mm_ss = u.yyyy_mm_dd_hh_mm_ss
fmt_dd_mm_yyyy_hh_mm = u.fmt_dd_mm_yyyy_hh_mm
fmt_dd_mm_yy_ = u.fmt_dd_mm_yy_
time_range = None


def process_html_file(df, df_filter, df_indisp, df_hist=None):
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

    # llenando la tabla de REPORTE INSTANTANEO
    state_str = str()
    for ix in df_indisp.index:
        prioridad = df_indisp[lb_prioridad].loc[ix]
        name = df_indisp[lb_name].loc[ix]
        state = df_indisp[lb_state].loc[ix]
        protocol = df_indisp[lb_protocol].loc[ix]
        state_str += populate_state_table(prioridad, name, protocol, state)

    # llenando la tabla de REPORTE DEL ÚLTIMO DÍA
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

    str_semanal = str()
    if df_hist is not None and not df_hist.empty:
        df_hist[lb_per_dispo] = [round(x/7, 2) for x in df_hist[lb_per_dispo]]
        filter_exp = df_hist[u.lb_filter].iloc[0]
        mask = (df_hist[lb_state] == f"{filter_exp}") & (df_hist[lb_per_dispo] < 99.5)
        df_hist = df_hist[mask].copy()
        period = df_hist[lb_period].iloc[0]
        html_str = html_str.replace("(#periodo_semanal)", period)

        for ix in df_hist.index:
            name = df_hist[lb_name].loc[ix]
            tag_name = df_hist[lb_tag].loc[ix]
            protocol = df_hist[lb_protocol].loc[ix]
            prioridad = df_hist[lb_prioridad].loc[ix]
            percentage = df_hist[lb_per_dispo].loc[ix]
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
            str_semanal += populate_with_bars(prioridad, name, protocol, percentage, image_p_relative)

    html_str = html_str.replace("<!--Inicio: UTR_STATE-->", state_str)
    html_str = html_str.replace("<!--Inicio: UTR_INDISPONIBLE-->", per_str)
    html_str = html_str.replace("<!--Inicio: UTR_SEMANAL-->", str_semanal)
    return html_str


def populate_with_bars(prioridad, name, protocol, percentage,image_scr):
    return f"<tr> <td id=\"prioridad_{prioridad}\"></td>  <td>{name}</td> " \
           f"<td>{protocol}</td> <td>{percentage}</td> " \
           f"\t <td><div><img alt=\"{image_scr}\" src=\"{image_scr}\"> </div> \n" \
                  f"</td></tr> \n"


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
    # definiendo tiempo del reporte:
    time_range = time_range_to_run

    # definiendo tiempo del reporte una semana atrás:
    week_time_range = u.define_time_range_for_last_week()

    # definiendo configuraciones para mail:
    recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]
    # recipients = ["rsanchez@cenace.org.ec"]
    from_email = "sistemaremoto@cenace.org.ec"

    # calculando estado de UTRs:
    df, df_filter, df_indisp = u.process_excel_file(excel_file=excel_file, sheet_name=sRemotoSheet,
                                                    time_range_to_run=time_range_to_run)

    # procesando información de una semana:
    df_hist, _, _ = u.process_excel_file(excel_file=excel_file, sheet_name=sRemotoSheet,
                                                    time_range_to_run=week_time_range,  span=pi_svr.span("7d"))

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


if __name__ == "__main__":
    try:
        # Definiendo fecha de la supervisión
        yesterday = u.define_time_range_for_yesterday()
        run_process_for(yesterday)
    except Exception as e:
        print(traceback.format_exc())
        ins.installer()


