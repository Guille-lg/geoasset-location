# GeoAssets Intelligence — Documentación Funcional y Técnica

> **Proyecto:** Caso II — Aplicación de IA a la Geolocalización de Activos Productivos  
> **Contexto académico:** Trabajo de Fin de Máster (TFM)  
> **Stack:** Vue 3 · FastAPI · Docker · LiteLLM · Google Maps API · PostgreSQL  

---

## 1. Objeto del Proyecto

### 1.1 Propósito

GeoAssets Intelligence es una plataforma de inteligencia geoespacial empresarial que combina fuentes de datos públicas, modelos de lenguaje de gran escala (LLMs) y técnicas de distribución de probabilidades para **identificar, estructurar y visualizar los activos productivos** de cualquier empresa española sobre un mapa interactivo.

El sistema responde a una necesidad real en contextos de análisis de inversión, due diligence, gestión de riesgos y planificación estratégica: conocer dónde están físicamente los activos productivos de una empresa (fábricas, almacenes, oficinas, centros logísticos, plantas de producción, etc.) de forma automatizada, escalable y verificable.

### 1.2 Alcance

- **Geografía cubierta:** España (incluyendo Canarias, Baleares, Ceuta y Melilla).
- **Tipo de entidades analizadas:** Empresas con presencia operativa en territorio español, cotizadas o no.
- **Tipo de activos identificables:** Ver Sección 5 — Catálogo de Categorías de Activos.
- **Fuentes de datos:** Google Maps API (Places + Geocoding), informes públicos anuales, webs corporativas y registros públicos accesibles.

### 1.3 Propuesta de Valor

| Método tradicional | GeoAssets Intelligence |
|---|---|
| Búsqueda manual fuente por fuente | Agregación automatizada y paralela |
| Datos no estructurados dispersos | Salida estructurada, categorizada y geocodificada |
| Horas o días de trabajo analítico | Resultado en 60–120 segundos |
| Sin probabilidad de confianza | Score de confianza por activo mediante distribución bayesiana |
| Visualización estática o ninguna | Mapa interactivo con capas, filtros y detalle por activo |

---

## 2. Arquitectura del Sistema

### 2.1 Vista de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTE (SPA)                        │
│              Vue 3 + Pinia + Leaflet / Mapbox GL            │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / WebSocket (SSE)
┌───────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  API Router │  │ Orchestrator │  │  LLM Processing   │  │
│  │  /search    │  │  Pipeline    │  │  (LiteLLM Pool)   │  │
│  │  /assets    │  │  + SSE       │  │  Parallel Workers │  │
│  │  /stream    │  │  Progress    │  │                   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Data Layer                              │    │
│  │  Google Maps API  │  PostgreSQL  │  Redis (cache)   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │        DOCKER COMPOSE      │
          │  frontend · backend        │
          │  postgres · redis          │
          └────────────────────────────┘
```

### 2.2 Stack Tecnológico Detallado

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | Vue 3 + Vite + TypeScript | SPA reactiva, composición moderna |
| Estado | Pinia | Store reactivo nativo de Vue 3 |
| Mapa | Leaflet.js + OpenStreetMap / Mapbox GL | Visualización geoespacial interactiva |
| UI | Tailwind CSS + HeadlessUI | Diseño profesional sin overhead |
| Backend | FastAPI (Python 3.11+) | Async nativo, tipado, OpenAPI automático |
| Streaming | Server-Sent Events (SSE) | Progreso en tiempo real sin WebSocket |
| LLM Gateway | LiteLLM | Abstracción multi-proveedor (OpenAI, Anthropic, etc.) |
| LLM Workers | asyncio + semaphore pool | Procesamiento paralelo controlado |
| Maps/Places | Google Maps Places API v2 | Fuente principal de activos geolocalizados |
| Base de datos | PostgreSQL + PostGIS | Almacenamiento geoespacial nativo |
| Caché | Redis | TTL por empresa, evita recómputo |
| Contenedores | Docker + Docker Compose | Despliegue reproducible |
| CI | GitHub Actions | Tests y build automatizados |

---

## 3. Flujo Funcional Completo

### 3.1 Diagrama de Secuencia

```
Usuario          Frontend (Vue)         Backend (FastAPI)         LLMs / APIs Externas
   │                   │                       │                          │
   │  Escribe empresa  │                       │                          │
   │──────────────────▶│                       │                          │
   │                   │  GET /search?q=       │                          │
   │                   │──────────────────────▶│                          │
   │                   │  [listado empresas]   │                          │
   │                   │◀──────────────────────│                          │
   │  Selecciona       │                       │                          │
   │──────────────────▶│                       │                          │
   │                   │  POST /assets/analyze │                          │
   │                   │──────────────────────▶│                          │
   │                   │                       │── PASO 1: Search Maps ──▶│
   │                   │  SSE: paso 1 ✓        │◀── raw places data ──────│
   │                   │◀──────────────────────│                          │
   │                   │                       │── PASO 2: LLM filter ───▶│
   │                   │  SSE: paso 2 ✓        │◀── structured JSON ──────│
   │                   │◀──────────────────────│                          │
   │                   │                       │── PASO 3: Enrich ───────▶│
   │                   │  SSE: paso 3 ✓        │◀── enriched assets ──────│
   │                   │◀──────────────────────│                          │
   │                   │                       │── PASO 4: Confidence ───▶│
   │                   │  SSE: paso 4 ✓        │◀── scored assets ────────│
   │                   │◀──────────────────────│                          │
   │                   │  SSE: complete + data │                          │
   │                   │◀──────────────────────│                          │
   │  Vista mapa ✓     │                       │                          │
   │◀──────────────────│                       │                          │
