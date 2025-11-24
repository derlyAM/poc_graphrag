# Docker Deployment Guide

## Descripción

Esta guía documenta el despliegue completo del sistema RAG utilizando Docker y Docker Compose. La aplicación está completamente dockerizada con tres servicios principales:

1. **Qdrant** - Base de datos vectorial
2. **API** - Servicio REST API (FastAPI)
3. **Streamlit** - Interfaz de usuario web

---

## Arquitectura de Servicios

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network: rag_network              │
│                                                               │
│  ┌───────────────┐      ┌───────────────┐   ┌─────────────┐│
│  │   Qdrant      │◄─────┤   API         │   │  Streamlit  ││
│  │  (Vector DB)  │      │  (FastAPI)    │   │    (UI)     ││
│  │               │      │               │   │             ││
│  │  Port: 6333   │      │  Port: 8000   │   │ Port: 8501  ││
│  └───────┬───────┘      └───────┬───────┘   └─────┬───────┘│
│          │                      │                   │        │
│          │                      │                   │        │
│  ┌───────▼──────────────────────▼───────────────────▼──────┐│
│  │              Shared Volumes                              ││
│  │  ./storage  ./logs  ./data                               ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Requisitos Previos

### Software Requerido

```bash
docker --version      # Docker 20.10+
docker-compose --version  # Docker Compose 1.29+
```

### Recursos del Sistema

- **RAM**: 4.5 GB mínimo (8 GB recomendado)
- **CPU**: 2.5 cores mínimo (4 cores recomendado)
- **Disco**: 3.6 GB mínimo (10 GB recomendado)

---

## Instalación y Configuración

### 1. Configurar Variables de Entorno

Asegúrate de que tu archivo `.env` exista con la configuración correcta:

```bash
# Verificar que .env existe
ls -la .env

# Si no existe, crear desde plantilla
cp .env.docker .env
```

**IMPORTANTE**: Actualiza tu `OPENAI_API_KEY` en el archivo `.env`:

```bash
# Editar .env
nano .env  # o vim .env

# Actualizar esta línea:
OPENAI_API_KEY=sk-tu-clave-real-aqui
```

### 2. Preparar Directorios

Los siguientes directorios deben existir y tener permisos correctos:

```bash
# Crear directorios si no existen
mkdir -p storage/qdrant_storage
mkdir -p logs
mkdir -p data

# Verificar permisos (opcional pero recomendado)
chmod -R 755 storage logs data
```

---

## Comandos de Despliegue

### Build de Imágenes

Construir todas las imágenes de los servicios:

```bash
# Build de todos los servicios
docker-compose build

# Build de un servicio específico
docker-compose build api
docker-compose build streamlit

# Build sin caché (útil para forzar reinstalación)
docker-compose build --no-cache
```

### Iniciar Servicios

```bash
# Iniciar todos los servicios en modo detached (background)
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f api
docker-compose logs -f streamlit
docker-compose logs -f qdrant

# Iniciar solo algunos servicios
docker-compose up -d qdrant api
```

### Detener Servicios

```bash
# Detener todos los servicios (mantiene volúmenes)
docker-compose stop

# Detener y eliminar contenedores (mantiene volúmenes)
docker-compose down

# Detener, eliminar contenedores Y volúmenes (⚠️ BORRA DATOS)
docker-compose down -v
```

### Verificar Estado

```bash
# Ver estado de servicios
docker-compose ps

# Ver uso de recursos
docker stats

# Verificar health checks
docker inspect rag_api | grep -A 10 Health
docker inspect rag_streamlit | grep -A 10 Health
docker inspect qdrant_vectordb | grep -A 10 Health
```

---

## Acceso a los Servicios

Una vez que todos los servicios estén levantados (status: healthy):

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Qdrant UI** | http://localhost:6333/dashboard | Panel de Qdrant |
| **API Docs** | http://localhost:8000/docs | Swagger UI (OpenAPI) |
| **API ReDoc** | http://localhost:8000/redoc | Documentación ReDoc |
| **Health Check** | http://localhost:8000/health | Estado de la API |
| **Streamlit UI** | http://localhost:8501 | Interfaz principal |

