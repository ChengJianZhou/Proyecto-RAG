from datetime import datetime, timedelta, timezone
import uuid

from app.core.config import settings


def utc_now() -> datetime:
    """
    Devuelve la fecha actual en UTC con timezone explícito.
    """
    return datetime.now(timezone.utc)


def generate_session_id() -> str:
    """
    Genera un identificador aleatorio para una sesión anónima.
    """
    return str(uuid.uuid4())


def get_session_expiration() -> datetime:
    """
    Calcula cuándo expira la sesión según la configuración en minutos.
    """
    return utc_now() + timedelta(minutes=settings.session_ttl_minutes)


def to_iso(dt: datetime) -> str:
    """
    Convierte un datetime a string ISO 8601.
    """
    return dt.isoformat()


def from_iso(value: str) -> datetime:
    """
    Convierte una fecha ISO 8601 a datetime.
    """
    return datetime.fromisoformat(value)