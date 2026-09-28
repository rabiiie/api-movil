# api-movil

API en AWS entre AppFibra y las apps Android: FotosObra y la app de KPI ("direccion", la vista global de proyectos).

La decision y el porque estan en `docs/adr/ADR-019-api-movil-en-aws.md` del repositorio de AppFibra, con el diagrama en `docs/adr/diagramas/`.

## 1. Las tres piezas

| Pieza | Que es | Que cuesta |
|---|---|---|
| API Gateway (HTTP API) | La URL publica. Recibe la peticion, comprueba el token y la pasa a Lambda | ~1 $ por millon de peticiones, sin coste fijo |
| Lambda | El codigo. AWS lo arranca cuando llega una peticion y lo apaga despues | 1 M de peticiones al mes gratis, siempre |
| DynamoDB | La tabla donde AppFibra deja los datos publicados. Llega en la etapa 4 | 25 GB gratis, siempre |

No hay ningun servidor encendido. Si nadie llama a la API, la factura es cero.

## 2. Ficheros

| Fichero | Que hace |
|---|---|
| `template.yaml` | Describe la infraestructura entera: la URL, la funcion y la ruta. Es el fichero importante |
| `src/carpetas/app.py` | El codigo que responde a `GET /v1/yo/carpetas` |
| `src/carpetas/requirements.txt` | Librerias de esa funcion |
| `src/direccion/app.py` | Las rutas `/v1/direccion/...` de la app de KPI, con la comprobacion de acceso |
| `herramientas/publicar_direccion_prueba.py` | Da acceso a una persona y escribe cifras de prueba, sin AppFibra |
| `events/get-carpetas.json` | Una peticion de ejemplo, para invocar la funcion en local sin levantar nada |
| `samconfig.toml` | Lo crea `sam deploy --guided`: region, nombre de la pila |

SAM (Serverless Application Model) es la herramienta de AWS para esto. `template.yaml` en formato SAM son 60 lineas; lo mismo en CloudFormation puro son varios cientos. SAM lo traduce al desplegar.

## 3. Lo que hace falta instalar

```powershell
winget install Amazon.AWSCLI
winget install Amazon.SAM-CLI
```

Cierra y abre PowerShell despues, y comprueba:

```powershell
aws --version
sam --version
docker --version
```

Docker hace falta solo para ejecutar en local: SAM levanta la Lambda dentro de un contenedor igual al de AWS.

## 4. Ejecutar en local

Invocar la funcion una vez con la peticion de ejemplo:

```powershell
sam build
sam local invoke CarpetasFunction --event events/get-carpetas.json
```

Levantar la API entera en el puerto 3000 y llamarla con el navegador o con curl:

```powershell
sam local start-api
```

```powershell
curl http://127.0.0.1:3000/yo/carpetas
```

`sam local start-api` no aplica el `StageName`, por eso en local la ruta es `/yo/carpetas` y en AWS sera `/v1/yo/carpetas`.

## 5. Desplegar

La primera vez se hizo con `sam deploy --guided`, que dejo las respuestas en `samconfig.toml`. A partir de ahi:

```powershell
sam build
sam deploy --profile insyte
```

Ver la URL de la pila desplegada:

```powershell
sam list stack-outputs --stack-name api-movil --region eu-central-1 --profile insyte
```

El identificador del API lo genera AWS al crearlo. Si se borra la pila y se vuelve a crear, la URL cambia: no se escribe en el codigo de las apps.

La pila tiene **proteccion de terminacion activada**: `sam delete` y el boton de borrar de la consola fallan hasta quitarla a proposito.

```powershell
aws cloudformation update-termination-protection --stack-name api-movil --no-enable-termination-protection --region eu-central-1 --profile insyte
```

Borrar todo lo desplegado:

```powershell
sam delete --stack-name api-movil --region eu-central-1 --profile insyte
```

## 6. Etapas

| Etapa | Que se hace | Estado |
|---|---|---|
| 0 | Aviso de presupuesto en AWS, instalar AWS CLI y SAM CLI | pendiente |
| 1 | Este proyecto: una ruta que responde en local | hecha |
| 2 | Desplegarlo en `eu-central-1` y llamarlo desde internet | hecha |
| 3 | Registrar la API en Entra ID y exigir el token (autorizador JWT) | hecha |
| 4 | DynamoDB: la tabla de carpetas por tecnico | hecha |
| 5 | AppFibra publica en esa tabla con un usuario IAM | |
| 6 | FotosObra lee la API en vez de `carpetas.json` | |
| 7 | Registros, alarmas, limites de peticiones, despliegue reproducible | hecha |
| D1c | App de KPI: tablas `direccion-resumen` y `direccion-acceso`, rutas `/v1/direccion/...` | hecha |