```

### 3.2 Descripción de Pasos del Pipeline

#### PASO 0 — Identificación de la Empresa
**Responsable:** Backend → Google Places Text Search + base de datos interna  
**Input:** Nombre libre escrito por el usuario  
**Output:** Entidad empresarial normalizada: nombre oficial, CIF/NIF (si disponible), sector CNAE, domicilio social  
**Duración estimada:** ~2 s  

Proceso:
1. Búsqueda en Places API con query `"{empresa}" empresa España`.
2. Desambiguación por LLM si hay múltiples candidatos (ranking por popularidad y coincidencia).
3. Extracción de nombre canónico para usar en las búsquedas de activos.

---

#### PASO 1 — Extracción de Activos desde Google Maps
**Responsable:** Backend → Google Maps Places API (Nearby Search + Text Search)  
**Input:** Nombre canónico de la empresa  
**Output:** Lista raw de `Place` objects de Google Maps  
**Duración estimada:** ~10–20 s  

Proceso:
1. Se ejecutan **N queries paralelas** con variaciones del nombre de la empresa más keywords por categoría de activo:
   - `"{empresa}" almacén logístico`
   - `"{empresa}" planta producción`
   - `"{empresa}" oficinas centrales`
   - `"{empresa}" centro distribución`
   - ... (ver Sección 5 para listado completo)
2. Se hace Nearby Search en las principales ciudades españolas (Madrid, Barcelona, Valencia, Sevilla, Zaragoza, Bilbao, Málaga, Murcia, Palma, Las Palmas, etc.) para garantizar cobertura nacional.
3. Se agregan y deduplican resultados por `place_id`.
4. Se obtienen detalles completos por cada `place_id`: nombre, dirección, coordenadas, tipo, horario, rating, website, photos.

**Parámetros de la API utilizados:**
```python
{
  "query": "{empresa} {keyword_categoria}",
  "locationbias": "rectangle:Spain",  # bbox España
  "language": "es",
  "fields": ["id", "displayName", "formattedAddress", 
             "location", "types", "websiteUri", 
             "nationalPhoneNumber", "regularOpeningHours"]
}
```

---

#### PASO 2 — Filtrado y Clasificación con LLM
**Responsable:** Backend → LiteLLM (pool de workers async)  
**Input:** Lista raw de places de Google Maps  
**Output:** Lista filtrada y clasificada de activos productivos  
**Duración estimada:** ~15–30 s (paralelo)  

Proceso:
1. Los resultados se agrupan en **batches de 20 places** para optimizar tokens.
2. Cada batch se envía a un worker LLM en paralelo (máximo configurable, por defecto 5 workers concurrentes).
3. El LLM evalúa para cada place:
   - ¿Es un activo productivo real de esta empresa? (`boolean`)
   - ¿Cuál es su categoría? (ver Sección 5)
   - ¿Cuál es el nombre normalizado?
   - ¿Es una sede principal, secundaria o instalación operativa?
4. El LLM responde en JSON estructurado estricto.
5. Se descartan lugares con `is_productive_asset: false`.

**System prompt del LLM de filtrado:**
```
Eres un analista experto en activos empresariales. 
Tu tarea es evaluar si un lugar de Google Maps es un activo productivo 
real de la empresa "{empresa}". Un activo productivo es cualquier 
instalación física donde la empresa realiza operaciones: fábricas, 
almacenes, oficinas, centros logísticos, plantas, etc. 
NO incluyas: restaurantes, tiendas de terceros, menciones indirectas, 
resultados irrelevantes. Responde ÚNICAMENTE en JSON válido.
```

---

#### PASO 3 — Enriquecimiento de Datos
**Responsable:** Backend → LiteLLM + Google Maps Place Details  
**Input:** Lista filtrada de activos productivos  
**Output:** Activos enriquecidos con metadatos adicionales  
**Duración estimada:** ~10–20 s  

Proceso:
1. Para cada activo confirmado, se solicitan detalles adicionales a Google Maps (reviews, fotos, datos de contacto completos).
2. Se infiere mediante LLM:
   - Descripción funcional del activo (qué hace en esa ubicación).
   - Estimación de tamaño/relevancia (Grande / Mediana / Pequeña) basada en señales disponibles.
   - Tags adicionales de actividad (ej: `["logística", "e-commerce", "refrigerado"]`).
3. Si hay website corporativo disponible, se hace un light scraping para validar la dirección.

---

#### PASO 4 — Scoring de Confianza (Distribución de Probabilidades)
**Responsable:** Backend → Motor probabilístico propio  
**Input:** Activos enriquecidos  
**Output:** Activos con `confidence_score` entre 0 y 1  
**Duración estimada:** ~3–5 s  

El score de confianza se calcula como una **distribución de Bernoulli ponderada** sobre señales independientes:

```python
# Señales y pesos
SIGNALS = {
    "name_match":          0.30,  # Nombre del place incluye el nombre de la empresa
    "type_match":          0.20,  # Tipo de Google Maps compatible con activo productivo
    "address_corporate":   0.15,  # Dirección coincide con info pública registral
    "website_match":       0.15,  # Website asociado es dominio corporativo
    "reviews_b2b":         0.10,  # Reviews sugieren uso B2B/industrial
    "llm_confidence":      0.10,  # Score interno del LLM en el paso de clasificación
}

