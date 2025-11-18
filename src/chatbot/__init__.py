"""
Chatbot conversacional para área de Inteligencia Artificial.

Este módulo implementa un chatbot multi-turno que:
- Mantiene historial de conversación
- Reformula queries con contexto
- Ofrece modos de respuesta (corto/largo)
- Reutiliza completamente el Pipeline RAG existente

Componentes:
- ConversationHistory: Gestión de historial
- QueryReformulator: Reformulación contextual
- ResponseFormatter: Formateo según modo
- ConversationalPipeline: Orquestador principal
"""

from src.chatbot.conversation_manager import ConversationHistory
from src.chatbot.query_reformulator import QueryReformulator
from src.chatbot.response_formatter import ResponseFormatter
from src.chatbot.conversational_pipeline import ConversationalPipeline

__version__ = "1.0.0"
__all__ = [
    "ConversationHistory",
    "QueryReformulator",
    "ResponseFormatter",
    "ConversationalPipeline",
]
