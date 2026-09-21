"""Ruta GET /v1/yo/eco. Devuelve la peticion tal y como llega.

Sirve para ver que manda API Gateway a la funcion. En la etapa 3, los datos
del token validado apareceran en este mismo diccionario, en
event["requestContext"]["authorizer"]["jwt"]["claims"].

Esta ruta se borra al terminar la etapa 3: devolver las cabeceras significa
devolver el token de quien llama.
"""

import json


def lambda_handler(event, context):
    # default=str evita que un valor no serializable rompa la respuesta.
    cuerpo = json.dumps(event, indent=2, ensure_ascii=False, default=str)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": cuerpo,
    }
