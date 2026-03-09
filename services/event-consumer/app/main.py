import time
from services.api.app.db.session import SessionLocal
from services.api.app.services.pipeline import consume_published_events, relay_outbox_batch


def run_forever() -> None:  # pragma: no cover
    while True:
        with SessionLocal() as session:
            relay_outbox_batch(session)
            consume_published_events(session)
            session.commit()
        time.sleep(5)


if __name__ == "__main__":  # pragma: no cover
    run_forever()
