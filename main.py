import subprocess as sb
from my_lib import pi_connect as p                    #Librería de conexión con Pi-Server
import pandas as pd                       #Librería de análisis de datos
import matplotlib.pyplot as plt           #Librería de gráficos (plots)
import datetime as dt
import codecs                               # Leer archivo HTML como un string
import os
import sent_mail as send
import installer as ins

""" Variables globales """
pi_svr = p.PIserver()
lb_tag = "Tag"
lb_name = "Nombre"
lb_expression = "Expresion"
lb_tiempo = "Tiempo"
lb_per_dispo = "Porcentaje_Disp"
excell_file = "Disponibilidad.xlsx"
lb_state = "Estado"
lb_date = "Fecha"
lb_period = "Periodo"
lb_activa = "Activa"
lb_protocol = "Protocolo"
lb_prioridad = "Prioridad"

script_path = os.path.dirname(os.path.abspath(__file__))
html_file = os.path.join(script_path, "templates", "supervision.html")
reporte_file = os.path.join(script_path, "reportes")
yyyy_mm_dd_hh_mm_ss = "%d-%m-%Y %H:%M:%S"
fmt_dd_mm_yyyy_hh_mm = "dd/MMM/yy HH:mm"
time_range = None


def define_time_range_for_yesterday():
    global time_range
    tdy = dt.datetime.now().strftime(yyyy_mm_dd_hh_mm_ss)
    ytd = dt.datetime.now() - dt.timedelta(days=1)
    time_range = pi_svr.time_range(ytd, tdy)
    return time_range


def process_excel_file(time_range, span=pi_svr.span("1d"), time_unit="di"):
    df = pd.read_excel(excell_file)
    df = df[df["Activa"] == "x"]
    df[lb_tiempo] = [0 for ix in df.index]
    df[lb_state] = ["" for ix in df.index]
    df = df.copy()
    for ix in df.index:
        tag_name = df[lb_tag].loc[ix]
        expression = "'{tag_name}' = \"DISPONIBLE\"".format(tag_name=tag_name)
        pt = p.PI_point(pi_svr, tag_name)
        value = pt.time_filter(time_range, expression, span, time_unit)
        df.loc[[ix], lb_tiempo] = value[tag_name][0]
        df.loc[[ix], lb_per_dispo] = round(value[tag_name][0]*100, 1)
        df.loc[[ix], lb_state] = str(pt.snapshot().Value)
        df.loc[[ix], lb_date] = str(pt.snapshot().Timestamp)
        df.loc[[ix], lb_period] = str(time_range).replace("00:00:00", "")

    df.sort_values(by=[lb_prioridad,  lb_per_dispo], inplace=True)
    # mask = (df[lb_per_dispo] < 99.5) & (df[lb_prioridad] == 1) & (df[lb_state] != "DISPONIBLE")
    mask = (df[lb_per_dispo] < 99.5)
    df_filter = df[mask].copy()
    df_indisp = df[df[lb_state] == "INDISPONIBLE"].copy()
    # df = df.set_index(lb_name)
    # df = df_filter.set_index(lb_name)
    # df = df_filter.set_index(lb_name)
    df_filter.sort_values(by=[lb_prioridad,  lb_per_dispo], inplace=True)
    return  df, df_filter, df_indisp


def process_html_file(df, df_filter, df_indisp):
    global reporte_file
    html_str = codecs.open(html_file, 'r', 'utf-8').read()
    fecha = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_str = html_str.replace("(#dd/mm/yyyy)", fecha)
    html_str = html_str.replace("(#no_UTR)", str(len(df.index)))
    html_str = html_str.replace("(#no_UTR_indisponible)", str(len(df_indisp)))
    html_str = html_str.replace("(#ayer)", time_range.StartTime.ToString(fmt_dd_mm_yyyy_hh_mm))
    html_str = html_str.replace("(#hoy)", time_range.EndTime.ToString(fmt_dd_mm_yyyy_hh_mm))

    state_str = str()
    for ix in df_indisp.index:
        timestamp = df_indisp[lb_date].loc[ix]
        name = df_indisp[lb_name].loc[ix]
        state = df_indisp[lb_state].loc[ix]
        protocol = df_indisp[lb_protocol].loc[ix]
        state_str += populate_state_table(name, protocol, state)

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
    fecha = fecha.replace("/","_")
    fecha = fecha.replace(":", "-")
    reporte_file = os.path.join(reporte_file, "sistema_remoto_{0}.html".format(fecha))

    Html_file = open(reporte_file, "w", encoding='utf-8')
    Html_file.write(html_str)
    Html_file.close()
    return html_str


def populate_state_table(name, protocol, state):
    return f"<tr> <td>{name}</td> <td>{protocol}</td> <td>{state}</td></tr> \n"


def populate_disp_percentage(prioridad, name, protocol, minutes, percentage):
    if prioridad == 1:
        return f"<tr> <td id=\"prioridad_1\"></td>  <td>{name}</td> <td>{protocol}</td> <td>{minutes}</td> " \
               f"<td>{bar(percentage)} </td> </tr> \n "
    if prioridad == 2:
        return f"<tr> <td id=\"prioridad_2\"></td>  <td>{name}</td> <td>{protocol}</td> <td>{minutes}</td> " \
               f"<td>{bar(percentage)} </td> </tr> \n"
    if prioridad == 3:
        return f"<tr> <td id=\"prioridad_3\"></td>  <td>{name}</td> <td>{protocol}</td> <td>{minutes}</td> " \
               f"<td>{bar(percentage)} </td> </tr> \n "
    else:
        return f"<tr> <td></td>  <td>{name}</td> <td>{protocol}</td> <td>{minutes}</td> </td> " \
               f"<td>{bar(percentage)} </tr> \n"


def bar(percentage):
    return f"<div class=\"meter\"> \n " \
           f"  <span style=\"width: {percentage*0.75}%\"></span>  \n " \
           f"  <div style=\"float: right;\">{percentage}</div> \n " \
           f"</div>"


def run_process_for_yesteday():
    time_range = define_time_range_for_yesterday()
    df, df_filter, df_indisp = process_excel_file(time_range)
    recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]
    # recipients = ["rsanchez@cenace.org.ec"]
    from_email = "sistemaremoto@cenace.org.ec"
    image_list = ["cenace.jpg"]
    str_html = process_html_file(df, df_filter, df_indisp)
    send.send_mail(str_html, "Supervisión Sistema Remoto " + dt.datetime.now().strftime("%d/%m/%Y"),
                   recipients, from_email, image_list)


if __name__ == "__main__":
    try:
        run_process_for_yesteday()
    except Exception as e:
        print(e)
        ins.installer()


