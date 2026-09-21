"""Escribe una fila de prueba en fotosobra-carpetas.

Hace a mano lo que hara AppFibra en la etapa 5: dejar en la tabla las
carpetas de una persona. Sirve para probar la ruta antes de tocar AppFibra.

Uso:
    python herramientas/publicar_prueba.py <oid o correo>

El oid sale de herramientas/probar_token.py.
"""

import datetime
import sys

import boto3

PERFIL = "insyte"
REGION = "eu-central-1"
TABLA = "fotosobra-carpetas"

CARPETAS = [
    {
        "ruta": "DGF/Mitte/Frankfurt/Obra 001",
        "nombre": "Obra 001",
        "subcontrata": "Trenching 21",
        "proyecto": "DGF Mitte",
    },
    {
        "ruta": "DGF/Mitte/Frankfurt/Obra 002",
        "nombre": "Obra 002",
        "subcontrata": "Trenching 21",
        "proyecto": "DGF Mitte",
    },
    {
        "ruta": "GFPLUS/Kassel/Obra 114",
        "nombre": "Obra 114",
        "subcontrata": "Trenching 21",
        "proyecto": "GF+ Kassel",
    },
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    persona = sys.argv[1].lower()
    sesion = boto3.Session(profile_name=PERFIL, region_name=REGION)
    tabla = sesion.resource("dynamodb").Table(TABLA)

    fila = {
        "persona": persona,
        "carpetas": CARPETAS,
        "publicado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }

    # put_item reemplaza la fila entera si ya existe. Es lo que quiere
    # AppFibra: cada ejecucion reescribe la lista completa de esa persona.
    tabla.put_item(Item=fila)
    print(f"escritas {len(CARPETAS)} carpetas para {persona}")


if __name__ == "__main__":
    main()
