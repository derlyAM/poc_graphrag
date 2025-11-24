# 🐳 Docker Quick Start Guide

## Inicio Rápido (< 5 minutos)

### 1. Prerequisitos

```bash
# Verificar Docker instalado
docker --version
docker-compose --version
```

### 2. Configurar API Key

```bash
# Editar archivo .env
nano .env

# Actualizar esta línea con tu API key real:
OPENAI_API_KEY=sk-tu-clave-aqui
```

### 3. Desplegar

```bash
# Construir imágenes
./scripts/deploy_docker.sh build

# Iniciar servicios
./scripts/deploy_docker.sh start

# Ver estado
./scripts/deploy_docker.sh status
```

### 4. Acceder

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Streamlit UI** | http://localhost:8501 | Interfaz principal |
| **API Docs** | http://localhost:8000/docs | Documentación Swagger |
| **Qdrant** | http://localhost:6333/dashboard | Dashboard de vectores |

---

## Comandos Útiles

```bash
# Ver logs en tiempo real
./scripts/deploy_docker.sh logs

# Verificar estado de servicios
./scripts/deploy_docker.sh status

# Reiniciar servicios
./scripts/deploy_docker.sh restart

# Detener servicios
./scripts/deploy_docker.sh stop

# Limpiar (mantiene datos)
./scripts/deploy_docker.sh clean

# Rebuild completo (tras cambios de código)
./scripts/deploy_docker.sh rebuild
```

---

## Test Rápido

### Test de API

```bash
# Health check
curl http://localhost:8000/health

# Listar documentos
curl http://localhost:8000/api/v1/documents

# Query RAG
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué es un OCAD?",
    "area": "sgr",
    "config": {
      "top_k_rerank": 3
    }
  }'
```

### Test de Streamlit

Abrir http://localhost:8501 en tu navegador y hacer una consulta.

---

## Troubleshooting

### "Cannot connect to Docker daemon"

```bash
# Iniciar Docker Desktop (macOS/Windows)
# O iniciar servicio Docker (Linux)
sudo systemctl start docker
```

### ".env file contains placeholder API key"

```bash
# Editar .env y agregar tu API key real
nano .env
# Cambiar: OPENAI_API_KEY=your_openai_api_key_here
# Por:     OPENAI_API_KEY=sk-tu-clave-real
```

### "Service unhealthy"

```bash
# Ver logs del servicio
docker-compose logs api

# Los servicios pueden tardar 40-60 segundos en estar listos
# Esperar y verificar nuevamente
./scripts/deploy_docker.sh status
```

### "Port already in use"

```bash
# Detener servicios locales que usan los puertos
# API usa puerto 8000
# Streamlit usa puerto 8501
# Qdrant usa puerto 6333

# Ver qué está usando el puerto (macOS/Linux)
lsof -i :8000
lsof -i :8501
lsof -i :6333

# Matar proceso
kill -9 <PID>
```

---

## Documentación Completa

Para más detalles, consultar:
- **Despliegue Docker**: `docs/DOCKER_DEPLOYMENT.md`
- **Resumen de Dockerización**: `docs/DOCKERIZATION_SUMMARY.md`
- **API Documentation**: `docs/API_DOCUMENTATION.md`

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│              Docker Network: rag_network                     │
│                                                               │
│  ┌──────────────┐       ┌──────────────┐   ┌──────────────┐│
│  │   Qdrant     │◄──────┤     API      │   │  Streamlit   ││
│  │ (Vector DB)  │       │  (FastAPI)   │   │     (UI)     ││
│  │              │       │              │   │              ││
│  │ Port: 6333   │       │ Port: 8000   │   │ Port: 8501   ││
│  └──────┬───────┘       └──────┬───────┘   └──────┬───────┘│
│         │                      │                    │        │
│         └──────────────────────┴────────────────────┘        │
│                   Shared Volumes:                            │
│              ./storage  ./logs  ./data                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Recursos del Sistema

- **RAM**: 4.5 GB (recomendado 8 GB)
- **CPU**: 2.5 cores (recomendado 4 cores)
- **Disco**: 3.6 GB (recomendado 10 GB)

---

**Versión**: 1.3.0
**Fecha**: 2025-11-24
**Estado**: ✅ Producción
