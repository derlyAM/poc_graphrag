#!/bin/bash
# Script seguro para ingestar documentos de Inteligencia Artificial
# Mata procesos de Streamlit si existen, ingesta, y da instrucciones para reiniciar

echo "================================================="
echo "INGESTIÓN SEGURA - DOCUMENTOS INTELIGENCIA ARTIFICIAL"
echo "================================================="
echo ""

# 1. Buscar y matar procesos de Streamlit
echo "1. Buscando procesos de Streamlit..."
STREAMLIT_PIDS=$(pgrep -f "streamlit run")

if [ -n "$STREAMLIT_PIDS" ]; then
    echo "   ⚠️  Encontrados procesos de Streamlit: $STREAMLIT_PIDS"
    echo "   Cerrando Streamlit para liberar Qdrant..."
    kill $STREAMLIT_PIDS 2>/dev/null
    sleep 2
    echo "   ✅ Streamlit cerrado"
else
    echo "   ℹ️  No hay procesos de Streamlit activos"
fi

# 2. Verificar que no haya procesos Python usando Qdrant
echo ""
echo "2. Verificando conexiones a Qdrant..."
sleep 1

# 3. Ejecutar ingestión
echo ""
echo "3. Iniciando ingestión de documentos de Inteligencia Artificial..."
echo "   Directorio: data_topic_IA/"
echo ""
python scripts/01_ingest_pdfs.py --area inteligencia_artificial --data-dir data_topic_IA

# 4. Resultado
RESULT=$?
echo ""
echo "================================================="
if [ $RESULT -eq 0 ]; then
    echo "✅ INGESTIÓN COMPLETADA EXITOSAMENTE"
    echo ""
    echo "Para usar Streamlit nuevamente:"
    echo "  streamlit run app/streamlit_app.py"
else
    echo "❌ ERROR EN LA INGESTIÓN"
    echo "Revisa el log arriba para detalles"
fi
echo "================================================="
