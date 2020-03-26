"""
Este script ejecuta la supervisión de sistema auxiliares, basada en las configuraciones del archivo:
    "Config.xlsx (excel_file)", hoja: sAuxiliares
con los campos:


El script envía un mail a la lista: recipients
con el usuario: from_email = "sistemasauxiliares@cenace.org.ec"
anexando las imágenes definidas en: image_list

"""
import codecs
import re
import traceback
from urllib.request import urlopen
from bs4 import BeautifulSoup
import datetime as dt
import pandas as pd
import os
import requests
from lxml import html
from my_lib import util as u, send_mail as send, ups_connection as ups_con, hvac_connection as hvac_con

""" Variables globales """

fmt_dd_mm_yy_ = "%d_%m_%Y"
ini_ups_state = "<!-- start ups:state --->"
end_ups_state = "<!-- end ups:state --->"
tag_ups_state = "<!-- ups:state -->"

ini_hvac_state = "<!-- start hvac:state --->"
end_hvac_state = "<!-- end hvac:state --->"
tag_hvac_state = "<!-- hvac:state -->"

""" Configuraciones del script """
excel_file = "Config.xlsx"
sheet_name = "sAuxiliares"
lb_tipo = "Tipo"
lb_usuario = "Usuario"
lb_password = "Password"
lb_ip = "IP"
lb_equipo = "Equipo"
lb_activa = "Activa"
script_path = os.path.dirname(os.path.abspath(__file__))
reporte_path = os.path.join(script_path, "reportes")
excel_file_path = os.path.join(script_path, excel_file)
html_template = os.path.join(script_path, "templates", "supervision_sist_auxiliares.html")


def process_data_for_hvac(ip_address, password):
    """ Log in to the UPS, Let´s try 3 times at least if there is a problem """
    success, token, msg = None, None, ""
    for ix in range(3):
        success, token, msg = hvac_con.log_in_hvac(ip_address, password)
        if success:
            break
    if not success:
        return False, "Log-in sin éxito (3 veces):\n " + msg

    """ Buscando información en las páginas web """
    pages = ["UnitOverview.htm"]
    html_str = str()
    for page in pages:
        success, str_info = hvac_con.get_hvac_info_for(ip_address, token, page)
        if success:
            html_str += str_info
    return True, html_str


def process_data_for_ups(ip_address, user, password):
    """ Log in to the UPS, Let´s try 3 times at least if there is a problem """
    success, token, msg = None, None, ""
    for ix in range(3):
        success, token, msg = ups_con.log_in_ups(ip_address, user, password)
        if success:
            break
        else:
            ups_con.log_out_ups(ip_address)
    if not success:
        return False, "Log-in sin éxito (3 veces):\n " + msg

    """ Buscando información en las páginas web """
    pages = ["uphome.htm", "upstat.htm"]
    html_str = str()
    for page in pages:
        success, str_info = ups_con.get_ups_info_for(ip_address, token, page)
        str_info =  ups_con.provide_style_to(str_info, ups_con.estilos)
        if success:
            html_str += str_info
    """ Haciendo Log out del UPS """
    ups_con.log_out_ups(ip_address)
    if len(html_str) == 0:
        return False, "<p> No fue posible establecer conexión con este equipo </p>"
    return True, html_str


# session_requests = requests.session()
# login_url = "http://10.30.201.151/logon.htm"
# result = session_requests.get(login_url)

# tree = html.fromstring(result.text)
# authenticity_token = list(set(tree.xpath("//input[@name='csrfmiddlewaretoken']/@value")))[0]
# 403 es invalido
# 200 es valido


def run_process_now():

    global time_range
    global reporte_path

    # leyendo información de configuración desde archivo excel
    df_config = pd.read_excel(excel_file, sheet_name=sheet_name)
    df_config = df_config[df_config[lb_activa] == "x"]

    # definiendo configuraciones para mail:
    # recipients = ["mbautista@cenace.org.ec", "ems@cenace.org.ec"]
    recipients = ["rsanchez@cenace.org.ec", "farmas@cenace.org.ec"]
    from_email = "sistemasauxiliares@cenace.org.ec"

    # leyendo la plantilla para el reporte
    html_str = codecs.open(html_template, 'r', 'utf-8').read()
    ups_html_state = u.get_block(ini_ups_state, end_ups_state, html_str)

    # colocando la fecha del reporte:
    fecha = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_str = html_str.replace("(#dd/mm/yyyy)", fecha)

    # Procesando UPS:
    ups_block_states = str()
    df_ups = df_config[df_config[lb_tipo] == "UPS apc"]
    for idx in df_ups.index:
        # get variables to process:
        ip = df_ups[lb_ip].loc[idx]
        equipo = df_ups[lb_equipo].loc[idx]
        user = df_ups[lb_usuario].loc[idx]
        password = df_ups[lb_password].loc[idx]
        # get information from ups
        success, current_hvac_state = process_data_for_ups(ip, user, password)
        # colocando en el formato definido en la plantilla
        current_hvac_state = ups_html_state.replace(tag_ups_state, current_hvac_state)
        current_hvac_state = current_hvac_state.replace("Estado UPS", equipo)
        ups_block_states += current_hvac_state

    # Colocando el estado de todos los UPS:
    html_str = u.replace_block(ini_ups_state, end_ups_state, html_str, ups_block_states)


    # Procesando HVAC:
    df_hvac = df_config[df_config[lb_tipo] == "HVAC stulz"]
    hvac_html_state = u.get_block(ini_hvac_state, end_hvac_state, html_str)
    hvac_block_states = str()
    for idx in df_hvac.index:
        # get variables to process:
        ip = df_hvac[lb_ip].loc[idx]
        equipo = df_hvac[lb_equipo].loc[idx]
        password = df_hvac[lb_password].loc[idx]
        # get information from hvac
        success, current_hvac_state = process_data_for_hvac(ip, password)
        # colocando en el formato definido en la plantilla
        current_hvac_state = hvac_html_state.replace(tag_hvac_state, current_hvac_state)
        current_hvac_state = current_hvac_state.replace("Estado Aire acondicionado", equipo)
        hvac_block_states += current_hvac_state

    # Colocando el estado de todos los HVAC:
    html_str = u.replace_block(ini_hvac_state, end_hvac_state, html_str, hvac_block_states)

    # guardando el reporte en la carpeta reportes
    reporte_path = os.path.join(reporte_path,
                                f"sistema_auxiliares_{dt.datetime.now().strftime(fmt_dd_mm_yy_)}.html")
    u.save_html(html_str, reporte_path)

    # encontrando imágenes en el archivo html para anexarlas
    # al momento del envío:
    regex = 'src=(".*(\\.gif|\\.jpg|\\.png)"){1}'
    image_list = re.findall(regex, html_str)
    image_list = [im[0].replace('"', '') for im in image_list]

    send.send_mail(html_str, "Supervisión Equipos de Energía y Climatización CENACE " +
                   dt.datetime.now().strftime("%d/%m/%Y"),
                   recipients, from_email, image_list)


if __name__ == "__main__":
    try:
        run_process_now()
    except Exception as e:
        print(traceback.format_exc())
