"""Rutas de la app de KPI (ADR-019, apartado 3.7).

GET /v1/direccion/yo                         que puede ver quien llama
GET /v1/direccion/avance/{cliente}           el cliente entero
GET /v1/direccion/avance/{cliente}/{ambito}  una ciudad o un proyecto

El token de Entra dice quien es la persona, no que puede ver: lo tiene
cualquiera del tenant, tambien los tecnicos de las subcontratas. Lo que puede
ver lo decide AppFibra y lo deja en la tabla de acceso. Esta funcion lo mira
en cada peticion, antes de leer ninguna cifra.
"""

import json
import os
from urllib.parse import unquote

import boto3

_dynamo = boto3.resource("dynamodb")
RESUMEN = _dynamo.Table(os.environ["TABLA_RESUMEN"])
ACCESO = _dynamo.Table(os.environ["TABLA_ACCESO"])

# En la fila de acceso, "todo lo de ese cliente".
TODO = "*"

# La version mas antigua de la app que acepta esta ruta, en versionCode de
# Android. La app la manda en cada peticion en la cabecera X-App-Version.
# Con 0 no se comprueba nada.
VERSION_MINIMA = int(os.environ.get("VERSION_MINIMA", "0"))


def version_de_la_app(event):
    """El versionCode de la cabecera X-App-Version, o 0 si falta o no es un numero.

    API Gateway (HTTP API) entrega las cabeceras en minusculas.
    """
    valor = (event.get("headers") or {}).get("x-app-version", "").strip()
    return int(valor) if valor.isdigit() else 0


def claves(event):
    """Claves con las que buscar a la persona, de la mas fiable a la menos.

    La misma busqueda que carpetas/app.py: el oid primero y despues las
    formas del correo, deshaciendo la de los invitados
    ("ana_subco.de#EXT#@insyte.onmicrosoft.com" -> "ana@subco.de").
    Las dos funciones se empaquetan por separado, por eso esta copiada.
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

    return list(dict.fromkeys(candidatas))


def buscar_acceso(posibles):
    """La fila de acceso de la persona, o None si AppFibra no le ha dado acceso."""
    for i, clave in enumerate(posibles):
        fila = ACCESO.get_item(Key={"persona": clave}).get("Item")
        if fila is not None:
            print(f"acceso encontrado por la clave {i} de {len(posibles)}")
            return fila
    return None


def puede_ver(acceso, cliente, ambito=None):
    """True si la fila de acceso deja ver ese cliente, o esa ciudad o proyecto.

    El cliente entero solo con "*": su item suma todas las ciudades, y quien
    solo tiene algunas no debe ver el total de las demas. Una ciudad, con "*"
    o si esta en su lista, escrita igual: la app toma los nombres de la lista
    "ambitos" que publica AppFibra, asi que no se normalizan aqui (Python
    convierte "ß" en "SS" y Postgres no).
    """
    permitidos = acceso.get("clientes", {}).get(cliente)
    if not permitidos:
        return False
    if TODO in permitidos:
        return True
    return ambito is not None and ambito in permitidos


def lambda_handler(event, context):
    posibles = claves(event)
    ruta = event["routeKey"]
    # El oid y la ruta, nunca el correo: los registros se guardan 30 dias.
    print(f"peticion {context.aws_request_id} de {posibles[0]} a {ruta}")

    # Una app vieja no llega a leer nada. 426 (Upgrade Required) es la forma
    # de decirle que tiene que actualizarse; "minima" le dice a cual.
    version = version_de_la_app(event)
    if version < VERSION_MINIMA:
        print(f"version {version} por debajo de la minima {VERSION_MINIMA}")
        return respuesta(426, {"error": "version_antigua", "minima": VERSION_MINIMA})

    acceso = buscar_acceso(posibles)
    if acceso is None:
        # A diferencia de carpetas, aqui no se responde con una lista vacia:
        # quien no esta en la tabla no es usuario de esta app.
        return respuesta(403, {"error": "sin_acceso"})

    if ruta == "GET /direccion/yo":
        return respuesta(200, {
            "clientes": acceso.get("clientes", {}),
            "publicado": acceso.get("publicado"),
        })

    # Un ambito con caracteres especiales viaja codificado en la URL:
    # "#ERROR" es /avance/DGF/%23ERROR. unquote lo deja como "#ERROR", y
    # sobre un valor que ya llega decodificado no cambia nada.
    parametros = event.get("pathParameters") or {}
    cliente = parametros.get("cliente", "").upper()
    ambito = parametros.get("ambito")
    if ambito is not None:
        ambito = unquote(ambito)

    if not puede_ver(acceso, cliente, ambito):
        return respuesta(403, {"error": "fuera_de_su_alcance"})

    vista = f"avance#{cliente}" if ambito is None else f"avance#{cliente}#{ambito}"
    fila = RESUMEN.get_item(Key={"vista": vista}).get("Item")
    if fila is None:
        return respuesta(404, {"error": "sin_datos"})

    # "datos" ya es el JSON que escribio AppFibra: se devuelve sin tocarlo.
    return respuesta(200, fila["datos"])


def respuesta(estado, cuerpo):
    return {
        "statusCode": estado,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo, ensure_ascii=False, default=str),
    }
