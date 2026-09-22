"""Escribe datos de prueba en las tablas de la app de KPI.

Hace a mano lo que hara AppFibra: dar acceso a una persona y publicar cifras.
Sirve para probar las rutas /direccion antes de activar la publicacion en
AppFibra.

Uso:
    python herramientas/publicar_direccion_prueba.py <oid o correo>
    python herramientas/publicar_direccion_prueba.py <oid o correo> --quitar

La primera forma da acceso a todo UGG y solo al proyecto P1 de DGF, y escribe
tres items: avance#UGG, avance#DGF#P1 y avance#DGF. Con --quitar borra la
fila de acceso, para ver el 403.

Lo que tiene que pasar despues, con herramientas/probar_token.py:
    /direccion/yo              200, los clientes de arriba
    /direccion/avance/UGG      200
    /direccion/avance/DGF/P1   200
    /direccion/avance/DGF      403: el item existe, pero suma proyectos que no son suyos
    /direccion/avance/GFPLUS   403: ese cliente no esta en su fila
"""

import datetime
import json
import sys

import boto3

PERFIL = "insyte"
REGION = "eu-central-1"
TABLA_RESUMEN = "direccion-resumen"
TABLA_ACCESO = "direccion-acceso"


def item(cliente, ambito, hp_por_dia):
    """Un item con la forma que publica AppFibra, con una sola fase."""
    ahora = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {
        "vista": f"avance#{cliente}" if ambito is None else f"avance#{cliente}#{ambito}",
        "cliente": cliente,
        "ambito": ambito,
        "tipo_ambito": "proyecto" if cliente == "DGF" else "ciudad",
        "activa": True,
        "fases": [{"key": "hp", "label": "Home Passed", "grano": "edificio",
                   "avance_por": "fecha", "total": sum(hp_por_dia.values())}],
        "dias": {"obra": {"hp": hp_por_dia}},
        "fuera_de_rango": {},
        "datos_de": ahora,
        "calculado": ahora,
        "prueba": True,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    persona = sys.argv[1].lower()
    sesion = boto3.Session(profile_name=PERFIL, region_name=REGION)
    acceso = sesion.resource("dynamodb").Table(TABLA_ACCESO)

    if "--quitar" in sys.argv:
        acceso.delete_item(Key={"persona": persona})
        print(f"quitado el acceso de {persona}")
        return

    resumen = sesion.resource("dynamodb").Table(TABLA_RESUMEN)
    items = [
        item("UGG", None, {"2026-09-21": 12, "2026-09-22": 9}),
        item("DGF", "P1", {"2026-09-22": 3}),
        item("DGF", None, {"2026-09-22": 40}),
    ]
    for i in items:
        # Igual que AppFibra: la clave como atributo y el resto como un JSON
        # en "datos", que la Lambda devuelve sin tocar.
        resumen.put_item(Item={"vista": i["vista"], "datos": json.dumps(i, ensure_ascii=False),
                               "publicado": i["calculado"]})
        print(f"escrito {i['vista']}")

    acceso.put_item(Item={
        "persona": persona,
        "clientes": {"UGG": ["*"], "DGF": ["P1"]},
        "publicado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })
    print(f"acceso para {persona}: UGG entero y DGF solo P1")


if __name__ == "__main__":
    main()
