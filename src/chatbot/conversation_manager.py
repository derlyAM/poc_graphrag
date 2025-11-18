"""
Conversation Manager - Gestión de historial conversacional.

Componente stateful que mantiene el historial de mensajes usuario-bot.
"""
from typing import List, Dict, Optional
from loguru import logger


class ConversationHistory:
    """
    Gestiona el historial de conversación multi-turno.

    Mantiene lista de mensajes con roles (user/assistant) y permite
    recuperar contexto para reformulación de queries.

    Esta funcionalidad NO existe en el Pipeline RAG (que es stateless).
    """

    def __init__(self, max_history: int = 20):
        """
        Inicializa gestor de historial.

        Args:
            max_history: Máximo número de mensajes a mantener
        """
        self.messages: List[Dict[str, str]] = []
        self.max_history = max_history

        logger.debug(f"ConversationHistory initialized (max={max_history})")

    def add_message(self, role: str, content: str) -> None:
        """
        Agrega mensaje al historial.

        Args:
            role: "user" o "assistant"
            content: Contenido del mensaje

        Raises:
            ValueError: Si role no es válido
        """
        if role not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        message = {"role": role, "content": content}
        self.messages.append(message)

        # Limitar tamaño del historial
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
            logger.debug(f"Historial truncado a {self.max_history} mensajes")

        logger.debug(f"Mensaje agregado: {role} ({len(content)} chars)")

    def get_last_n_messages(self, n: int = 5) -> List[Dict[str, str]]:
        """
        Obtiene los últimos N mensajes.

        Args:
            n: Número de mensajes a recuperar

        Returns:
            Lista de mensajes (más recientes primero)
        """
        if n <= 0:
            return []

        if len(self.messages) <= n:
            return self.messages.copy()

        return self.messages[-n:]

    def get_all_messages(self) -> List[Dict[str, str]]:
        """
        Obtiene todos los mensajes del historial.

        Returns:
            Lista completa de mensajes
        """
        return self.messages.copy()

    def clear(self) -> None:
        """Limpia todo el historial."""
        message_count = len(self.messages)
        self.messages = []
        logger.info(f"Historial limpiado ({message_count} mensajes eliminados)")

    def get_conversation_summary(self, max_chars: int = 200) -> str:
        """
        Genera resumen breve de la conversación.

        Útil para logging o debugging.

        Args:
            max_chars: Máximo caracteres por mensaje

        Returns:
            String con resumen de la conversación
        """
        if not self.messages:
            return "[Conversación vacía]"

        summary_lines = []
        for msg in self.messages[-5:]:  # Últimos 5
            role_icon = "👤" if msg["role"] == "user" else "🤖"
            content_preview = msg["content"][:max_chars]
            if len(msg["content"]) > max_chars:
                content_preview += "..."
            summary_lines.append(f"{role_icon} {content_preview}")

        return "\n".join(summary_lines)

    def __len__(self) -> int:
        """Retorna número de mensajes en historial."""
        return len(self.messages)

    def __repr__(self) -> str:
        """Representación string del historial."""
        return f"<ConversationHistory: {len(self.messages)} messages>"