PhotoDoc usa la misma cuenta de AWS pero trabaja en `us-west-2`. Esta API va en `eu-central-1` (Frankfurt): los datos de los tecnicos no salen de la UE.

## 7. Controles de produccion

| Control | Valor | Por que |
|---|---|---|
| Limite de peticiones | 20 por segundo, rafaga 50 | Techo para toda la API. Por encima responde 429 |
| Retencion de registros | 30 dias | Los registros llevan el `oid` del tecnico: son datos personales |
| Alarma `api-movil-errores-lambda` | 1 error en 5 min | Con este volumen un error no es ruido |
| Alarma `api-movil-5xx` | 1 en 5 min | Algo roto entre API Gateway y la funcion |
| Alarma `api-movil-trafico` | 2000 peticiones en 5 min | Un bucle o alguien probando, no uso normal |
| Etiqueta | `proyecto=fotosobra-api` | Para un presupuesto de AWS filtrado por esta API |
| Version minima de la app | `FotosObraVersionMinima`, `KpiVersionMinima` (0 = sin comprobar) | La app manda su `versionCode` en `X-App-Version`; por debajo de la minima la ruta responde 426 sin leer nada |

Las alarmas avisan al tema SNS `api-movil-avisos`. El correo tiene que **confirmar la suscripcion** pulsando el enlace que manda AWS la primera vez; hasta entonces no llega nada.

Cambiar el destinatario sin tocar el fichero:

```powershell
sam deploy --profile insyte --parameter-overrides CorreoAvisos=otro@insytedeutschland.de
```

Subir la version minima de FotosObra cuando una version nueva deja atras a las anteriores (un cambio de la API, un fallo de seguridad). Las apps por debajo reciben `426 {"error": "version_antigua", "minima": N}` y piden actualizar:

```powershell
sam deploy --profile insyte --parameter-overrides FotosObraVersionMinima=10
```

## 8. Ejercicios

Cinco pruebas sobre lo desplegado. Cada una enseña una cosa y ninguna cuesta dinero.

### 1. Donde van los print

En una ventana de PowerShell:

```powershell
sam logs --stack-name api-movil --name CarpetasFunction --region eu-central-1 --profile insyte --tail
```

Se queda esperando. En otra ventana, llama a la URL. La linea `peticion <id> en entorno desarrollo` aparece en la primera ventana.

`print` en una Lambda escribe en CloudWatch Logs. Es la unica forma de ver que pasa dentro: no hay consola ni fichero de log en disco.

### 2. El arranque en frio

Con `--tail` puesto, llama dos veces seguidas y compara las lineas `REPORT`.

La primera trae `Init Duration`: AWS tuvo que levantar el contenedor. La segunda no, porque reutiliza el que ya esta caliente. Despues de unos minutos sin trafico lo apaga y la siguiente vuelve a arrancar en frio.

`Init Duration` no se cobra. `Duration` si.

### 3. Una ruta que no existe

```powershell
curl.exe -i https://<base>/v1/yo/inventada
```

Devuelve `404 Not Found`, y en los registros no aparece nada.

API Gateway decide antes de invocar la funcion. Una peticion a una ruta que no existe no ejecuta codigo y no se cobra. Lo mismo hara con un token invalido a partir de la etapa 3.

### 4. Que manda API Gateway a la funcion

La ruta `/v1/yo/eco` devolvia el `event` entero. Se uso para ver donde llegan
los claims del token validado (`requestContext.authorizer.jwt.claims`) y se
borro al terminar la etapa 3: devolver las cabeceras es devolver el token de
quien llama.

Para ver lo mismo sin exponer nada, `herramientas/probar_token.py` imprime los
claims leidos del token en el propio portatil.

### 5. Que ve el cliente cuando el codigo falla

Anadir temporalmente en `src/carpetas/app.py`, como primera linea de la funcion:

```python
raise ValueError("prueba")
```

Desplegar y llamar. El cliente recibe `500 Internal Server Error` con un cuerpo vacio; el traceback completo esta en CloudWatch.

Es lo correcto: el error no se le cuenta a quien llama. Por eso hace falta Sentry o las alarmas de CloudWatch, o los fallos pasan desapercibidos.

Deshacer el cambio y volver a desplegar al terminar.

