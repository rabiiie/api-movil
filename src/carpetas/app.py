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


def claves(event):
    """Claves con las que buscar la fila, de la mas fiable a la menos.

    AppFibra publica por el id de Entra cuando el permiso de OneDrive lo trae,
    y por el correo en minusculas cuando no. Medido el 22.09.2026: de 273
    personas, 140 solo tienen correo, asi que esta lista no es un caso raro.

    Un invitado de otro dominio no siempre trae su correo tal cual. Entra ID
    usa la forma "ana_subco.de#EXT#@insyte.onmicrosoft.com", que no coincide
    con el "ana@subco.de" que ve OneDrive. Se deshace esa forma: lo de delante
    del #EXT# con el ultimo guion bajo convertido en arroba.
    """
    c = event["requestContext"]["authorizer"]["jwt"]["claims"]
    candidatas = [c["oid"]]

    for clave in ("preferred_username", "email", "upn", "unique_name"):
        valor = (c.get(clave) or "").strip().lower()
        if not valor:
            continue
        candidatas.append(valor)
        if "#ext#" in valor:
            local = valor.split("#ext#")[0]
            if "_" in local:
                candidatas.append("@".join(local.rsplit("_", 1)))

    # Sin duplicados y conservando el orden.
    return list(dict.fromkeys(candidatas))


def leer(persona):
    """Lee una fila por su clave. Devuelve None si no existe."""
    return TABLA.get_item(Key={"persona": persona}).get("Item")


def lambda_handler(event, context):
    posibles = claves(event)
    oid = posibles[0]

    # Los correos no se escriben en los registros: CloudWatch los guarda 30
    # dias y son datos personales. El oid identifica igual y no es un dato de
    # contacto.
    print(f"peticion {context.aws_request_id} de {oid}")

    fila = None
    for i, clave in enumerate(posibles):
        fila = leer(clave)
        if fila is not None:
            # Con que clave se encontro, sin decir cual: 0 es el oid y el
            # resto son formas del correo. Sirve para saber cuanta gente
            # depende del correo sin registrar el correo.
            print(f"fila encontrada por la clave {i} de {len(posibles)}")
            break

    if fila is None:
        # No es un error: es un tecnico sin carpetas asignadas todavia, o que
        # AppFibra aun no ha publicado, o cuyo correo no coincide. La app
        # muestra la lista vacia.
        print(f"sin fila para {oid}, probadas {len(posibles)} claves")
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
