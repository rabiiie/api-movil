"""Ruta GET /v1/yo/carpetas.

Etapa 1: devuelve una lista fija. Todavia no hay token ni DynamoDB.
"""

import json
import os


def lambda_handler(event, context):
    """Punto de entrada. AWS llama a esta funcion por cada peticion.

    event: diccionario con la peticion. Para un HTTP API es el formato
        "payload 2.0": event["requestContext"]["http"]["method"] y ["path"],
        event["headers"], event["queryStringParameters"], event["body"].
        A partir de la etapa 3, el token validado llega en
        event["requestContext"]["authorizer"]["jwt"]["claims"].
    context: datos de la ejecucion. context.aws_request_id identifica esta
        llamada y sale en los registros de CloudWatch.
    """

    # print escribe en CloudWatch Logs. Es la forma de depurar una Lambda.
    print(f"peticion {context.aws_request_id} en entorno {os.environ.get('ENTORNO')}")

    # Etapa 4: aqui se consultara DynamoDB por el oid del tecnico.
    carpetas = [
        {"ruta": "DGF/Mitte/Obra 001", "nombre": "Obra 001"},
        {"ruta": "DGF/Mitte/Obra 002", "nombre": "Obra 002"},
    ]

    # La respuesta es un diccionario con estas tres claves. API Gateway lo
    # traduce a una respuesta HTTP. El cuerpo tiene que ser texto, no un
    # diccionario: de ahi json.dumps.
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps({"carpetas": carpetas}, ensure_ascii=False),
    }
