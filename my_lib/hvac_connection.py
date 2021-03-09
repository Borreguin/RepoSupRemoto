"""
Este script permite recolectar datos de la plataforma web de los HVAC de marca Stulz

"""
import re
from urllib.request import urlopen
from bs4 import BeautifulSoup
import requests
from lxml import html

estilos = {
    "cbox": "width:49%;min-width:230px;max-width:350px;float:left; background-color:#F9F9DF;border:1px solid #AA7",
    "ctitle": "text-align:center;font-size:14pt;font-weight:bold;line-height:32px;",
    "ovcaption": "float:left;font-size:11pt",
    "cvalue": "float:right"
}


def provide_style_to(str_html: str, dict_style: dict):
    for k in dict_style.keys():
        str_html = str_html.replace(f'class="{k}"', f'style="{dict_style[k]}"')
    return str_html


def log_in_hvac(ip_address, password):
    url_login = f"http://{ip_address}"
    payload = {
        "password": password
    }
    try:
        session_requests = requests.session()
        result = session_requests.post(
            url_login,
            data=payload,
            headers=dict(referer=url_login)
        )
        if result.status_code == 200:
            tree = html.fromstring(result.text)
            regex = 'id=[\d\.]+'
            token = re.findall(regex, result.text)
            return True, token[0], "Log in exitoso"
        elif result.status_code == 403:
            return False, "", "Sesión ya abierta"
        else:
            return False, "", "Log in sin éxito"
    except Exception as e:
        msg = "Ha ocurrido un problema de conexión: \n" + str(e)
        return False, "", msg


def session_requests_get(url):
    try:
        session_requests = requests.session()
        result = session_requests.get(url)
        if result.status_code == 200:
            return True, result
        else:
            return False, result
    except Exception as e:
        msg = "Problema en la conexión: \n" + str(e)
        return False, msg


def get_hvac_info_for(ip_address, token, page_name):
    url_info = f"http://{ip_address}/{page_name}?{token}"
    success, result = session_requests_get(url_info)
    if not success:
        return False, f"No es posible consultar la página: {url_info} \n" + str(result)

    success, table = False, f"No es posible consultar la página: {url_info} \n" + str(result)
    for i in range(5):

        try:
            page = urlopen(url_info)
            soup = BeautifulSoup(page, 'html.parser')
            if "UnitOverview.htm" == page_name:
                content = soup.findAll("div", {"id": "body"})[0]
                for ix in [1, 3]:
                    try:
                        content.contents[ix].contents[1].contents[3] = "\n"
                    except:
                        pass
                table = str(content).replace("<div>", '<div style="padding: 4px; clear:both; font-size: 11pt"; line-height:20px;>')
                table = table.replace('style="height:180px;"', 'style="height:130px;"')
                table = provide_style_to(table, estilos)
                success = True

        except Exception as e:
            success, table = False, f"Problemas al consultar la página: {url_info} \n" + str(e)

    return success, table