### Verificar que los Servicios Están Listos

```bash
# Health check de API
curl http://localhost:8000/health

# Health check de Qdrant
curl http://localhost:6333/health

# Health check de Streamlit
curl http://localhost:8501/_stcore/health
```

Deberías ver respuestas exitosas de todos los servicios.

---

## Configuración de Entorno en Docker

### Variables de Entorno Importantes

Las siguientes variables se configuran automáticamente en `docker-compose.yml`:

```yaml
# Conexión a Qdrant (CRÍTICO)
QDRANT_HOST=qdrant  # Nombre del servicio, NO "localhost"
QDRANT_PORT=6333

# OpenAI API (desde .env)
OPENAI_API_KEY=${OPENAI_API_KEY}

# Modelos y configuración (desde .env con defaults)
EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-small}
LLM_MODEL=${LLM_MODEL:-gpt-4o-mini}
TOP_K_RETRIEVAL=${TOP_K_RETRIEVAL:-20}
TOP_K_RERANK=${TOP_K_RERANK:-5}
```

### Volúmenes Montados

```yaml
volumes:
  - ./storage:/app/storage     # Datos de Qdrant (lectura/escritura)
  - ./logs:/app/logs           # Logs de aplicación (lectura/escritura)
  - ./data:/app/data:ro        # PDFs de entrada (solo lectura)
```

---

## Gestión de Logs

### Ver Logs en Tiempo Real

```bash
# Todos los servicios
docker-compose logs -f

# Solo API
docker-compose logs -f api

# Solo Streamlit
docker-compose logs -f streamlit

# Últimas 100 líneas de API
docker-compose logs --tail=100 api
```

### Logs Persistidos

Los logs también se guardan en el directorio `./logs/`:

```bash
# Ver logs de la API
tail -f logs/api.log

# Ver logs de Streamlit
tail -f logs/streamlit.log

# Ver logs de aplicación general
tail -f logs/app.log
```

---

## Debugging y Troubleshooting

### Entrar a un Contenedor

```bash
# Shell interactivo en el contenedor de API
docker exec -it rag_api /bin/bash

# Shell en Streamlit
docker exec -it rag_streamlit /bin/bash

# Ejecutar comando específico
docker exec rag_api ls -la /app/storage
docker exec rag_api python -c "from src.config import config; print(config.qdrant.host)"
```

### Verificar Conectividad Entre Servicios

```bash
# Desde API, verificar conexión a Qdrant
docker exec rag_api curl -s http://qdrant:6333/health

# Verificar DNS dentro del contenedor
docker exec rag_api ping -c 3 qdrant
docker exec rag_streamlit ping -c 3 qdrant
```

### Reiniciar un Servicio Específico

```bash
# Reiniciar API
docker-compose restart api

# Reiniciar Streamlit
docker-compose restart streamlit

# Forzar recreación (útil tras cambios de código)
docker-compose up -d --force-recreate api
```

### Problemas Comunes

#### 1. "Cannot connect to Qdrant"

**Causa**: API/Streamlit intentan conectar a `localhost` en vez de `qdrant`

**Solución**:
```bash
# Verificar que QDRANT_HOST está configurado correctamente
docker exec rag_api printenv | grep QDRANT_HOST
# Debería mostrar: QDRANT_HOST=qdrant

# Si no, revisar docker-compose.yml
```

#### 2. "Service unhealthy"

**Causa**: El health check falla (servicio no responde)

**Solución**:
```bash
# Ver logs del servicio
docker-compose logs api

# Verificar que el servicio está escuchando
docker exec rag_api netstat -tuln | grep 8000

# Dar más tiempo al start period (editar docker-compose.yml)
healthcheck:
  start_period: 60s  # Aumentar si modelos tardan en cargar
```

#### 3. "Permission denied" en volúmenes

**Causa**: Permisos incorrectos en directorios montados

**Solución**:
```bash
# Verificar permisos
ls -la storage logs data

# Dar permisos (cuidado con permisos excesivos)
chmod -R 755 storage logs data

# Si persiste, verificar usuario en contenedor
docker exec rag_api id
```

