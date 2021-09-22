# Created by Roberto Sanchez at 4/16/2019
# -*- coding: utf-8 -*-
""""
    Servicio Web de Sistema Remoto:
        - Permite la administración de Nodos, Entidades y Tags
        - Serializar e ingresar datos

    If you need more information. Please contact the email above: rg.sanchez.a@gmail.com
    "My work is well done to honor God at any time" R Sanchez A.
    Mateo 6:33
"""
import datetime as dt
from flask_app.api.services.sRemoto.endpoints import *
from flask_restplus import Resource
# importando configuraciones iniciales
from flask_app.my_lib import utils
from flask_app.my_lib.SendMail.send_mail import send_mail
from flask_app.my_lib.Sistema_Remoto.sRemoto import run_process_for
from flask_app.api.services.restplus_config import api
from flask_app.api.services.sRemoto import serializers as srl

# importando clases para leer desde MongoDB


# configurando logger y el servicio web, para ejecutar Reporte de Sistema Remoto
#ENVIO AUTOMATICO DE REPORTE

ns = api.namespace('exec-sRemoto', description='Ejecutar reporte de Sistema Remoto')

ser_from = srl.sRemotoSerializers(api)
api = ser_from.add_serializers()


@ns.route('/ejecutar')
@ns.route('/ejecutar/<string:grupo>/<string:fecha_reporte>')
class SRReportAPI(Resource):

    def post(self, grupo: str = None, fecha_reporte: str = None):
        """ Ejecutar el reporte de sistema remoto para un especificado grupo """
        if fecha_reporte is None:
            fecha_reporte=dt.datetime.now()
        else:
            fecha_reporte=utils.valid_date(fecha_reporte)
        ini_time = fecha_reporte - dt.timedelta(days=1)
        if grupo is None:
            grupo="User"
        user_config_path = os.path.join(init.SREMOTO_REPO, "users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        mask = df_user["Grupo"] == grupo
        df_filter = df_user[mask]
        recipients = list(df_filter["Correo"])
        from_email=init.EMAIL_SREMOTO
        time_range_to_run=(ini_time, fecha_reporte)
        success,msg=run_process_for(time_range_to_run, recipients, from_email)
        return dict(success=success,msg=msg), 200 if success else 409


@ns.route('/prueba/<string:user_group>')
class PruebaReport(Resource):

    def post(self, user_group: str = "Grupo de usuarios"):
        """
        Mail de prueba
        """
        # leer archivo de excel con path
        user_config_path = os.path.join(init.SREMOTO_REPO, "users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        mask=df_user["Grupo"]==user_group
        df_filter=df_user[mask]
        users=list(df_filter["Correo"])
        success,msg=send_mail("Esta es una prueba","TEST",users,init.EMAIL_SREMOTO)
        return dict(success=success,msg=msg),200 if success else 409


