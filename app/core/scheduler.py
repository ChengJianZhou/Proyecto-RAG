from apscheduler.schedulers.background import BackgroundScheduler

from app.documents.cleanup import cleanup_expired_documents

scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    """
    Arranca el scheduler y registra la tarea periódica de limpieza.
    """
    if not scheduler.running:
        scheduler.add_job(
            cleanup_expired_documents,
            trigger="interval",
            minutes=1,
            id="cleanup_expired_documents",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler() -> None:
    """
    Detiene el scheduler al apagar la aplicación.
    """
    if scheduler.running:
        scheduler.shutdown()