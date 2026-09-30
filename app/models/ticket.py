from enum import Enum
from datetime import datetime
from typing import List, Union


class StatusEnum(str, Enum):
    NUEVO = "Nuevo"
    EN_PROCESO = "En Proceso"
    RESUELTO = "Resuelto"
    REABIERTO = "Reabierto"
    CERRADO = "Cerrado"


class PriorityEnum(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"


# HU08: Acciones del solicitante sobre un ticket resuelto
class SolutionActionEnum(str, Enum):
    ACEPTAR = "ACEPTAR"
    REABRIR = "REABRIR"


# HU06: Comentarios
class WorkComment:
    _id_counter = 1

    def __init__(self, ticket_id: int, author_id: int, author_name: str, text: str):
        self.id = WorkComment._id_counter
        WorkComment._id_counter += 1
        self.ticket_id = ticket_id
        self.author_id = author_id
        self.author_name = author_name
        self.text = text
        self.created_at = datetime.utcnow()


# Estructura de Historial de Estados
class StatusHistory:
    def __init__(self, old_status: str, new_status: str, user_id: int, reason: str = ""):
        self.old_status = str(old_status)
        self.new_status = str(new_status)
        self.user_id = user_id
        self.reason = reason
        self.timestamp = datetime.utcnow()


# HU05: Notificaciones internas
class Notification:
    def __init__(self, user_id: int, message: str):
        self.user_id = user_id
        self.message = message
        self.created_at = datetime.utcnow()


TICKETS_DB = {}
NOTIFICATIONS_DB = []


class Ticket:
    _id_counter = 1

    # HU07 y HU08: Matriz de transiciones permitidas
    ALLOWED_TRANSITIONS = {
        StatusEnum.NUEVO: [StatusEnum.EN_PROCESO],
        StatusEnum.EN_PROCESO: [StatusEnum.RESUELTO],
        StatusEnum.RESUELTO: [StatusEnum.REABIERTO, StatusEnum.CERRADO],
        StatusEnum.REABIERTO: [StatusEnum.EN_PROCESO, StatusEnum.RESUELTO],
        StatusEnum.CERRADO: [],
    }

    # Estados que obligatoriamente requieren un motivo de cambio
    REASON_REQUIRED = {StatusEnum.REABIERTO}

    def __init__(
        self,
        title: str,
        description: str,
        category: str,
        owner_id: int,
        priority: PriorityEnum = PriorityEnum.MEDIA,
    ):
        self.id = Ticket._id_counter
        Ticket._id_counter += 1
        self.title = title
        self.description = description
        self.category = category
        self.owner_id = owner_id
        self.status = StatusEnum.NUEVO
        self.priority = priority
        self.assigned_agent_id = None
        self.assigned_at = None
        self.assigned_by_id = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.comments = []
        self.status_history = []
        self.audit_logs = []

    def _audit(self, action: str, user_id: int, detail: str = ""):
        self.audit_logs.append({
            "action": action,
            "user_id": user_id,
            "detail": detail,
            "timestamp": datetime.utcnow(),
        })

    def _notify(self, user_id: int, message: str):
        if user_id is not None:
            NOTIFICATIONS_DB.append(Notification(user_id, message))

    def get_allowed_transitions(self) -> List[StatusEnum]:
        """Retorna las opciones válidas para cargar dinámicamente en el select HTML."""
        return self.ALLOWED_TRANSITIONS.get(self.status, [])

    # HU05: Asignación a un agente
    def assign_agent(self, agent_id: int, coordinator_id: int = None):
        self.assigned_agent_id = agent_id
        self.assigned_by_id = coordinator_id
        self.assigned_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self._audit("ASIGNACION", coordinator_id or agent_id, f"Asignado al agente {agent_id}")
        self._notify(agent_id, f"Se te asignó el ticket #{self.id}: {self.title}")

    # HU06: Registrar comentario
    def add_comment(self, author_id: int, author_name: str, text: str):
        if not text or not text.strip():
            raise ValueError("El comentario no puede estar vacío.")
        comment = WorkComment(self.id, author_id, author_name, text.strip())
        self.comments.append(comment)
        self.updated_at = datetime.utcnow()
        self._audit("COMENTARIO", author_id, f"Comentario #{comment.id}")
        return comment

    # HU07 & HU08: Transición de estado
    def change_status(self, new_status: Union[StatusEnum, str], user_id: int, reason: str = ""):
        # Conversión desde texto a Enum (Maneja envíos desde formularios HTML)
        if isinstance(new_status, str):
            try:
                new_status = StatusEnum(new_status)
            except ValueError:
                raise ValueError(f"El estado '{new_status}' no es válido.")

        reason = (reason or "").strip()
        allowed = self.get_allowed_transitions()

        if new_status not in allowed:
            raise ValueError(
                f"Transición no permitida de '{self.status.value}' a '{new_status.value}'. "
                f"Opciones válidas: {[s.value for s in allowed] or 'Ninguna (estado final)'}."
            )

        if new_status in self.REASON_REQUIRED and not reason:
            raise ValueError(f"El cambio a '{new_status.value}' requiere indicar un motivo.")

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        # Registro en el historial con la clase StatusHistory
        history_entry = StatusHistory(
            old_status=old_status.value,
            new_status=new_status.value,
            user_id=user_id,
            reason=reason,
        )
        self.status_history.append(history_entry)
        self._audit("CAMBIO_ESTADO", user_id, f"{old_status.value} -> {new_status.value}")

        # Notificaciones
        message = f"El ticket #{self.id} cambió de '{old_status.value}' a '{new_status.value}'."
        if user_id != self.owner_id:
            self._notify(self.owner_id, message)
        if user_id != self.assigned_agent_id:
            self._notify(self.assigned_agent_id, message)

    # HU08: Respuesta del solicitante a la solución
    def respond_to_solution(
        self, action: Union[SolutionActionEnum, str], user_id: int, reopen_reason: str = ""
    ):
        if self.status != StatusEnum.RESUELTO:
            raise ValueError("Solo se pueden responder tickets en estado 'Resuelto'.")

        if user_id != self.owner_id:
            raise PermissionError("Solo el solicitante del ticket puede responder a la solución.")

        if isinstance(action, str):
            action = SolutionActionEnum(action)

        if action == SolutionActionEnum.ACEPTAR:
            new_status = StatusEnum.CERRADO
            detail = "El solicitante confirmó la solución."
        else:  # REABRIR
            if not reopen_reason or not reopen_reason.strip():
                raise ValueError("Debe proporcionar un motivo para reabrir la solicitud.")
            new_status = StatusEnum.REABIERTO
            detail = f"Solicitud reabierta. Motivo: {reopen_reason.strip()}"

        self.change_status(new_status, user_id, detail)
        return new_status