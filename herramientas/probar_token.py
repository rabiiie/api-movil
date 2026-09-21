"""Pide un token a Entra ID y llama a la API con el.

Hace lo mismo que hara la app Android, pero en 40 lineas y desde el portatil.
Usa el flujo de codigo de dispositivo: el script no abre navegador, da un
codigo y se inicia sesion en otro sitio. Es el flujo de las teles y las
consolas, y sirve para probar sin montar una app.

Uso:
    pip install msal
    python herramientas/probar_token.py

El token no se imprime nunca: solo lo que lleva dentro.
"""

import base64
import datetime
import json
import sys
import urllib.error
import urllib.request

import msal

TENANT = "68c7939c-d7c1-4a03-86b4-827f15fcd06d"
# El registro de la app, el que pide. El mismo que usa FotosObra.
CLIENTE = "b84892a2-8f14-420e-848e-847ef6750cad"
# El ambito de la API, el registro al que se le pide.
AMBITO = "api://78d4dbf7-fb0e-4677-9c1e-95f046dddbff/Fotos.Acceso"
BASE = "https://49fk8zzcz7.execute-api.eu-central-1.amazonaws.com/v1"
# Ruta por defecto. Se cambia por argumento: probar_token.py /yo/eco
RUTA = sys.argv[1] if len(sys.argv) > 1 else "/yo/carpetas"

CLAIMS = ["iss", "aud", "tid", "oid", "preferred_username", "name", "scp", "appid", "azp", "roles"]


def partes(token):
    """Un JWT son tres trozos separados por puntos: cabecera.datos.firma.

    Los dos primeros son JSON en base64, legibles por cualquiera. Lo que
    protege el token no es que sea ilegible, es que la firma no se puede
    falsificar sin la clave privada de Microsoft.
    """
    datos = token.split(".")[1]
    # base64 de URL sin relleno: hay que devolverle los "=" que le faltan.
    datos += "=" * (-len(datos) % 4)
    return json.loads(base64.urlsafe_b64decode(datos))


def main():
    app = msal.PublicClientApplication(
        CLIENTE, authority=f"https://login.microsoftonline.com/{TENANT}"
    )

    flujo = app.initiate_device_flow(scopes=[AMBITO])
    if "user_code" not in flujo:
        print("Entra ID no acepto el flujo de dispositivo:")
        print(json.dumps(flujo, indent=2))
        return

    print(flujo["message"])
    print("\nEsperando...")
    resultado = app.acquire_token_by_device_flow(flujo)

    if "access_token" not in resultado:
        print(f"\nNo hubo token: {resultado.get('error')}")
        print(resultado.get("error_description", ""))
        return

    token = resultado["access_token"]
    datos = partes(token)

    print("\n--- lo que lleva el token ---")
    for clave in CLAIMS:
        if clave in datos:
            print(f"{clave:20} {datos[clave]}")
    caduca = datetime.datetime.fromtimestamp(datos["exp"])
    print(f"{'exp':20} {caduca:%H:%M:%S} ({int(datos['exp'] - datos['iat']) // 60} min de vida)")

    url = BASE + RUTA
    print(f"\n--- llamando a {url} ---")
    peticion = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(peticion) as r:
            print(f"HTTP {r.status}")
            print(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode("utf-8"))


if __name__ == "__main__":
    main()
