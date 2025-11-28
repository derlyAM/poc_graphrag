# 🚀 Guía Completa de Instalación y Pruebas

**Versión**: 1.3.0  
**Última actualización**: 2025-01-15

Esta guía te llevará paso a paso para instalar, configurar y probar el sistema RAG completo.

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#1-requisitos-previos)
2. [Instalación](#2-instalación)
3. [Configuración](#3-configuración)
4. [Iniciar Servicios](#4-iniciar-servicios)
5. [Ingestar Documentos](#5-ingestar-documentos)
6. [Probar la API REST](#6-probar-la-api-rest)
7. [Probar Streamlit UI](#7-probar-streamlit-ui)
8. [Probar con Scripts](#8-probar-con-scripts)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Requisitos Previos

### Software Necesario

✅ **Python 3.11 o superior**
```bash
# Verificar versión
python --version
# o
python3 --version
```

✅ **Docker Desktop** (para Qdrant)
- Descargar: https://www.docker.com/products/docker-desktop
- Verificar instalación:
```bash
docker --version
docker-compose --version
```

✅ **Git** (opcional, si clonas el repositorio)
```bash
git --version
```

✅ **API Key de OpenAI**
- Obtener en: https://platform.openai.com/api-keys
- Formato: `sk-...`

---

## 2. Instalación

### Paso 2.1: Clonar o Descargar el Proyecto

Si tienes el proyecto en un repositorio:
```bash
git clone <url-del-repositorio>
cd poc_graphrag
```

Si ya tienes el proyecto, navega a la carpeta:
```bash
cd C:\Users\Asus\Documents\Personal\proyecto-integrador\poc_graphrag
```

### Paso 2.2: Crear Entorno Virtual

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Verificar que el entorno está activo:**
- Windows: Verás `(venv)` al inicio de la línea de comandos
- Linux/Mac: Verás `(venv)` al inicio de la línea de comandos

### Paso 2.3: Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Tiempo estimado**: 2-5 minutos (depende de tu conexión)

**Verificar instalación:**
```bash
python -c "import fastapi, streamlit, openai, qdrant_client; print('✅ Todas las dependencias instaladas')"
```

---

## 3. Configuración

### Paso 3.1: Crear Archivo `.env`

Crea un archivo llamado `.env` en la raíz del proyecto:

**Windows (PowerShell):**
```powershell
New-Item -Path .env -ItemType File
```

**Linux/Mac:**
```bash
touch .env
```

### Paso 3.2: Configurar Variables de Entorno

Abre el archivo `.env` y agrega tu API key de OpenAI:

```env
# OpenAI API Key (REQUERIDO)
OPENAI_API_KEY=sk-tu-api-key-aqui

# Qdrant Configuration (Opcional - valores por defecto)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=normativa_sgr
QDRANT_USE_MEMORY=false

# Embedding Model (Opcional)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# LLM Configuration (Opcional)
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=800

# Retrieval Configuration (Opcional)
TOP_K_RETRIEVAL=20
TOP_K_RERANK=5
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Re-ranking Model (Opcional)
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2

# Logging (Opcional)
LOG_LEVEL=INFO
```

**⚠️ IMPORTANTE**: Reemplaza `sk-tu-api-key-aqui` con tu API key real de OpenAI.

**Verificar que el archivo existe:**
```bash
# Windows
dir .env

# Linux/Mac
ls -la .env
```

---

## 4. Iniciar Servicios

### Paso 4.1: Iniciar Qdrant (Base de Datos Vectorial)

**Asegúrate de que Docker Desktop esté corriendo**

```bash
docker-compose up -d qdrant
```

**Verificar que Qdrant está corriendo:**
```bash
# Verificar contenedor
docker ps | grep qdrant

# Verificar salud
curl http://localhost:6333/health
```

**Si todo está bien, verás:**
```json
{"title":"qdrant - vector search engine","version":"1.12.5"}
```

**Dashboard de Qdrant:**
- URL: http://localhost:6333/dashboard
- Puedes ver las colecciones y datos desde aquí

---

## 5. Ingestar Documentos

### Paso 5.1: Preparar Documentos PDF

Crea una carpeta `data/` en la raíz del proyecto si no existe:

```bash
# Windows
mkdir data

# Linux/Mac
mkdir -p data
```

Coloca tus archivos PDF en la carpeta `data/`:
```
poc_graphrag/
├── data/
│   ├── documento1.pdf
│   ├── documento2.pdf
│   └── ...
```

### Paso 5.2: Ejecutar Script de Ingestión

```bash
python scripts/01_ingest_pdfs.py
```

**Este proceso:**
1. Extrae texto de los PDFs
2. Divide en chunks
3. Genera embeddings
4. Carga en Qdrant

**Tiempo estimado**: 2-10 minutos (depende del tamaño de los PDFs)

**Salida esperada:**
```
Iniciando ingestión de documentos...
Procesando: documento1.pdf
  - Chunks creados: 150
  - Embeddings generados: 150
  - Cargados en Qdrant: 150
✅ Ingestión completada
```

**Verificar que los documentos se cargaron:**
```bash
# Verificar colección en Qdrant
curl http://localhost:6333/collections/normativa_sgr
```

---

## 6. Probar la API REST

### Paso 6.1: Iniciar el Servidor API

**Opción A: Script (Recomendado)**

**Windows:**
```bash
scripts\start_api.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/start_api.sh
./scripts/start_api.sh
```

**Opción B: Manual**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verás:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Paso 6.2: Verificar Health Check

**Opción A: Navegador**
Abre: http://localhost:8000/health

**Opción B: cURL**
```bash
curl http://localhost:8000/health
```

**Opción C: Python**
```python
import requests
response = requests.get("http://localhost:8000/health")
print(response.json())
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "version": "1.3.0",
  "timestamp": "2025-01-15T10:30:00",
  "services": {
    "qdrant": "connected",
    "openai": "available"
  }
}
```

### Paso 6.3: Ver Documentación Interactiva

Abre en tu navegador:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Desde aquí puedes probar todos los endpoints directamente.

### Paso 6.4: Probar Endpoint de Consulta

**Opción A: cURL**
```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"¿Qué es un OCAD?\", \"area\": \"sgr\"}"
```

**Opción B: Python**
```python
import requests

url = "http://localhost:8000/api/v1/rag/query"
payload = {
    "question": "¿Qué es un OCAD?",
    "area": "sgr"
}

response = requests.post(url, json=payload)
result = response.json()

print("Respuesta:", result["answer"])
print("Fuentes:", result["num_sources"])
print("Costo:", f"${result['metrics']['total_cost']:.6f}")
```

**Opción C: Desde Swagger UI**
1. Ve a http://localhost:8000/docs
2. Expande `POST /api/v1/rag/query`
3. Click en "Try it out"
4. Modifica el JSON:
```json
{
  "question": "¿Qué es un OCAD?",
  "area": "sgr"
}
```
5. Click en "Execute"
6. Verás la respuesta completa

### Paso 6.5: Probar Otros Endpoints

**Listar documentos:**
```bash
curl http://localhost:8000/api/v1/documents
```

**Obtener estado del sistema:**
```bash
curl http://localhost:8000/api/v1/status
```

**Ver detalle de un documento:**
```bash
# Reemplaza 'documento_id' con un ID real
curl http://localhost:8000/api/v1/documents/documento_id
```

---

## 7. Probar Streamlit UI

### Paso 7.1: Iniciar Streamlit

En una **nueva terminal** (mantén la API corriendo en otra):

```bash
# Activar entorno virtual (si no está activo)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Iniciar Streamlit
streamlit run app/streamlit_app.py
```

**Verás:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

### Paso 7.2: Usar la Interfaz Web

1. **Abre tu navegador** en: http://localhost:8501

2. **Selecciona el área** en el sidebar:
   - Sistema General de Regalías (SGR)
   - Inteligencia Artificial
   - General

3. **Escribe una pregunta** en el campo de búsqueda:
   - "¿Qué es un OCAD?"
   - "¿Cuáles son los requisitos para viabilizar un proyecto?"
   - "Explica el proceso de ajuste de proyectos"

4. **Click en "🔍 Buscar"**

5. **Verás:**
   - Respuesta generada
   - Fuentes consultadas
   - Métricas de performance
   - Costo de la consulta

### Paso 7.3: Probar Chatbot Conversacional

1. En la interfaz de Streamlit, ve a la página **"Chatbot IA"** (en el sidebar)

2. Inicia una conversación:
   - "Hola, ¿qué es un OCAD?"
   - "¿Puedes darme más detalles?"
   - "¿Qué documentos mencionan esto?"

3. El chatbot mantendrá el contexto de la conversación

---

## 8. Probar con Scripts

### Paso 8.1: Prueba Rápida

```bash
python scripts/test_quick.py
```

**Salida esperada:**
```
Inicializando pipeline...
Pregunta: ¿Qué es un OCAD?

================================================================================
RESPUESTA:
================================================================================
El OCAD (Órgano Colegiado de Administración y Decisión) es...

================================================================================
MÉTRICAS:
================================================================================
Tiempo: 6.23s
Chunks: 5
Costo: $0.000234
```

### Paso 8.2: Prueba Completa

```bash
python scripts/test_pipeline.py
```

Este script ejecuta múltiples queries y muestra estadísticas.

### Paso 8.3: Otros Scripts de Prueba

```bash
# Probar búsqueda vectorial
python scripts/test_retrieval.py

# Probar multihop
python scripts/test_multihop.py

# Probar HyDE
python scripts/test_hyde.py

# Probar chatbot
python scripts/test_chatbot_shared_pipeline.py
```

---

## 9. Troubleshooting

### ❌ Error: "Cannot connect to Qdrant"

**Solución:**
```bash
# Verificar que Docker está corriendo
docker ps

# Verificar que Qdrant está corriendo
docker ps | grep qdrant

# Si no está corriendo, iniciarlo
docker-compose up -d qdrant

# Ver logs
docker-compose logs qdrant
```

### ❌ Error: "OPENAI_API_KEY is required"

**Solución:**
1. Verifica que el archivo `.env` existe
2. Verifica que tiene la línea: `OPENAI_API_KEY=sk-...`
3. Verifica que la API key es válida (empieza con `sk-`)
4. Reinicia el servidor después de modificar `.env`

### ❌ Error: "No module named 'api'"

**Solución:**
```bash
# Asegúrate de estar en la raíz del proyecto
cd C:\Users\Asus\Documents\Personal\proyecto-integrador\poc_graphrag

# Verifica que el entorno virtual está activo
# Windows: deberías ver (venv) al inicio
# Linux/Mac: deberías ver (venv) al inicio

# Reinstala dependencias
pip install -r requirements.txt
```

### ❌ Error: "Collection 'normativa_sgr' not found"

**Solución:**
```bash
# Necesitas ingestar documentos primero
python scripts/01_ingest_pdfs.py
```

### ❌ Error: "Port 8000 already in use"

**Solución:**
```bash
# Windows: Encontrar proceso usando el puerto
netstat -ano | findstr :8000

# Linux/Mac: Encontrar proceso
lsof -i :8000

# Matar el proceso o usar otro puerto
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### ❌ Error: "Port 8501 already in use"

**Solución:**
```bash
# Streamlit te permite usar otro puerto automáticamente
# O especifica uno manualmente:
streamlit run app/streamlit_app.py --server.port 8502
```

### ❌ Error: "No documents found in data/"

**Solución:**
1. Crea la carpeta `data/` si no existe
2. Coloca archivos PDF en `data/`
3. Ejecuta: `python scripts/01_ingest_pdfs.py`

### ❌ Error: "Docker daemon is not running"

**Solución:**
1. Abre Docker Desktop
2. Espera a que inicie completamente
3. Verifica con: `docker ps`

---

## ✅ Checklist de Verificación

Usa este checklist para verificar que todo está funcionando:

- [ ] Python 3.11+ instalado
- [ ] Docker Desktop instalado y corriendo
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Archivo `.env` creado con `OPENAI_API_KEY`
- [ ] Qdrant corriendo (`docker-compose up -d qdrant`)
- [ ] Qdrant saludable (`curl http://localhost:6333/health`)
- [ ] Documentos ingeridos (`python scripts/01_ingest_pdfs.py`)
- [ ] API corriendo (`uvicorn api.main:app`)
- [ ] Health check OK (`curl http://localhost:8000/health`)
- [ ] Query funciona (`POST /api/v1/rag/query`)
- [ ] Streamlit corriendo (`streamlit run app/streamlit_app.py`)
- [ ] Interfaz web accesible (http://localhost:8501)

---

## 🎯 Próximos Pasos

Una vez que todo esté funcionando:

1. **Explora la documentación**:
   - `docs/GUIA_ENDPOINTS_API.md` - Guía completa de endpoints
   - `docs/STACK_TECNOLOGICO.md` - Stack tecnológico
   - `docs/ARQUITECTURA_TECNICA.md` - Arquitectura del sistema

2. **Prueba diferentes tipos de queries**:
   - Consultas simples
   - Consultas complejas (multihop)
   - Consultas con terminología incorrecta (HyDE)

3. **Sube tus propios documentos**:
   - Usa la API: `POST /api/v1/documents/ingest`
   - O colócalos en `data/` y ejecuta el script de ingestión

4. **Integra con tu aplicación**:
   - Usa los endpoints REST
   - Consulta la documentación en `/docs`

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs:
   - API: `logs/api.log`
   - Streamlit: `logs/streamlit.log`
   - Qdrant: `docker-compose logs qdrant`

2. Verifica la documentación:
   - `README.md`
   - `docs/` (varios archivos)

3. Revisa los issues conocidos en el repositorio

---

**¡Listo! 🎉 Ahora deberías tener el sistema RAG completamente funcional.**

**Última actualización**: 2025-01-15  
**Versión**: 1.3.0





