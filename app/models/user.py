from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash

class RoleEnum(str, Enum):
    SOLICITANTE = "Solicitante"
    COORDINADOR = "Coordinador"

class User:
    def __init__(self, id: int, username: str, password_raw: str, role: RoleEnum):
        self.id = id
        self.username = username
        self.password_hash = generate_password_hash(password_raw)
        self.role = role

    def check_password(self, password_raw: str) -> bool:
        return check_password_hash(self.password_hash, password_raw)

USERS_DB = {
    "solicitante1": User(1, "solicitante1", "pass123", RoleEnum.SOLICITANTE),
    "coordinador1": User(2, "coordinador1", "admin123", RoleEnum.COORDINADOR)
}