def compute_confidence(asset: AssetCandidate) -> float:
    score = sum(
        weight * asset.signals.get(signal, 0)
        for signal, weight in SIGNALS.items()
    )
    # Aplicar suavizado beta para evitar extremos 0/1 duros
    alpha, beta_param = 1 + score * 10, 1 + (1 - score) * 10
    return beta.mean(alpha, beta_param)
```

Los activos con `confidence_score < 0.35` se marcan como `LOW_CONFIDENCE` y se muestran con indicador visual diferenciado en el mapa.

---

#### PASO 5 — Persistencia y Caché
**Responsable:** Backend → PostgreSQL + Redis  

- Resultados completos se persisten en PostgreSQL con extensión PostGIS.
- Se cachean en Redis con TTL de 24 horas por empresa (evita recómputo en accesos repetidos).
- El usuario puede forzar refresco con flag `force_refresh=true`.

---

## 4. API — Endpoints Principales

### `GET /api/v1/companies/search`
Búsqueda y autocompletado de empresas.

**Query params:**
- `q` (str): Texto de búsqueda (mínimo 3 caracteres)
- `limit` (int, default 10): Número de resultados

**Response:**
```json
{
  "companies": [
    {
      "id": "mercadona_es",
      "name": "Mercadona S.A.",
      "cif": "A-46103834",
      "sector": "Comercio al por menor",
      "cnae": "4711",
      "logo_url": "...",
      "headquarters": "Tavernes Blanques, Valencia"
    }
  ]
}
```

---

### `POST /api/v1/assets/analyze`
Lanza el pipeline completo de análisis.

**Body:**
```json
{
  "company_id": "mercadona_es",
  "company_name": "Mercadona S.A.",
  "force_refresh": false
}
```

**Response (si ya hay caché):**
```json
{
  "cached": true,
  "assets": [...],
  "metadata": { "last_updated": "2025-04-01T10:00:00Z", "total_assets": 47 }
}
```

**Response (si no hay caché):** → Redirige a streaming SSE.

---

### `GET /api/v1/assets/stream/{job_id}`
Streaming Server-Sent Events del progreso del pipeline.

**Eventos emitidos:**
```
event: step_start
data: {"step": 1, "name": "Buscando en Google Maps", "estimated_seconds": 15}

