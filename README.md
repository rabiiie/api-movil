# api-movil

API en AWS entre AppFibra y las apps Android (FotosObra y, mas adelante, la app de direccion).

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
| 4 | DynamoDB: la tabla de carpetas por tecnico | |
| 5 | AppFibra publica en esa tabla con un usuario IAM | |
| 6 | FotosObra lee la API en vez de `carpetas.json` | |
| 7 | Registros, alarmas, limites de peticiones, despliegue reproducible | |

PhotoDoc usa la misma cuenta de AWS pero trabaja en `us-west-2`. Esta API va en `eu-central-1` (Frankfurt): los datos de los tecnicos no salen de la UE.

## 7. Ejercicios

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

## 8. Como probar la API

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
| `roles` | ausente | Aqui llegara `Direccion` cuando exista la app de direccion |

Los claims llegan siempre como texto, tambien `exp` e `iat`.
