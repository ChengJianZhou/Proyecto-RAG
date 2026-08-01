from pathlib import Path
import json

from app.core.config import settings
from app.documents.session import utc_now, from_iso


def cleanup_expired_documents() -> int:
    """
    Elimina JSON procesados y PDFs originales expirados.
    Devuelve cuántos documentos procesados ha eliminado.
    """
    processed_dir = Path(settings.processed_dir)

    if not processed_dir.exists() or not processed_dir.is_dir():
        return 0

    now = utc_now()
    deleted_count = 0

    for json_file in processed_dir.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            expires_at = data.get("expires_at")
            original_path = data.get("original_path")

            if not expires_at:
                continue

            if from_iso(expires_at) <= now:
                if original_path:
                    Path(original_path).unlink(missing_ok=True)

                json_file.unlink(missing_ok=True)
                deleted_count += 1

        except Exception:
            continue

    return deleted_count