event: step_complete
data: {"step": 1, "name": "Buscando en Google Maps", "found": 83, "duration_ms": 12400}

event: step_start
data: {"step": 2, "name": "Clasificando activos con IA", "estimated_seconds": 25}

event: complete
data: {"assets": [...], "total": 47, "high_confidence": 38, "low_confidence": 9}

event: error
data: {"step": 2, "message": "LLM timeout, retrying..."}
```

---

### `GET /api/v1/assets/{company_id}`
Obtiene activos ya procesados de la base de datos.

**Query params:**
- `category` (str, opcional): Filtrar por categoría
- `min_confidence` (float, default 0.0): Filtrar por score mínimo
- `bbox` (str, opcional): Filtrar por bounding box `lat_min,lon_min,lat_max,lon_max`

---

## 5. Catálogo de Categorías de Activos

| Código | Categoría | Descripción | Keywords de búsqueda |
|---|---|---|---|
| `HQ` | Sede Central | Oficina principal o casa matriz | sede central, headquarter, dirección general |
| `OFF` | Oficina Regional | Delegación o sucursal administrativa | oficina, delegación, sucursal |
| `FAB` | Fábrica / Planta Industrial | Instalación de manufactura o producción | fábrica, planta, manufactura, producción |
| `LOG` | Centro Logístico | Almacén de distribución y logística | almacén, logística, distribución, centro logístico |
| `TEC` | Centro Tecnológico | I+D, laboratorio, data center | laboratorio, I+D, innovación, data center |
| `COM` | Punto de Venta / Tienda | Local comercial propio | tienda, punto de venta, store |
| `AGR` | Explotación Agrícola / Ganadera | Activo de sector primario | explotación, finca, granja |
| `ENE` | Instalación Energética | Planta fotovoltaica, eólica, subestación | planta solar, parque eólico, subestación |
| `TRA` | Infraestructura de Transporte | Puerto, terminal, estación | terminal, puerto, estación |
| `HOT` | Activo Hotelero / Turístico | Hotel, resort o activo turístico | hotel, resort, complejo turístico |
| `SAN` | Centro Sanitario | Hospital, clínica, centro médico propio | hospital, clínica, centro médico |
| `OTR` | Otro Activo Productivo | No categorizable en las anteriores | — |

---

## 6. Modelo de Datos

### Entidad `Asset`

```python
class Asset(BaseModel):
    id: str                          # UUID
    company_id: str                  # FK empresa
    name: str                        # Nombre normalizado
    raw_name: str                    # Nombre original de Google Maps
    category: AssetCategory          # Enum de categorías (Sección 5)
    subcategory: Optional[str]       # Etiqueta libre adicional
    
    # Localización
    latitude: float
    longitude: float
    address: str                     # Dirección formateada
    municipality: str
    province: str
    autonomous_community: str
    postal_code: Optional[str]
    
    # Metadatos funcionales
    description: Optional[str]       # Descripción inferida por LLM
    size_estimate: Optional[str]     # "LARGE" | "MEDIUM" | "SMALL"
    functional_tags: List[str]       # Tags de actividad
    is_headquarters: bool
    
    # Fuente y confianza
    google_place_id: str
    confidence_score: float          # 0.0 – 1.0
    confidence_tier: str             # "HIGH" | "MEDIUM" | "LOW"
    data_sources: List[str]          # ["google_maps", "llm_inference", ...]
    
    # Control
    created_at: datetime
    updated_at: datetime
    force_refreshed_at: Optional[datetime]
