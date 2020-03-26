"""
Este script permite recolectar datos de la plataforma web de los UPS de marca APC

"""


from urllib.request import urlopen
from bs4 import BeautifulSoup
import requests


""" Configuración de estilos """


estilos = {
    "alarmGood": "font: 11px Verdana, Arial, Helvetica, sans-serif; color: #060; font-weight: bold; padding-bottom: 2px; padding-top: 2px;",
	"dataSection": "font: 12px Verdana, Arial, Helvetica, sans-serif; color: #036; font-weight: bold; padding-top: 3px; padding-bottom: 3px; background-color:#E1EBFB; border-bottom: 1px solid #ccc; text-indent:2px;",
	"notactive": "line-height: 6px;background-color:#eee; border-top: 1px solid #ccc; border-right: 1px solid #ccc; border-bottom: 1px solid #666;border-left: 1px solid #666;",
	"indent2": "padding-left: 25px;",
	"active": "line-height: 6px;background-color:#090; border-top: 1px solid #0C0; border-right: 1px solid #0C0; border-bottom: 1px solid #030; border-left: 1px solid #030;",
	"dataName": "font-weight: normal; text-indent: 2px; text-align: left; color: #036;",
	"dataSubSection": "font: 12px Verdana, Arial, Helvetica, sans-serif; color: #369; font-weight: bold; padding-top:8px; text-indent:7px;",
	"dataSubSection2": "font: 11px Verdana, Arial, Helvetica, sans-serif; color: #369; font-weight: bold; padding-top:8px;"
}

def log_in_ups(ip_address, user, password):
    url_login = f"http://{ip_address}/Forms/login1"
    payload = {
        "login_username": user,
        "login_password": password
    }
    try:
        session_requests = requests.session()
        result = session_requests.post(
            url_login,
            data=payload,
            headers=dict(referer=url_login)
        )
        if result.status_code == 200:
            token = str(result.request.path_url).split("/")
            token = token[1] + "/"  + token[2]
            return True, token, "Log in exitoso"
        elif result.status_code == 403:
            return False, "", "Sesión ya abierta"
        else:
            return False, "", "Log in sin éxito"
    except Exception as e:
        msg = "Ha ocurrido un problema de conexión: \n" + str(e)
        return False, "", msg


def log_out_ups(ip_address):
    url_logout = f"http://{ip_address}/logout.htm"
    success, status_code = session_requests_get(url_logout)
    if success:
        return True, "Log out exitoso"
    else:
        return False, status_code


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


def provide_style_to(str_html: str, dict_style: dict):
    for k in dict_style.keys():
        str_html = str_html.replace(f'class="{k}"', f'style="{dict_style[k]}"')
    return str_html


def get_ups_info_for(ip_address, token, page_name):
    url_info = f"http://{ip_address}/{token}/{page_name}"
    success, result = session_requests_get(url_info)
    if not success:
        return False, f"No es posible consultar la página: {url_info} \n" + str(result)

    page = urlopen(url_info)
    soup = BeautifulSoup(page, 'html.parser')
    if "upstat.htm" == page_name:
        table = soup.findAll("table", {"class": "data"})[0]
        new_table = str()
        for child in table.children:
            if "Last Battery Transfer" in str(child) \
                    or "Bypass Input Voltage" in str(child) \
                    or "Peak Output Current" in str(child) \
                    or "Output Load kVA" in str(child) \
                    or "Fault Tolerance" in str(child) \
                    or "Redundancy:" in str(child)\
                    or "Output Watts at n+0:" in str(child)\
                    or 'class="space"' in str(child)\
                    or 'Measurements' in str(child)\
                    or "Present kVA Capacity:" in str(child):
                continue
            new_table += str(child)
        new_table = new_table.replace("Internal Temperature", "Temperatura interna")
        new_table = new_table.replace("Runtime Remaining", "Tiempo de autonomía")
        new_table = new_table.replace("Input Voltage", "Voltaje de entrada")
        new_table = new_table.replace("Input Current", "Corriente de entrada")
        new_table = new_table.replace("Output Voltage", "Voltaje de salida")
        new_table = new_table.replace("Output Current", "Corriente de salida")
        new_table = new_table.replace("Output VA at n+0", "VA (%)")
        return True, new_table

    if "uphome.htm" == page_name:
        tables = soup.findAll("table", {"class": "data"})
        content_to_add = tables[0].contents[5].contents[1]
        content = tables[1].contents[5]
        content.contents = content.contents[:1] + [content_to_add] + content.contents[1:]
        content = str(content).replace('width="70%"', 'width="100%"')
        content = content.replace('class="space" colspan="2"', '')
        content = content.replace('colspan="2"', 'colspan="3"')
        content = content.replace('active"> <', 'active">&nbsp;&nbsp;<')
        content = content.replace('Load in Watts', 'Toma de carga')
        content = content.replace('Battery Capacity', 'Capacidad de la batería')
        content = content.replace(' indent', '')
        return True, content

    return False, f"Página no encontrada: {url_info}"