## 9. La tabla

`fotosobra-carpetas`, clave `persona`, una fila por tecnico:

```json
{
  "persona": "1fb3462a-...",
  "carpetas": [
    {"ruta": "DGF/Mitte/Frankfurt/Obra 001", "nombre": "Obra 001",
     "subcontrata": "Trenching 21", "proyecto": "DGF Mitte"}
  ],
  "publicado": "2026-09-21T11:15:44+00:00"
}
```

La lista va dentro de la fila: siempre se leen juntas. La Lambda busca por
`oid` y, si no hay fila, por `preferred_username` en minusculas, porque
algunos permisos de OneDrive solo traen el correo.

Una persona sin fila no es un error: devuelve `carpetas: []` y `publicado: null`.

El rol de la Lambda solo tiene `dynamodb:GetItem` sobre el ARN de esta tabla.
No puede hacer `Scan`, ni escribir, ni tocar otra tabla.

Sin copias de seguridad a proposito: es una copia de datos que estan en
AppFibra y que el trabajo de publicacion reconstruye. El cifrado en reposo va
de serie.

Escribir una fila de prueba, que es lo que hara AppFibra en la etapa 5:

```powershell
python herramientas/publicar_prueba.py <oid o correo>
```

## 10. Como probar la API

```powershell
pip install msal
python herramientas/probar_token.py            # GET /v1/yo/carpetas
python herramientas/probar_token.py /yo/tareas # otra ruta
```

Pide un token a Entra ID con el flujo de codigo de dispositivo, imprime los
claims (nunca el token) y llama a la API con el.

Sin token, cualquier ruta devuelve 401 y la Lambda no se ejecuta: el rechazo
ocurre en API Gateway.

Medido el 21.09.2026 con un token real:

| Claim | Valor | Para que sirve |
|---|---|---|
| `iss` | `https://login.microsoftonline.com/<tid>/v2.0` | Exige `requestedAccessTokenVersion: 2` en el manifiesto |
| `aud` | el GUID del registro, sin `api://` | Los tokens v2 usan el GUID; el `api://` es de los v1 |
| `oid` | id del usuario en el inquilino | Con este se decide que devolver. Estable entre aplicaciones |
| `sub` | distinto por aplicacion | No sirve para identificar entre sistemas |
| `idp` | inquilino que autentico de verdad | Distinto del `tid` cuando la cuenta es invitada |
| `roles` | ausente | No se usa: el acceso a la app de KPI lo decide AppFibra en `direccion-acceso` |

Los claims llegan siempre como texto, tambien `exp` e `iat`.

## 11. La app de KPI (etapa D1c)

Tres rutas, una funcion:

| Ruta | Devuelve |
|---|---|
| `GET /v1/direccion/yo` | Los clientes que puede ver quien llama y, de cada uno, `*` o su lista de ciudades o proyectos |
| `GET /v1/direccion/avance/{cliente}` | El item del cliente entero. Solo con `*` en ese cliente |
| `GET /v1/direccion/avance/{cliente}/{ambito}` | Una ciudad o un proyecto. Con `*` o si esta en su lista |

**El token no basta.** El autorizador acepta cualquier token del tenant de
INSYTE, y ese token lo tienen tambien los tecnicos de las subcontratas que usan
FotosObra. Por eso la funcion busca a la persona en `direccion-acceso` en cada
peticion, antes de leer ninguna cifra, y sin fila responde 403. Quien escribe
esa tabla es AppFibra, con sus permisos de Keycloak: quitar el acceso alli lo
quita aqui en la siguiente publicacion.

**El total de un cliente es informacion.** Quien solo tiene algunas ciudades
no puede pedir el item del cliente: suma tambien las ciudades que no son suyas.
La app suma las suyas en el movil.

Probar despues de desplegar:

```powershell
python herramientas/probar_token.py /direccion/yo                # 403: aun no tienes fila
python herramientas/publicar_direccion_prueba.py <tu oid>
python herramientas/probar_token.py /direccion/yo                # 200
python herramientas/probar_token.py /direccion/avance/UGG        # 200
python herramientas/probar_token.py /direccion/avance/DGF/P1     # 200
python herramientas/probar_token.py /direccion/avance/DGF        # 403: solo tienes P1
python herramientas/probar_token.py /direccion/avance/GFPLUS     # 403
python herramientas/publicar_direccion_prueba.py <tu oid> --quitar
python herramientas/probar_token.py /direccion/yo                # 403 otra vez
```
