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
import uuid

from flask_app.api.services.sRemoto.endpoints import *
from flask_restplus import Resource
from flask import request, send_from_directory
import re
# importando configuraciones iniciales
from flask_app.api.services.restplus_config import api
from flask_app.api.services.sRemoto import serializers as srl
from flask_app.api.services.sRemoto import parsers
# importando clases para leer desde MongoDB
from random import randint


# configurando logger y el servicio web, para administrar Reporte de Sistema Remoto
ns = api.namespace('admin-sRemoto', description='Administración de reporte de Sistema Remoto')

ser_from = srl.sRemotoSerializers(api)
api = ser_from.add_serializers()


@ns.route('/user/<string:grupo>/<string:nombre>/<string:correo_electronico>')
class ReportUser(Resource):

    def post(self, grupo: str = "Grupo de Usuario", nombre: str = "Nombre del usuario", correo_electronico: str =
    "Correo electronico"):
        """Crea un usuario de reporte """
        #leer archivo de excel con path
        user_config_path=os.path.join(init.SREMOTO_REPO,"users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        id = uuid.uuid4()
        user=dict(ID=id,Grupo=grupo,Usuario=nombre,Correo=correo_electronico,Activado=True)
        df_user=df_user.append(user,ignore_index=True)
        df_user.set_index(keys=["ID"],inplace=True)
        df_user.to_excel(user_config_path)
        return dict(success=True,msg="Usuario Creado")

@ns.route('/user/<string:id>/<string:grupo>/<string:nombre>/<string:correo_electronico>')
class ReportUserEdit(Resource):

    def put(self,id:str="ID", grupo: str = "Grupo de Usuario", nombre: str = "Nombre del usuario", correo_electronico: str=
            "Correo electronico"):
        """Edita un usuario de reporte por ID """
        # leer archivo de excel con path
        user_config_path = os.path.join(init.SREMOTO_REPO, "users.xlsx")
        df_user = pd.read_excel(user_config_path,index_col="ID")
        if not id in df_user.index:
            return dict(success=False,msg="Usuario no encontrado"),404
        user=df_user.loc[id]
        user["Grupo"]=grupo
        user["Usuario"] = nombre
        user["Correo"] = correo_electronico
        df_user.loc[id]=user
        df_user.to_excel(user_config_path)
        return dict(success=True, msg="Usuario Editado")

@ns.route('/user/<string:id>')
class ReportUserDelete(Resource):

    def delete(self, id: str = "ID"):
        """Borra un usuario de reporte """
        # leer archivo de excel con path
        user_config_path = os.path.join(init.SREMOTO_REPO, "users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        if not id in df_user.index:
            return dict(success=False, msg="Usuario no encontrado"), 404
        df_user.drop(index=id,axis="index",inplace=True)
        df_user.to_excel(user_config_path)
        return dict(success=True, msg="Usuario Editado")

@ns.route('/config-utr-excel')
class ConfigUTR(Resource):

    def post(self):
        """
        Configuracion total/ Reemplazo total de configuracion
        """
        pass

    def put(self):
        """
        Editar/Añadir
        """
        pass

    def get(self):
        """
        Obtener configuracion actual
        """
        pass

@ns.route('/users')
class Users(Resource):

    def get(self):
        """
        Obtiene los usuarios
        """
        #leer archivo de excel con path
        user_config_path=os.path.join(init.SREMOTO_REPO,"users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        users=df_user.to_dict(orient="records")
        return dict(success=True,msg="Usuarios encontrados",users=users)

@ns.route('/user/<string:id>/active')
class ActiveUser(Resource):

    def post(self, id: str = "ID"):
        """Activa usuario"""
        # leer archivo de excel con path
        user_config_path = os.path.join(init.SREMOTO_REPO, "users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        if not id in df_user.index:
            return dict(success=False, msg="Usuario no encontrado"), 404
        user = df_user.loc[id]
        user["Activado"] = True
        df_user.loc[id] = user
        df_user.to_excel(user_config_path)
        return dict(success=True, msg="Usuario Activado")

@ns.route('/user/<string:id>/desactive')
class ActiveUser(Resource):

    def post(self, id: str = "ID"):
        """Desactiva usuario"""
        # leer archivo de excel con path
        user_config_path = os.path.join(init.SREMOTO_REPO, "users.xlsx")
        df_user = pd.read_excel(user_config_path, index_col="ID")
        if not id in df_user.index:
            return dict(success=False, msg="Usuario no encontrado"), 404
        user = df_user.loc[id]
        user["Activado"] = False
        df_user.loc[id] = user
        df_user.to_excel(user_config_path)
        return dict(success=True, msg="Usuario Desactivado")

# @ns.route('/nodo/id/<string:id_nodo>/desactivado')
# class SRNodeAPIDeactivated(Resource):
#
#     def put(self, id_nodo: str = "ID del nodo a cambiar"):
#         """
#         Desactiva el nodo
#         """
#         pass
#
#
# @ns.route('/nodo/<string:tipo>/<string:nombre>/<string:entidad_tipo>/<string:entidad_nombre>')
# class SREntidadAPI(Resource):
#     def get(self, tipo: str = "Tipo nodo", nombre: str = "Nombre nodo", entidad_tipo: str = "Entidad tipo",
#             entidad_nombre: str = "Entidad nombre"):
#         """ Retorna las entidades de un nodo """
#         pass
#
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