```

---

## 7. Interfaz de Usuario — Especificación Funcional

### 7.1 Pantalla de Búsqueda

- Campo de búsqueda con **autocompletado** (debounce 300ms, mínimo 3 caracteres).
- Cada sugerencia muestra: logo de empresa (si disponible), nombre oficial, sector y ciudad de sede.
- Diseño limpio tipo buscador, centrado en pantalla, con fondo oscuro y tipografía profesional.

### 7.2 Pantalla de Carga (Processing View)

Al iniciar el análisis, se muestra una pantalla de carga inmersiva con:

- **Barra de progreso global** con porcentaje acumulado.
- **Lista de pasos** con estados visuales: pendiente / en curso (animado) / completado / error.
- Para cada paso en curso se muestra:
  - Nombre del paso.
  - Tiempo estimado restante (calculado dinámicamente con los eventos SSE).
  - Contador de resultados parciales (ej: "83 ubicaciones encontradas").
- **Log de actividad en tiempo real** (últimas 5 líneas, scroll automático).
- Estética: dark mode, colores accent corporativos, iconografía coherente.

### 7.3 Vista Principal — Mapa Interactivo

Una vez completado el análisis:

**Panel izquierdo (30% del ancho):**
- Nombre y logo de la empresa analizada.
- Resumen estadístico: total activos, activos por categoría, cobertura geográfica.
- Lista de activos con scroll, buscable y filtrable.
- Cada ítem muestra: icono de categoría · nombre · municipio · badge de confianza.
- Click en ítem → centra mapa y abre popup del activo.

**Panel derecho (70% del ancho) — Mapa:**
- Mapa interactivo con marcadores agrupados por clustering (Leaflet.markercluster).
- Cada marcador usa icono diferenciado por categoría de activo.
- Marcadores con `confidence_tier: LOW` se muestran semitransparentes.
- Click en marcador → popup con:
  - Nombre del activo.
  - Categoría e icono.
  - Dirección completa.
  - Descripción inferida.
  - Score de confianza (barra visual).
  - Tags funcionales.
  - Enlace a Google Maps.

**Controles del mapa:**
- Filtro por categoría (checkboxes en overlay).
- Filtro por nivel de confianza (slider).
- Toggle clustering.
- Botón de exportar a CSV / GeoJSON.
- Selector de capa base (callejero / satélite / topográfico).

---

## 8. Ciclo de Vida del Desarrollo de IA Generativa

En cumplimiento de los requisitos del TFM, el proyecto sigue las fases establecidas del ciclo de vida de IA generativa:

### 8.1 Definición del Problema y Casos de Uso
- Identificación de la tarea: extracción y estructuración de información geoespacial empresarial.
- Definición de métricas de éxito: precision/recall de activos identificados vs. ground truth manual.
- Establecimiento de criterios de calidad mínimos por caso de uso.

### 8.2 Selección y Diseño del Modelo
- Elección de arquitectura: LLMs de propósito general (GPT-4o, Claude 3.5 Sonnet) via LiteLLM como abstracción.
- Justificación del modelo: capacidad de comprensión contextual y generación de JSON estructurado.
- Diseño de prompts: prompt engineering sistemático con ejemplos few-shot para filtrado y clasificación.

### 8.3 Preparación de Datos
- Limpieza y normalización de resultados crudos de Google Maps.
- Construcción de dataset de evaluación con anotación manual para 10 empresas piloto (ground truth).
- Estrategia de deduplicación por `place_id` y normalización de nombres.

### 8.4 Desarrollo e Implementación
- Prompt versioning en ficheros `.yaml` con control de versiones Git.
- Pipeline modular y desacoplado: cada paso es independiente y testeable.
- Paralelismo controlado con semáforos para no superar rate limits de APIs.

### 8.5 Evaluación y Validación
- Métricas automáticas: precision, recall, F1 sobre dataset de ground truth.
- Evaluación de confianza: calibración del `confidence_score` vs. acierto real.
- Evaluación LLM-as-judge: uso de un LLM externo para evaluar calidad de clasificaciones.
- Análisis de errores: categorización de falsos positivos y falsos negativos.

### 8.6 Despliegue y Monitorización
- Contenerización completa con Docker Compose.
- Logging estructurado (JSON) de todas las llamadas a LLMs: prompt, respuesta, latencia, coste estimado.
- Sistema de caché con TTL para evitar llamadas redundantes.
- Health checks automáticos de todos los servicios.

### 8.7 Mejora Continua
- Feedback loop: el usuario puede marcar activos como incorrectos desde el frontend.
- Los marcajes se almacenan y se usan para refinar los prompts en iteraciones futuras.
- Registro de versiones de prompts y sus métricas asociadas.

---

## 9. Estructura del Repositorio

```
geoassets-intelligence/
│
├── docker-compose.yml
├── .env.example
├── README.md
│
├── frontend/                        # Vue 3 + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar.vue
│   │   │   ├── ProcessingView.vue   # Pantalla de carga con SSE
│   │   │   ├── AssetMap.vue         # Mapa principal (Leaflet)
│   │   │   ├── AssetSidebar.vue     # Panel lateral de activos
│   │   │   └── AssetPopup.vue       # Popup de detalle
│   │   ├── stores/
│   │   │   ├── companies.ts
│   │   │   └── assets.ts
│   │   ├── services/
│   │   │   ├── api.ts               # Cliente HTTP
│   │   │   └── sse.ts               # Cliente SSE
│   │   └── views/
│   │       ├── HomeView.vue
│   │       └── AnalysisView.vue
│   └── Dockerfile
│
├── backend/                         # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── companies.py
│   │   │   ├── assets.py
│   │   │   └── stream.py
│   │   ├── pipeline/
│   │   │   ├── orchestrator.py      # Coordinador del pipeline
│   │   │   ├── steps/
│   │   │   │   ├── step0_identify.py
│   │   │   │   ├── step1_maps.py
│   │   │   │   ├── step2_llm_filter.py
│   │   │   │   ├── step3_enrich.py
│   │   │   │   └── step4_scoring.py
│   │   │   └── models.py            # Pydantic models
│   │   ├── prompts/                 # Prompts versionados
│   │   │   ├── v1/
│   │   │   │   ├── filter_assets.yaml
│   │   │   │   └── classify_asset.yaml
│   │   │   └── v2/
│   │   ├── services/
│   │   │   ├── google_maps.py
│   │   │   ├── llm_client.py        # Wrapper LiteLLM
│   │   │   └── cache.py             # Redis client
│   │   └── db/
│   │       ├── models.py            # SQLAlchemy + PostGIS
│   │       └── migrations/
│   ├── tests/
│   │   ├── test_pipeline.py
│   │   ├── test_scoring.py
│   │   └── evaluation/
│   │       └── ground_truth.json
│   └── Dockerfile
│
└── docs/
    ├── documentacion_funcional_tecnica.md   # Este documento
    └── evaluation_results/
