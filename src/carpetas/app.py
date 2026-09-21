"""Ruta GET /v1/yo/carpetas.

Etapa 3: identifica a quien llama por el token. La lista sigue siendo fija;
en la etapa 4 saldra de DynamoDB.
"""

import json


def quien_llama(event):
    """Devuelve (oid, correo) del token validado por API Gateway.

    La funcion no comprueba el token ni lo descodifica: cuando el codigo se
    ejecuta, API Gateway ya verifico firma, emisor, audiencia y caducidad.
    Si algo de eso fallara, esta funcion no se habria ejecutado.

    Los claims llegan siempre como texto, incluso los numeros y las listas.
    """
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    return claims["oid"], claims.get("preferred_username", "")


def lambda_handler(event, context):
    oid, correo = quien_llama(event)

    # El correo no se escribe en los registros: CloudWatch los guarda 30 dias
    # y son datos personales. El oid identifica igual y no es un dato de
    # contacto.
    print(f"peticion {context.aws_request_id} de {oid}")

    # Etapa 4: consulta a DynamoDB por ese oid.
    carpetas = [
        {"ruta": "DGF/Mitte/Obra 001", "nombre": "Obra 001"},
        {"ruta": "DGF/Mitte/Obra 002", "nombre": "Obra 002"},
    ]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(
            {"usuario": correo, "oid": oid, "carpetas": carpetas}, ensure_ascii=False
        ),
    }
