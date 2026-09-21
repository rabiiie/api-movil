"""Ruta GET /v1/yo/carpetas.

Devuelve las carpetas de OneDrive que AppFibra publico para quien llama.
"""

import json
import os

import boto3

# Fuera del handler a proposito: esto se ejecuta una vez por contenedor, no
# una vez por peticion. Abrir la conexion aqui es lo que hace que la segunda
# llamada sea mucho mas rapida que la primera.
TABLA = boto3.resource("dynamodb").Table(os.environ["TABLA_CARPETAS"])


def quien_llama(event):
    """Devuelve (oid, correo) del token validado por API Gateway.

    La funcion no comprueba el token ni lo descodifica: cuando el codigo se
    ejecuta, API Gateway ya verifico firma, emisor, audiencia y caducidad.
    Si algo de eso fallara, esta funcion no se habria ejecutado.

    Los claims llegan siempre como texto, incluso los numeros y las listas.
    """
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    return claims["oid"], claims.get("preferred_username", "")


def leer(persona):
    """Lee una fila por su clave. Devuelve None si no existe."""
    return TABLA.get_item(Key={"persona": persona}).get("Item")


def lambda_handler(event, context):
    oid, correo = quien_llama(event)

    # El correo no se escribe en los registros: CloudWatch los guarda 30 dias
    # y son datos personales. El oid identifica igual y no es un dato de
    # contacto.
    print(f"peticion {context.aws_request_id} de {oid}")

    # AppFibra publica por oid cuando OneDrive le da el id de Entra del
    # usuario. En los permisos que solo traen correo, publica por correo.
    fila = leer(oid)
    if fila is None and correo:
        fila = leer(correo.lower())

    if fila is None:
        # No es un error: es un tecnico sin carpetas asignadas todavia, o
        # que AppFibra aun no ha publicado. La app muestra la lista vacia.
        print(f"sin fila publicada para {oid}")
        return respuesta({"carpetas": [], "publicado": None})

    return respuesta(
        {
            "carpetas": fila.get("carpetas", []),
            "publicado": fila.get("publicado"),
        }
    )


def respuesta(cuerpo):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(cuerpo, ensure_ascii=False, default=str),
    }
