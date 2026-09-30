from enum import Enum
from datetime import datetime

class StatusEnum(str, Enum):
    NUEVO = "Nuevo"
    EN_PROCESO = "En Proceso"
    RESUELTO = "Resuelto"

class PriorityEnum(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"

class PriorityAuditLog:
    def __init__(self, ticket_id: int, old_priority: str, new_priority: str, changed_by_user_id: int):
        self.ticket_id = ticket_id
        self.old_priority = old_priority
        self.new_priority = new_priority
        self.changed_by_user_id = changed_by_user_id
        self.timestamp = datetime.utcnow()

class Ticket:
    _id_counter = 1

    def __init__(self, title: str, description: str, category: str, owner_id: int):
        self.id = Ticket._id_counter
        Ticket._id_counter += 1
        self.title = title
        self.description = description
        self.category = category
        self.owner_id = owner_id
        self.status = StatusEnum.NUEVO
        self.priority = PriorityEnum.MEDIA
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.audit_logs = []

    def update_priority(self, new_priority: PriorityEnum, coordinator_id: int):
        old_p = self.priority
        self.priority = new_priority
        self.updated_at = datetime.utcnow()
        log = PriorityAuditLog(
            ticket_id=self.id,
            old_priority=old_p,
            new_priority=new_priority,
            changed_by_user_id=coordinator_id
        )
        self.audit_logs.append(log)

TICKETS_DB = {}
