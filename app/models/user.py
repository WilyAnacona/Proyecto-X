from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash

class RoleEnum(str, Enum):
    SOLICITANTE = "Solicitante"
    COORDINADOR = "Coordinador"
    AGENTE = "Agente"

class User:
    def __init__(self, id: int, username: str, password_raw: str, role: RoleEnum, is_active: bool = True):
        self.id = id
        self.username = username
        self.password_hash = generate_password_hash(password_raw)
        self.role = role
        self.is_active = is_active

    def check_password(self, password_raw: str) -> bool:
        return check_password_hash(self.password_hash, password_raw)

USERS_DB = {
    "solicitante1": User(1, "solicitante1", "pass123", RoleEnum.SOLICITANTE),
    "coordinador1": User(2, "coordinador1", "admin123", RoleEnum.COORDINADOR),
    "agente1": User(3, "agente1", "agent123", RoleEnum.AGENTE, is_active=True),
    "agente2": User(4, "agente2", "agent123", RoleEnum.AGENTE, is_active=True)  # Inactivo para pruebas
}
