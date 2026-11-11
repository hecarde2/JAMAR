# Asistente de IA Omnicanal - Muebles Jamar

Asistente conversacional para Muebles Jamar que unifica un widget web, una Mini App de Telegram, un bot de Telegram y una API REST. Permite recomendar productos según inventario real, analizar fotografías de espacios, consultar el perfil Customer 360 y simular o pre-aprobar crédito CrediJamar.

El proyecto está preparado para funcionar de inmediato en modo demostración, sin credenciales externas. Al configurar Snowflake, Google Gemini y Telegram se habilitan las integraciones reales.

## Contenido

- [Características principales](#características-principales)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos previos](#requisitos-previos)
- [Inicio rápido con Docker](#inicio-rápido-con-docker)
- [Configuración del entorno](#configuración-del-entorno)
- [Configurar Google Gemini](#configurar-google-gemini)
- [Configurar Telegram](#configurar-telegram)
- [Integración con Snowflake](#integración-con-snowflake)
- [Uso del frontend y del widget](#uso-del-frontend-y-del-widget)
- [Comandos del bot](#comandos-del-bot)
- [API REST](#api-rest)
- [Sesiones omnicanal](#sesiones-omnicanal)
- [Motor CrediJamar](#motor-credijamar)
- [Análisis de imágenes](#análisis-de-imágenes)
- [Modo demostración](#modo-demostración)
- [Desarrollo local sin Docker](#desarrollo-local-sin-docker)
- [Operación y verificación](#operación-y-verificación)
- [Solución de problemas](#solución-de-problemas)
- [Seguridad y despliegue en producción](#seguridad-y-despliegue-en-producción)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Estado de validación](#estado-de-validación)

## Características principales

- **Asesoría de interiores:** analiza una fotografía de sala, comedor, alcoba, oficina o almacenamiento y recomienda productos por categoría, estilo, paleta de color y presupuesto.
- **Inventario por ciudad:** consulta disponibilidad y stock en Bogotá, Medellín, Cali, Barranquilla, Cartagena y Bucaramanga.
- **CrediJamar:** simula cuota semanal y mensual, calcula capacidad de pago y determina el estado de pre-aprobación usando el perfil Customer 360.
- **Experiencia omnicanal:** widget web, página embebible, Mini App de Telegram, bot de Telegram y API REST.
- **Sesión compartida:** la identidad `tg-<id>` permite continuar la misma conversación entre el bot y la Mini App.
- **Modo demostración:** catálogo semilla, clientes de ejemplo y respuestas con plantillas cuando no hay credenciales.
- **IA generativa opcional:** Google Gemini para texto y visión, con fallback local si la clave no está configurada o la llamada falla.
- **Interfaz corporativa:** español, diseño responsive, iconos vectoriales Lucide y sin emojis.

## Arquitectura

```text
Navegador web / iframe
        |
        v
Frontend React + Vite + Tailwind
        |
        v
nginx :80  ---- /api/* ---->  FastAPI :8000
                                  |
                                  +--> Snowflake (inventario y Customer 360)
                                  +--> Google Gemini (texto y visión)
                                  +--> Catálogo demo (fallback)
                                  |
Telegram Mini App ----------------+
                                  |
Telegram Bot ---------------------+
        |
        +--> API interna http://backend:8000
```

En Docker Compose existen tres servicios:

| Servicio   | Contenedor       | Función                                                        | Puerto por defecto  |
| ---------- | ---------------- | -------------------------------------------------------------- | ------------------- |
| `backend`  | `jamar-backend`  | API FastAPI, agente, crédito, visión y acceso a datos          | `8000`              |
| `frontend` | `jamar-frontend` | Aplicación React servida por nginx; proxy de `/api` al backend | `3000`              |
| `bot`      | `jamar-bot`      | Bot de Telegram e integración con la API                       | Sin puerto expuesto |

El frontend y el bot se comunican con el backend por la red interna `jamar-net`. Solo el frontend y el backend publican puertos al host.

## Tecnologías

- **Backend:** Python 3.12, FastAPI, Pydantic v2, Uvicorn, Pillow, httpx.
- **IA:** Google Gemini mediante `google-genai`.
- **Datos:** Snowflake Connector for Python, con catálogo local de demostración.
- **Frontend:** React 18, Vite 6, Tailwind CSS 3, Lucide React.
- **Servidor web:** nginx 1.27 con proxy inverso y fallback SPA.
- **Bot:** python-telegram-bot 21, httpx.
- **Orquestación:** Docker Compose v2.
- **Crédito:** amortización francesa semanal con evaluación determinista.

## Estructura del proyecto

```text
jamar-ai-assistant/
├── backend/
│   ├── main.py                 # Entrada FastAPI, CORS, healthcheck y routers
│   ├── config.py               # Configuración tipada desde entorno/.env
│   ├── schemas.py              # Modelos de entrada y salida de la API
│   ├── agent.py                # Clasificación de intención, sesiones y Gemini
│   ├── catalog.py              # Catálogo, ciudades y clientes de demostración
│   ├── credit_engine.py        # Simulación y pre-aprobación CrediJamar
│   ├── snowflake_client.py     # Consultas a Snowflake y fallback demo
│   ├── routes/
│   │   ├── chat.py             # Conversación e historial
│   │   ├── credit.py           # Simulación, cupo y configuración de crédito
│   │   ├── customers.py        # Customer 360
│   │   ├── products.py         # Catálogo, inventario y ciudades
│   │   └── vision.py           # Análisis de imágenes y recomendaciones
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Página principal, embed y parámetros de URL
│   │   ├── api.js              # Cliente HTTP de la API
│   │   ├── telegram.js         # Puente con Telegram WebApp SDK
│   │   ├── utils.js            # Formatos, imágenes y utilidades
│   │   └── components/
│   │       ├── ChatWidget.jsx
│   │       ├── MessageBubble.jsx
│   │       ├── ProductCard.jsx
│   │       ├── CreditSimulator.jsx
│   │       ├── ImageUploader.jsx
│   │       ├── Launcher.jsx
│   │       ├── BrandMark.jsx
│   │       └── TypingIndicator.jsx
│   ├── public/products/        # Ilustraciones PNG/SVG de productos
│   ├── nginx.conf              # SPA, healthcheck y proxy /api
│   ├── package.json
│   └── Dockerfile
├── bot/
│   ├── bot.py                  # Comandos, menús, catálogo, crédito y fotos
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── start.sh                    # Arranque asistido para Linux/macOS
├── start.bat                   # Arranque asistido para Windows
└── README.md
```

## Requisitos previos

- Docker Engine 24 o superior y Docker Compose v2.
- Opcional para desarrollo local: Python 3.12+, Node.js 20+ y npm.
- Opcional: una API key de Google Gemini.
- Opcional: un token de bot de Telegram creado con `@BotFather`.
- Opcional: cuenta, usuario, contraseña y warehouse de Snowflake.

No se requieren credenciales para levantar la demo.

## Inicio rápido con Docker

### 1. Entrar al proyecto

```bash
cd jamar-ai-assistant
```

### 2. Crear el archivo de entorno

```bash
cp .env.example .env
```

En Windows:

```bat
copy .env.example .env
```

Los scripts `start.sh` y `start.bat` crean `.env` automáticamente si no existe, pero no sobrescriben uno existente.

### 3. Configurar la IA

Edita `.env` y agrega la clave de Gemini:

```env
GEMINI_API_KEY=tu_clave_de_google_ai_studio
```

Sin esta clave el asistente funciona con plantillas locales y la visión usa un análisis heurístico.

### 4. Configurar integraciones opcionales

- Telegram: define `TELEGRAM_BOT_TOKEN` y una `PUBLIC_WEBAPP_URL` accesible por Telegram.
- Snowflake: define `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER` y las credenciales correspondientes. La aplicación no usa datos demo salvo que se active explícitamente `SNOWFLAKE_FALLBACK_DEMO=true`.

### 5. Iniciar los servicios

Linux/macOS:

```bash
chmod +x start.sh
./start.sh
```

Windows:

```bat
start.bat
```

También puedes usar Docker Compose directamente:

```bash
docker compose up --build -d
```

### 6. Abrir la aplicación

Con los puertos por defecto:

| Recurso                   | URL                                      |
| ------------------------- | ---------------------------------------- |
| Página principal y widget | `http://localhost:3000`                  |
| Widget embebible          | `http://localhost:3000/?embed=1`         |
| Simulador de crédito      | `http://localhost:3000/?open=1&credit=1` |
| API                       | `http://localhost:8000`                  |
| Swagger UI                | `http://localhost:8000/docs`             |
| ReDoc                     | `http://localhost:8000/redoc`            |
| Healthcheck               | `http://localhost:8000/api/health`       |

Si los puertos `3000` u `8000` están ocupados, cambia `FRONTEND_PORT` y `BACKEND_PORT` en `.env` antes de iniciar.

## Configuración del entorno

Toda la configuración se carga desde variables de entorno o desde `.env`. En Docker Compose, el archivo `.env` de la raíz se inyecta en los servicios.

### Aplicación y red

| Variable               | Valor por defecto                             | Descripción                                                                                                         |
| ---------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `ENVIRONMENT`          | `production`                                  | Entorno de ejecución. En local puedes usar `development`.                                                           |
| `LOG_LEVEL`            | `INFO`                                        | Nivel de logs de backend y bot.                                                                                     |
| `FRONTEND_PORT`        | `3000`                                        | Puerto público del frontend.                                                                                        |
| `BACKEND_PORT`         | `8000`                                        | Puerto público del backend.                                                                                         |
| `CORS_ORIGINS`         | `http://localhost:3000,http://localhost:5173` | Orígenes permitidos, separados por coma.                                                                            |
| `PUBLIC_WEBAPP_URL`    | `http://localhost:3000`                       | URL pública que abre el bot en Telegram. Debe ser HTTPS y accesible desde Internet para la Mini App.                |
| `ASSET_BASE_URL`       | `http://localhost:3000/products`              | Variable reservada para futuras URLs de imágenes. El frontend actual resuelve imágenes desde `/products/<archivo>`. |
| `BACKEND_INTERNAL_URL` | `http://backend:8000`                         | Variable reservada. El bot usa `API_BASE_URL` para comunicarse con el backend.                                      |

### Google Gemini

| Variable                 | Valor por defecto  | Descripción                                                             |
| ------------------------ | ------------------ | ----------------------------------------------------------------------- |
| `GEMINI_API_KEY`         | vacío              | API key de Google AI Studio. Si está vacía, se usan plantillas locales. |
| `GEMINI_MODEL`           | `gemini-2.5-flash` | Modelo para generación de texto.                                        |
| `GEMINI_VISION_MODEL`    | `gemini-2.5-flash` | Modelo para análisis de imágenes.                                       |
| `GEMINI_TIMEOUT_SECONDS` | `40`               | Tiempo máximo de espera de la API de Gemini.                            |

### Snowflake

| Variable                                      | Valor por defecto      | Descripción                                                                                                                                                               |
| --------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SNOWFLAKE_ACCOUNT`                           | vacío                  | Identificador de cuenta de Snowflake.                                                                                                                                     |
| `SNOWFLAKE_USER`                              | vacío                  | Usuario de conexión.                                                                                                                                                      |
| `SNOWFLAKE_TOKEN`                             | vacío                  | PAT (Programmatic Access Token) emitido por Snowflake. Al definirlo se activa la autenticación por token.                                                                 |
| `SNOWFLAKE_PASSWORD`                          | vacío                  | Contraseña tradicional del usuario. También se acepta como nombre antiguo de la variable PAT si se configura `PROGRAMMATIC_ACCESS_TOKEN`. Ignorada con `externalbrowser`. |
| `SNOWFLAKE_AUTHENTICATOR`                     | vacío                  | Método de autenticación. Vacío = usuario/contraseña o PAT si se define `SNOWFLAKE_TOKEN`. Usa `externalbrowser` para SSO.                                                 |
| `SNOWFLAKE_CLIENT_STORE_TEMPORARY_CREDENTIAL` | `false`                | Solo con `externalbrowser`: guarda el token SSO para reutilizarlo sin abrir el navegador de nuevo.                                                                        |
| `SNOWFLAKE_DATABASE`                          | `JAMAR_DW`             | Base de datos.                                                                                                                                                            |
| `SNOWFLAKE_SCHEMA`                            | `PUBLIC`               | Esquema.                                                                                                                                                                  |
| `SNOWFLAKE_WAREHOUSE`                         | `JAMAR_WH`             | Warehouse usado en las consultas.                                                                                                                                         |
| `SNOWFLAKE_ROLE`                              | vacío                  | Rol opcional. Se recomienda un rol de solo lectura.                                                                                                                       |
| `SNOWFLAKE_INVENTORY_TABLE`                   | `INVENTARIO_PRODUCTOS` | Tabla de inventario.                                                                                                                                                      |
| `SNOWFLAKE_CUSTOMER_TABLE`                    | `CUSTOMER_360`         | Tabla de perfiles Customer 360.                                                                                                                                           |
| `SNOWFLAKE_FALLBACK_DEMO`                     | `false`                | Si es `true`, usa datos demo cuando Snowflake no está configurado o una consulta falla. Por defecto los errores se muestran para evitar datos demo inesperados.           |

### Telegram

| Variable             | Valor por defecto       | Descripción                                                                                       |
| -------------------- | ----------------------- | ------------------------------------------------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN` | vacío                   | Token entregado por `@BotFather`. Si está vacío, el contenedor del bot queda activo sin conexión. |
| `PUBLIC_WEBAPP_URL`  | `http://localhost:3000` | URL pública del frontend usada por los botones de Mini App.                                       |
| `API_BASE_URL`       | `http://backend:8000`   | URL interna del backend usada por el bot. Compose la define automáticamente.                      |

### CrediJamar

| Variable                      | Valor por defecto | Descripción                                      |
| ----------------------------- | ----------------- | ------------------------------------------------ |
| `CREDIT_WEEKLY_RATE`          | `0.0045`          | Tasa semanal usada en la amortización.           |
| `CREDIT_MAX_TERM_WEEKS`       | `52`              | Plazo máximo permitido.                          |
| `CREDIT_MIN_DOWN_PAYMENT_PCT` | `0.10`            | Cuota inicial mínima como porcentaje del precio. |

### Variables opcionales del frontend en desarrollo

Se definen en `frontend/.env.local`, no en el `.env` raíz:

| Variable            | Valor por defecto       | Descripción                                                     |
| ------------------- | ----------------------- | --------------------------------------------------------------- |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Destino del proxy de Vite para `/api`.                          |
| `VITE_API_BASE_URL` | vacío                   | URL absoluta de la API si el frontend no usa el proxy relativo. |

## Configurar Google Gemini

1. Ingresa a [Google AI Studio](https://aistudio.google.com/apikey).
2. Crea una API key.
3. Agrégala al archivo `.env`:

   ```env
   GEMINI_API_KEY=tu_clave
   GEMINI_MODEL=gemini-2.5-flash
   GEMINI_VISION_MODEL=gemini-2.5-flash
   ```

4. Reinicia el backend:

   ```bash
   docker compose up -d --force-recreate backend
   ```

5. Verifica que la IA esté habilitada:

   ```bash
   curl -s http://localhost:8000/api/health
   ```

   La respuesta debe incluir `"ai_enabled": true`.

### Comportamiento de la IA

- **Texto:** Gemini recibe el mensaje, la intención detectada, el historial reciente, los productos recuperados, la oferta de crédito y el perfil Customer 360.
- **Visión:** Gemini recibe la fotografía y devuelve un JSON con tipo de espacio, estilo, colores dominantes y recomendaciones.
- **Fallback:** si no hay clave, la clave es inválida, se agota la cuota o la llamada falla, el backend responde con plantillas locales y visión heurística. Los errores quedan en los logs.
- **Sin emojis:** las respuestas pasan por un filtro que elimina emojis antes de enviarse.

Si el modelo configurado no está disponible en tu cuenta o región, cambia `GEMINI_MODEL` y `GEMINI_VISION_MODEL` por un modelo habilitado en Google AI Studio para tu proyecto.

## Configurar Telegram

### 1. Crear el bot

1. Abre Telegram y busca `@BotFather`.
2. Ejecuta `/newbot`.
3. Define nombre y usuario del bot.
4. Copia el token entregado.

### 2. Configurar el token

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### 3. Publicar el frontend con HTTPS

Telegram requiere una URL pública HTTPS para abrir Mini Apps. `http://localhost:3000` solo funciona en el navegador local, no dentro de Telegram.

Opciones:

- Desplegar frontend y backend en un servidor con dominio y certificado TLS.
- Usar un túnel temporal para pruebas, por ejemplo ngrok o Cloudflare Tunnel.

Configura la URL pública:

```env
PUBLIC_WEBAPP_URL=https://asistente.tu-dominio.com
```

Si usas un túnel, actualiza también `CORS_ORIGINS` con el origen público.

### 4. Registrar la Mini App en BotFather

En BotFather puedes usar `/newapp` para registrar la Mini App y `/setmenubutton` para asignar el botón de menú. Usa como URL:

```text
https://asistente.tu-dominio.com/?open=1
```

La Mini App detecta automáticamente el usuario de Telegram y usa la identidad `tg-<id>`, la misma que emplea el bot.

### 5. Reiniciar el bot

```bash
docker compose restart bot
```

Si el token no está configurado, el contenedor del bot permanece activo e inicia sin conexión, evitando reinicios en bucle.

## Integración con Snowflake

El backend consulta dos tablas. Los nombres son configurables, pero las columnas esperadas son fijas.

### Tabla `INVENTARIO_PRODUCTOS`

Una fila representa un producto en una ciudad. El mismo `PRODUCT_ID` puede aparecer varias veces con distinta `CIUDAD` y `STOCK`.

| Columna          | Tipo sugerido | Uso                                              |
| ---------------- | ------------- | ------------------------------------------------ |
| `PRODUCT_ID`     | VARCHAR       | Identificador único del producto.                |
| `SKU`            | VARCHAR       | Código comercial.                                |
| `NOMBRE`         | VARCHAR       | Nombre visible.                                  |
| `CATEGORIA`      | VARCHAR       | Sala, Comedor, Alcoba, Almacenamiento u Oficina. |
| `SUBCATEGORIA`   | VARCHAR       | Tipo específico de mueble.                       |
| `COLOR`          | VARCHAR       | Color principal.                                 |
| `COLOR_HEX`      | VARCHAR       | Color en formato hexadecimal.                    |
| `PRECIO`         | NUMBER        | Precio en COP.                                   |
| `ANCHO_CM`       | NUMBER        | Ancho en centímetros.                            |
| `PROFUNDIDAD_CM` | NUMBER        | Profundidad en centímetros.                      |
| `ALTO_CM`        | NUMBER        | Alto en centímetros.                             |
| `MATERIAL`       | VARCHAR       | Materiales principales.                          |
| `DESCRIPCION`    | VARCHAR       | Descripción comercial.                           |
| `IMAGEN`         | VARCHAR       | Nombre del archivo servido en `/products/`.      |
| `RATING`         | FLOAT         | Calificación de 0 a 5.                           |
| `CIUDAD`         | VARCHAR       | Ciudad donde hay inventario.                     |
| `STOCK`          | NUMBER        | Unidades disponibles en esa ciudad.              |

### Tabla `CUSTOMER_360`

| Columna                  | Tipo sugerido | Uso                                           |
| ------------------------ | ------------- | --------------------------------------------- |
| `USER_ID`                | VARCHAR       | Identidad del cliente, por ejemplo `tg-1001`. |
| `NOMBRE`                 | VARCHAR       | Nombre completo.                              |
| `DOCUMENTO`              | VARCHAR       | Documento enmascarado.                        |
| `CIUDAD`                 | VARCHAR       | Ciudad del cliente.                           |
| `SEGMENTO`               | VARCHAR       | Segmento comercial.                           |
| `COMPRAS`                | NUMBER        | Número de compras.                            |
| `TICKET_PROMEDIO`        | NUMBER        | Ticket promedio en COP.                       |
| `ULTIMA_COMPRA`          | DATE          | Fecha de la última compra.                    |
| `CATEGORIAS_PREFERIDAS`  | VARCHAR       | Categorías separadas por coma.                |
| `INGRESO_MENSUAL`        | NUMBER        | Ingreso mensual estimado.                     |
| `OBLIGACIONES_MENSUALES` | NUMBER        | Obligaciones financieras mensuales.           |
| `SCORE_CREDITO`          | NUMBER        | Score usado por CrediJamar.                   |
| `CUPO_CREDIJAMAR`        | NUMBER        | Cupo máximo pre-aprobado.                     |

### Ejemplo de DDL

```sql
CREATE OR REPLACE TABLE JAMAR_DW.PUBLIC.INVENTARIO_PRODUCTOS (
  PRODUCT_ID VARCHAR NOT NULL,
  SKU VARCHAR,
  NOMBRE VARCHAR,
  CATEGORIA VARCHAR,
  SUBCATEGORIA VARCHAR,
  COLOR VARCHAR,
  COLOR_HEX VARCHAR,
  PRECIO NUMBER(12, 2),
  ANCHO_CM NUMBER,
  PROFUNDIDAD_CM NUMBER,
  ALTO_CM NUMBER,
  MATERIAL VARCHAR,
  DESCRIPCION VARCHAR,
  IMAGEN VARCHAR,
  RATING FLOAT,
  CIUDAD VARCHAR,
  STOCK NUMBER
);

CREATE OR REPLACE TABLE JAMAR_DW.PUBLIC.CUSTOMER_360 (
  USER_ID VARCHAR NOT NULL,
  NOMBRE VARCHAR,
  DOCUMENTO VARCHAR,
  CIUDAD VARCHAR,
  SEGMENTO VARCHAR,
  COMPRAS NUMBER,
  TICKET_PROMEDIO NUMBER(12, 2),
  ULTIMA_COMPRA DATE,
  CATEGORIAS_PREFERIDAS VARCHAR,
  INGRESO_MENSUAL NUMBER(12, 2),
  OBLIGACIONES_MENSUALES NUMBER(12, 2),
  SCORE_CREDITO NUMBER,
  CUPO_CREDIJAMAR NUMBER(12, 2)
);
```

### Consideraciones

- El cliente usa `paramstyle="qmark"` y consultas parametrizadas para los valores.
- Los nombres de base de datos, esquema y tabla se validan como identificadores seguros.
- Si no hay credenciales, el backend usa el catálogo demo.
- Si una consulta falla y `SNOWFLAKE_FALLBACK_DEMO=true`, se usa el catálogo demo y se registra el error.
- Para producción se recomienda un rol de solo lectura y `SNOWFLAKE_FALLBACK_DEMO=false`.
- El campo `IMAGEN` debe ser un nombre de archivo disponible en `frontend/public/products/`. Para usar un CDN externo hay que ajustar `productImage` en `frontend/src/utils.js`.
- La app no escribe en Snowflake. La solicitud formal de crédito se gestiona con un asesor.

### Autenticación `externalbrowser`

`externalbrowser` abre el navegador del sistema para completar el inicio de sesión SSO y
recibe el token en un servidor local. Por eso requiere un navegador y acceso a `localhost`:
funciona al ejecutar el backend de forma local, no dentro de un contenedor headless.

```env
SNOWFLAKE_ACCOUNT=<organizacion>-<cuenta>
SNOWFLAKE_USER=<usuario>
SNOWFLAKE_AUTHENTICATOR=externalbrowser
SNOWFLAKE_PASSWORD=
SNOWFLAKE_CLIENT_STORE_TEMPORARY_CREDENTIAL=true
```

Pasos:

1. Usa el identificador de cuenta exacto que aparece en Snowflake (por ejemplo
   `<organizacion>-<cuenta>` o `<locator>.<region>`); `OZ69178` sin región puede devolver 404.
2. Ejecuta el backend fuera de Docker, en una máquina con navegador:

   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. En la primera consulta se abre el navegador. Completa el login y el backend recibe el token.
   Con `SNOWFLAKE_CLIENT_STORE_TEMPORARY_CREDENTIAL=true` el token se reutiliza mientras sea válido.

Para contenedores o servidores sin navegador se recomienda autenticación por par de claves
(`SNOWFLAKE_AUTHENTICATOR=snowflake_jwt` con clave privada), no `externalbrowser`.

## Uso del frontend y del widget

### Página principal

`http://localhost:3000` muestra la landing del asistente. El widget flotante se abre automáticamente en pantallas grandes y puede abrirse manualmente.

### Parámetros de URL

| Parámetro           | Ejemplo                                             | Efecto                                                          |
| ------------------- | --------------------------------------------------- | --------------------------------------------------------------- |
| `open=1`            | `/?open=1`                                          | Abre el widget al cargar.                                       |
| `embed=1`           | `/?embed=1`                                         | Oculta la landing y muestra solo el widget a pantalla completa. |
| `credit=1`          | `/?open=1&credit=1`                                 | Abre directamente el simulador de crédito.                      |
| `price=2499000`     | `/?open=1&credit=1&price=2499000`                   | Precarga el precio en el simulador.                             |
| `name=Sofa%20Miami` | `/?open=1&credit=1&price=2499000&name=Sofa%20Miami` | Muestra el nombre del producto en el simulador.                 |

### Integración mediante iframe

El proyecto no incluye un SDK JavaScript autónomo. La forma soportada de integrarlo en otro sitio es un iframe:

```html
<iframe
  src="https://asistente.tu-dominio.com/?embed=1"
  title="Asistente Jamar"
  style="width: 100%; height: 720px; border: 0;"
  allow="clipboard-write"
></iframe>
```

Para abrir el widget sobre la página anfitriona, usa un enlace o botón:

```html
<a
  href="https://asistente.tu-dominio.com/?open=1"
  target="_blank"
  rel="noopener"
>
  Hablar con el Asistente Jamar
</a>
```

Para abrir el simulador con un producto:

```text
https://asistente.tu-dominio.com/?open=1&credit=1&price=2549000&name=Cama%20Uribe%20Queen
```

### Funciones del widget

- Conversación con historial.
- Tarjetas de producto con precio, dimensiones, material, stock y calificación.
- Carrito de productos.
- Simulador CrediJamar con cuota inicial y plazo.
- Carga de imágenes JPG, PNG o WEBP de hasta 8 MB.
- Drag and drop de imágenes.
- Indicador de escritura y estado de conexión.
- Adaptación a Telegram mediante el SDK WebApp.

## Comandos del bot

| Comando            | Función                                             |
| ------------------ | --------------------------------------------------- |
| `/start`           | Inicia la conversación y muestra el menú principal. |
| `/menu`            | Muestra el menú principal.                          |
| `/productos`       | Abre el catálogo por categorías.                    |
| `/credito`         | Consulta el cupo pre-aprobado CrediJamar.           |
| `/mini`            | Abre la Mini App y el simulador.                    |
| `/ayuda` o `/help` | Muestra la ayuda.                                   |
| `/reset`           | Reinicia el historial de la conversación.           |

Además de los comandos, el bot acepta:

- Mensajes de texto en lenguaje natural.
- Fotografías para analizar un espacio.
- Botones de catálogo, producto, crédito y asesor.

La identidad usada por el bot es `tg-<id de Telegram>`. Esa misma identidad se usa en la Mini App para compartir historial.

## API REST

La API está montada bajo el prefijo `/api`. La documentación interactiva está en `/docs`.

### Endpoints

| Método   | Ruta                                | Descripción                                             |
| -------- | ----------------------------------- | ------------------------------------------------------- |
| `GET`    | `/`                                 | Información básica del servicio.                        |
| `GET`    | `/api/health`                       | Estado del backend, modo de datos, IA y Telegram.       |
| `POST`   | `/api/chat`                         | Procesa un mensaje del usuario.                         |
| `GET`    | `/api/chat/history/{session_id}`    | Consulta el historial de una sesión.                    |
| `DELETE` | `/api/chat/history/{session_id}`    | Reinicia una sesión. Acepta `user_id` como query param. |
| `POST`   | `/api/vision`                       | Analiza una imagen y recomienda productos.              |
| `POST`   | `/api/credit-check`                 | Simula y evalúa una solicitud CrediJamar.               |
| `GET`    | `/api/credit/preapproval/{user_id}` | Consulta cupo y perfil financiero.                      |
| `GET`    | `/api/credit/config`                | Parámetros públicos del simulador.                      |
| `GET`    | `/api/products`                     | Busca productos con filtros.                            |
| `GET`    | `/api/products/{product_id}`        | Detalle de un producto.                                 |
| `GET`    | `/api/inventory/summary`            | Resumen de inventario por categoría.                    |
| `GET`    | `/api/cities`                       | Ciudades con cobertura y número de tiendas.             |
| `GET`    | `/api/customer/{user_id}`           | Perfil Customer 360.                                    |

### Ejemplo de conversación

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Busco una cama queen para mi alcoba",
    "user_id": "tg-1001",
    "city": "Barranquilla",
    "channel": "web"
  }'
```

Campos principales de la respuesta:

- `reply`: respuesta del asistente.
- `intent`: intención detectada.
- `session_id`: clave de sesión resuelta.
- `products`: productos recomendados.
- `credit`: oferta CrediJamar si aplica.
- `suggestions`: sugerencias de seguimiento.
- `source`: `gemini`, `demo` u otra fuente.

### Ejemplo de catálogo

```bash
curl "http://localhost:8000/api/products?city=Medellin&category=Sala&max_price=3000000&limit=4"
```

Parámetros soportados:

| Parámetro   | Tipo    | Descripción                         |
| ----------- | ------- | ----------------------------------- |
| `city`      | string  | Ciudad de entrega.                  |
| `category`  | string  | Categoría o subcategoría.           |
| `color`     | string  | Color del producto.                 |
| `max_price` | number  | Presupuesto máximo en COP.          |
| `q`         | string  | Texto libre.                        |
| `limit`     | integer | Máximo de resultados, entre 1 y 50. |

### Ejemplo de análisis de imagen

```bash
curl -X POST http://localhost:8000/api/vision \
  -F "file=@sala.jpg" \
  -F "city=Medellin" \
  -F "budget=3000000" \
  -F "room_type=Sala" \
  -F "user_id=tg-1001"
```

La respuesta incluye `analysis` con `room_type`, `style`, `dominant_colors`, `notes`, `recommended_category` y `source`.

Formatos permitidos: JPG, PNG y WEBP. Tamaño máximo: 8 MB.

### Ejemplo de crédito

```bash
curl -X POST http://localhost:8000/api/credit-check \
  -H "Content-Type: application/json" \
  -d '{
    "price": 2549000,
    "down_payment": 300000,
    "term_weeks": 24,
    "user_id": "tg-1001"
  }'
```

La respuesta incluye estado, monto máximo, cuota semanal, cuota mensual, intereses, tasa efectiva anual y motivo de la decisión.

### Ejemplo de Customer 360

```bash
curl http://localhost:8000/api/customer/tg-1001
curl http://localhost:8000/api/credit/preapproval/tg-1001
```

## Sesiones omnicanal

La clave de sesión se resuelve en este orden:

1. Si llega `user_id`, se usa `user:<user_id>`.
2. Si no hay `user_id`, se usa `session_id`.
3. Si no hay ninguno, se genera `web:<aleatorio>`.

El frontend y la Mini App envían `user_id` cuando Telegram expone el usuario. El bot usa `tg-<id>`, por lo que ambos canales comparten historial.

El historial se guarda en memoria y conserva los últimos 16 mensajes por sesión. Esto implica:

- Se pierde al reiniciar el backend.
- No se comparte entre réplicas del backend.
- Para producción con varias instancias se requiere Redis, base de datos u otro almacén compartido.

## Motor CrediJamar

El motor es determinista y no escribe en Snowflake.

### Cálculo

- Usa amortización francesa con cuota semanal.
- Plazos disponibles: 8, 12, 16, 24, 36 y 52 semanas.
- Cuota inicial mínima: 10% del precio por defecto.
- Tasa semanal por defecto: `0.0045`.
- Capacidad de pago mensual: 30% del ingreso disponible después de obligaciones, con un piso del 10% del ingreso.
- Cupo máximo: el menor valor entre el cupo del cliente y el capital máximo financiable según capacidad de pago.
- La aprobación requiere score mínimo de 650, monto financiado dentro del cupo y cuota semanal dentro de la capacidad.

### Estados

| Estado                | Significado                                             |
| --------------------- | ------------------------------------------------------- |
| `pre_aprobado`        | El perfil cumple las políticas para continuar.          |
| `requiere_validacion` | El monto supera el cupo o requiere revisión documental. |
| `no_aprobado`         | No cumple score, cupo o capacidad de pago.              |

La respuesta siempre incluye un aviso de que la aprobación definitiva la confirma un asesor CrediJamar.

## Análisis de imágenes

El flujo de visión es:

1. Valida tipo y tamaño del archivo.
2. Corrige orientación EXIF y redimensiona a un máximo de 1280 px.
3. Si Gemini está configurado, solicita un JSON estructurado.
4. Si Gemini no está disponible, usa un análisis heurístico de paleta con Pillow.
5. Busca inventario compatible por categoría, ciudad y presupuesto.
6. Ordena los productos por armonía de color y proporción.
7. Agrega el análisis al historial de la sesión compartida.

El análisis heurístico no identifica objetos reales: estima colores y tipo de espacio a partir del nombre del archivo, la pista del usuario y la paleta de la imagen. Para recomendaciones visuales precisas se requiere Gemini.

## Modo demostración

El sistema arranca en modo demostración si no hay credenciales de Snowflake o Gemini.

Incluye:

- 14 productos de ejemplo.
- 6 ciudades: Bogotá, Medellín, Cali, Barranquilla, Cartagena y Bucaramanga.
- 37 tiendas en total.
- Clientes demo `tg-1001` y `demo-user`.
- Perfiles deterministas para cualquier otro `user_id`.
- Respuestas con plantillas profesionales en español.
- Análisis de imagen heurístico.

El catálogo demo se define en `backend/catalog.py`. La ciudad y el score de un cliente no registrado se generan de forma determinista a partir de su `user_id`.

## Desarrollo local sin Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Carga las variables de entorno. `pydantic-settings` busca `.env` en el directorio de ejecución, por lo que puedes copiar el archivo raíz:

```bash
cp ../.env .env
```

Inicia la API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

En otra terminal:

```bash
cd frontend
npm ci
npm run dev
```

Abre `http://localhost:5173`. Vite redirige `/api` a `http://localhost:8000` mediante `VITE_PROXY_TARGET`.

Para compilar producción:

```bash
npm run build
npm run preview
```

### Bot

Con el backend en ejecución:

```bash
cd bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Define las variables y ejecuta:

```bash
export TELEGRAM_BOT_TOKEN="tu_token"
export API_BASE_URL="http://localhost:8000"
export PUBLIC_WEBAPP_URL="http://localhost:5173"
python bot.py
```

En Windows PowerShell usa `$env:TELEGRAM_BOT_TOKEN="..."` y equivalentes para las demás variables.

## Operación y verificación

### Ver estado

```bash
docker compose ps
curl http://localhost:8000/api/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "snowflake_mode": "demo",
  "ai_enabled": false,
  "telegram_enabled": false,
  "timestamp": "..."
}
```

Con Gemini configurado, `ai_enabled` debe ser `true`. Con Snowflake configurado, `snowflake_mode` debe ser `snowflake`.

### Ver logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f bot
```

### Reconstruir después de cambios

```bash
docker compose up --build -d
```

Solo backend:

```bash
docker compose up --build -d backend
```

Solo frontend:

```bash
docker compose up --build -d frontend
```

### Detener

```bash
docker compose down
```

Detener y eliminar volúmenes:

```bash
docker compose down -v
```

El proyecto no usa volúmenes persistentes; el historial de conversación vive en memoria.

### Validaciones recomendadas

```bash
python3 -m compileall -q backend bot
cd frontend && npm ci && npm run build
docker compose config -q
```

Prueba manual mínima:

```bash
curl http://localhost:8000/api/health
curl http://localhost:3000/
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Busco un sofá para mi sala","city":"Bogotá"}'
```

## Solución de problemas

### El puerto 8000 o 3000 ya está en uso

Síntoma:

```text
Bind for 0.0.0.0:8000 failed: port is already allocated
```

Solución: cambia los puertos en `.env`:

```env
FRONTEND_PORT=13000
BACKEND_PORT=18000
```

Luego reinicia:

```bash
docker compose up -d
```

Si cambias el puerto del frontend, actualiza `PUBLIC_WEBAPP_URL` y `CORS_ORIGINS` con el nuevo origen.

### La IA sigue en modo demostración

Verifica:

```bash
grep GEMINI_API_KEY .env
curl -s http://localhost:8000/api/health
docker compose logs backend | grep -i gemini
```

Causas comunes:

- La clave está vacía o tiene espacios.
- No se reinició el backend después de cambiar `.env`.
- La clave es inválida, está restringida o no tiene cuota disponible.
- El modelo configurado no está disponible para la cuenta o región.

Prueba con otro modelo disponible en tu proyecto:

```env
GEMINI_MODEL=nombre_del_modelo_disponible
GEMINI_VISION_MODEL=nombre_del_modelo_disponible
```

### El bot no responde

Verifica el token, los logs y la conectividad con el backend:

```bash
docker compose logs -f bot
docker compose exec bot python -c "import os; print(bool(os.getenv('TELEGRAM_BOT_TOKEN')))"
```

Si el token está vacío, el contenedor no se conecta pero permanece activo. Configura `TELEGRAM_BOT_TOKEN` y ejecuta:

```bash
docker compose restart bot
```

### La Mini App no abre en Telegram

Telegram requiere una URL pública HTTPS. Revisa:

- `PUBLIC_WEBAPP_URL` no debe ser `localhost`.
- La URL debe ser accesible desde un dispositivo móvil.
- El certificado TLS debe ser válido.
- La Mini App debe estar registrada en BotFather.
- Si usas un túnel, actualiza `CORS_ORIGINS`.

### Snowflake no responde y se usa la demo

Es el comportamiento esperado si `SNOWFLAKE_FALLBACK_DEMO=true`. Revisa los logs:

```bash
docker compose logs backend | grep -i snowflake
```

Comprueba credenciales, base de datos, esquema, warehouse, rol y nombres de tablas. Si quieres que los errores se propaguen en producción:

```env
SNOWFLAKE_FALLBACK_DEMO=false
```

### Error de CORS en el navegador

Agrega el origen exacto del frontend en `CORS_ORIGINS`, incluyendo protocolo y puerto:

```env
CORS_ORIGINS=https://asistente.tu-dominio.com,http://localhost:5173
```

Reinicia el backend después del cambio.

### El frontend carga pero no habla con la API

En Docker, nginx redirige `/api` a `http://backend:8000` dentro de la red `jamar-net`. Verifica:

```bash
curl http://localhost:8000/api/health
curl http://localhost:3000/api/health
docker compose logs frontend
```

Si ambos healthchecks responden, el problema suele estar en el navegador, CORS o un proxy externo.

### Error al construir el frontend por `package-lock.json`

El Dockerfile usa `npm ci` y requiere `package-lock.json`. Si falta, genera el archivo:

```bash
cd frontend
npm install
```

Luego reconstruye:

```bash
docker compose build --no-cache frontend
```

### Quiero reiniciar una conversación

```bash
curl -X DELETE "http://localhost:8000/api/chat/history/user:tg-1001?user_id=tg-1001"
```

En Telegram usa `/reset`.

## Seguridad y despliegue en producción

- No versionar `.env`; el `.gitignore` ya lo excluye.
- Usar HTTPS para el frontend y, si se expone, para el backend.
- No publicar el backend directamente si no es necesario; el frontend ya hace proxy de `/api`.
- Restringir `CORS_ORIGINS` a los dominios reales.
- Usar un rol Snowflake de solo lectura y credenciales de mínimo privilegio.
- Mantener `SNOWFLAKE_FALLBACK_DEMO=false` en producción para detectar fallos de datos.
- Implementar autenticación, autorización y rate limiting antes de exponer la API públicamente.
- No enviar imágenes con datos sensibles si se habilita Gemini; las imágenes se envían al proveedor externo para análisis.
- Revisar los logs para detectar fallos de Gemini, Snowflake o Telegram.
- Para varias réplicas del backend, reemplazar el almacén de sesiones en memoria por Redis o una base de datos.
- Configurar un proxy inverso con límites de tamaño y tiempo acordes al límite de 8 MB por imagen.

El proyecto no incluye autenticación de usuarios, firma de solicitudes, control de cuotas ni persistencia de conversaciones. Es una base funcional que debe endurecerse antes de un despliegue público.

## Limitaciones conocidas

- El historial de sesión es en memoria y no persiste al reiniciar.
- La integración con Snowflake usa autenticación por usuario y contraseña; no implementa key pair ni OAuth.
- Las columnas de Snowflake deben coincidir con el esquema documentado.
- Las imágenes de producto se resuelven desde `/products/<archivo>`; no hay integración directa con un CDN.
- La integración web es por iframe o enlace, no un SDK JavaScript embebible.
- El análisis heurístico de imágenes no detecta objetos reales.
- No hay suite de pruebas automatizada incluida; las validaciones actuales son compilación, pruebas de humo y verificación manual.
- El bot no expone un webhook; usa polling de Telegram.
- No hay autenticación ni control de abuso incorporados.

## Estado de validación

La versión actual fue validada con:

- Compilación de `backend` y `bot` con `python -m compileall`.
- Pruebas de humo del backend para health, chat, historial, catálogo, visión, crédito y Customer 360.
- Pruebas simuladas de las rutas de texto y visión de Gemini.
- Build de los tres servicios con Docker Compose.
- Healthcheck del backend y del frontend con proxy `/api`.
- Build de producción del frontend con Vite.

Las llamadas reales a Gemini requieren configurar `GEMINI_API_KEY`. Las consultas reales a Snowflake requieren credenciales válidas y las tablas documentadas. La conexión real del bot requiere `TELEGRAM_BOT_TOKEN` y una URL pública HTTPS para la Mini App.

---

Proyecto interno de Muebles Jamar. No se incluye una licencia de distribución en este repositorio.