#### 4. Cambios en código no se reflejan

**Causa**: Imágenes no se reconstruyeron

**Solución**:
```bash
# Rebuild forzado sin caché
docker-compose build --no-cache api streamlit

# Reiniciar con recreación
docker-compose up -d --force-recreate
```

---

## Actualizar la Aplicación

Cuando hagas cambios en el código:

```bash
# 1. Detener servicios
docker-compose down

# 2. Rebuild imágenes
docker-compose build --no-cache

# 3. Reiniciar servicios
docker-compose up -d

# 4. Verificar logs
docker-compose logs -f api streamlit
```

---

## Monitoreo de Recursos

### Ver Uso de CPU/RAM en Tiempo Real

```bash
docker stats

# Formato específico
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Limitar Recursos (Opcional)

Editar `docker-compose.yml`:

```yaml
api:
  # ... otras configuraciones
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

---

## Backup y Restauración

### Backup de Datos de Qdrant

```bash
# Método 1: Copiar directorio storage
tar -czf backup_qdrant_$(date +%Y%m%d).tar.gz storage/qdrant_storage/

# Método 2: Snapshot de Qdrant (si es compatible con tu versión)
curl -X POST http://localhost:6333/collections/normativa_sgr/snapshots
```

### Restaurar Datos

```bash
# 1. Detener servicios
docker-compose down

# 2. Restaurar storage
tar -xzf backup_qdrant_20250124.tar.gz

# 3. Reiniciar
docker-compose up -d
```

---

## Limpieza de Sistema

### Limpiar Contenedores e Imágenes No Usados

```bash
# Limpiar contenedores detenidos
docker container prune -f

# Limpiar imágenes sin uso
docker image prune -a -f

# Limpiar todo (contenedores, imágenes, volúmenes, networks)
docker system prune -a --volumes -f  # ⚠️ CUIDADO: Borra TODO
```

### Resetear Todo (Fresh Start)

```bash
# 1. Detener y eliminar todo
docker-compose down -v

# 2. Limpiar imágenes del proyecto
docker rmi rag_api rag_streamlit

# 3. Rebuild desde cero
docker-compose build --no-cache

# 4. Iniciar
docker-compose up -d
```

---

## Producción: Consideraciones Adicionales

### Security Hardening

1. **No exponer puertos innecesarios**: Comentar ports de Qdrant si no necesitas acceso externo
2. **Usar secrets de Docker**: Para `OPENAI_API_KEY`
3. **Non-root user**: Agregar usuario no privilegiado en Dockerfiles
4. **Escaneo de vulnerabilidades**: `docker scan rag_api`

### Escalabilidad

- Usar **nginx** como reverse proxy
- Implementar **rate limiting**
- Migrar a **Kubernetes** para multi-nodo
- Usar **Redis** para caché y queue

### Monitoreo Avanzado

- **Prometheus + Grafana**: Métricas
- **ELK Stack**: Logs centralizados
- **Jaeger**: Distributed tracing

---

## Comandos Quick Reference

```bash
# === BUILD ===
docker-compose build                    # Build all
docker-compose build --no-cache         # Force rebuild

# === START/STOP ===
docker-compose up -d                    # Start all (detached)
docker-compose down                     # Stop all
docker-compose restart api              # Restart specific service

# === LOGS ===
docker-compose logs -f                  # All logs (follow)
docker-compose logs -f api              # API logs
docker-compose logs --tail=100 api      # Last 100 lines

# === STATUS ===
docker-compose ps                       # Service status
docker stats                            # Resource usage

# === DEBUGGING ===
docker exec -it rag_api /bin/bash       # Interactive shell
curl http://localhost:8000/health       # Health check

# === CLEANUP ===
docker-compose down -v                  # Stop + remove volumes
docker system prune -a -f               # Clean everything
```

---

## Recursos y Referencias

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Qdrant Docker Setup](https://qdrant.tech/documentation/guides/installation/#docker)

---

**Versión**: 1.3.0
**Última actualización**: 2025-11-24
**Autor**: Sistema RAG - Documentos Normativos
