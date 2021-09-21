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

from flask_restplus import Resource
from flask import request, send_from_directory
import re
# importando configuraciones iniciales
from flask_app.my_lib.utils import set_max_age_to_response
from flask_app.api.services.restplus_config import api
from flask_app.api.services.sRemoto import serializers as srl
from flask_app.api.services.sRemoto import parsers
# importando clases para leer desde MongoDB
from random import randint

# configurando logger y el servicio web, para ejecutar Reporte de Sistema Remoto
ns = api.namespace('exec-sRemoto', description='Ejecutar reporte de Sistema Remoto')

ser_from = srl.sRemotoSerializers(api)
api = ser_from.add_serializers()

@ns.route('/ejecutar')
@ns.route('/ejecutar/<string:fecha_inicio>/<string:fecha_fin>')
class SRReportAPI(Resource):

    def post(self, fecha_inicio: str = "fecha_inicio", fecha_fin: str = "fecha_fin"):
        """ Ejecuta el reporte de sistema remoto """
        pass


@ns.route('/nodo/id/<string:id_nodo>/activado')
class SRNodeAPIActivated(Resource):

    def put(self, id_nodo: str = "ID del nodo a cambiar"):
        """
        Activa el nodo
        """
        pass

@ns.route('/nodo/id/<string:id_nodo>/desactivado')
class SRNodeAPIDeactivated(Resource):

    def put(self, id_nodo: str = "ID del nodo a cambiar"):
        """
        Desactiva el nodo
        """
        pass


@ns.route('/nodo/<string:tipo>/<string:nombre>/<string:entidad_tipo>/<string:entidad_nombre>')
class SREntidadAPI(Resource):
    def get(self, tipo: str = "Tipo nodo", nombre: str = "Nombre nodo", entidad_tipo: str = "Entidad tipo",
            entidad_nombre: str = "Entidad nombre"):
        """ Retorna las entidades de un nodo """
        pass

#
# @ns.route('/rtu/<string:id_nodo>/<string:id_entidad>')
# class SRRTUSAPI(Resource):
#
#     def get(self, id_nodo: str = "id nodo", id_entidad: str = "id entidad"):
#         """ Regresa la lista de RTU de una entidad
#             Id nodo: id único del nodo
#             Id entidad: id único de la entidad
#             <b>404</b> Si el nodo o la entidad no existe
#         """
#         pass
#
#     @api.expect(ser_from.rtu)
#     def post(self, id_nodo: str = "id nodo", id_entidad: str = "id entidad"):
#         """ Ingresa una nueva RTU en una entidad si esta no existe, caso contrario la edita
#             Id nodo: id único del nodo
#             Id entidad: id único de la entidad
#             <b>404</b> Si el nodo o la entidad no existe
#         """
#         pass
#
#     @api.expect(ser_from.rtu_id)
#     def delete(self, id_nodo: str = "id nodo", id_entidad: str = "id entidad"):
#         """ Elimina una RTU en una entidad
#             Id nodo: id único del nodo
#             Id entidad: id único de la entidad
#             <b>404</b> Si el nodo o la entidad no existe
#         """
#         pass
#
#
# @ns.route('/rtu/<string:id_nodo>/<string:id_entidad>/<string:id_utr>')
# class SRRTUAPI(Resource):
#
#     @staticmethod
#     def get(id_nodo: str = "id nodo", id_entidad: str = "id entidad", id_utr: str = "id UTR"):
#         """ Regresa la cofiguración de la RTU
#             Id nodo: id único del nodo
#             Id entidad: id único de la entidad
#             Id utr: id único de la entidad
#             <b>404</b> Si el nodo, la entidad o UTR no existe
#         """
#         pass