```

---

## 10. Variables de Entorno

```env
# APIs externas
GOOGLE_MAPS_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# LiteLLM
LITELLM_MODEL=gpt-4o                 # Modelo por defecto
LITELLM_FALLBACK_MODEL=claude-3-5-sonnet-20241022
AGENT_LITELLM_MODEL=bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
AGENT_LITELLM_FALLBACK_MODEL=
PIPELINE_LITELLM_MODEL=bedrock/openai.gpt-oss-120b-1:0
PIPELINE_LITELLM_FALLBACK_MODEL=
LITELLM_MAX_WORKERS=5                # Workers paralelos máximos
LITELLM_TIMEOUT=30                   # Timeout por llamada (s)

# Base de datos
POSTGRES_HOST=postgres
POSTGRES_DB=geoassets
POSTGRES_USER=geoassets
POSTGRES_PASSWORD=...

# Redis
REDIS_HOST=redis
REDIS_TTL_SECONDS=86400              # 24h caché por empresa

# Configuración de pipeline
MAPS_CITIES_COVERAGE=madrid,barcelona,valencia,sevilla,zaragoza,bilbao,malaga,murcia,palma,las-palmas
CONFIDENCE_THRESHOLD_HIGH=0.65
CONFIDENCE_THRESHOLD_MEDIUM=0.35
```

---

## 11. Limitaciones Conocidas y Consideraciones

1. **Cobertura de Google Maps:** Google Maps no garantiza la indexación completa de activos industriales o logísticos en zonas rurales. Empresas de sectores primarios o con activos muy dispersos pueden tener cobertura inferior.

2. **Rate limits:** La Google Maps Places API tiene cuotas por proyecto. Para análisis de muchas empresas consecutivas se recomienda implementar cola de trabajos con Celery.

3. **Alucinaciones LLM:** Los LLMs pueden clasificar incorrectamente lugares ambiguos. El sistema de scoring de confianza mitiga esto, pero no lo elimina. Se recomienda revisión humana para activos con confianza baja.

4. **Actualización de datos:** Los resultados se cachean 24 horas. Empresas en reestructuración activa pueden tener datos desfasados; usar `force_refresh=true` para actualizaciones críticas.

5. **Empresas pequeñas o sin presencia digital:** El sistema está optimizado para empresas con presencia verificable en Google Maps. Microempresas o negocios sin perfil de Google Business pueden no aparecer.

6. **Coste de API:** Cada análisis completo genera entre 50–200 llamadas a Google Maps y 10–30 llamadas a LLMs. Se recomienda monitorizar el coste por empresa para proyectos de escala.

---

*Documento vivo — versión 1.0 · Abril 2025*