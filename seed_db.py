from app import app
from models import db, Swimmer, KlockanSession, KlockanResult

with app.app_context():
    db.drop_all()
    db.create_all()

    elias = Swimmer(name="Elias", is_active=True)
    anna = Swimmer(name="Anna", is_active=True)
    lina = Swimmer(name="Lina", is_active=False)

    db.session.add_all([elias, anna, lina])
    db.session.commit()

    session1 = KlockanSession(
        date="2026-03-15",
        pool_length="25 m",
        max_rounds=3
    )
    db.session.add(session1)
    db.session.commit()

    results = [
        KlockanResult(
            session_id=session1.id,
            round_number=1,
            swimmer_id=elias.id,
            stroke="Freestyle",
            equipment="Fenor",
            failed_start_time=50
        ),
        KlockanResult(
            session_id=session1.id,
            round_number=1,
            swimmer_id=anna.id,
            stroke="Butterfly",
            equipment="Ingen",
            failed_start_time=55
        ),
        KlockanResult(
            session_id=session1.id,
            round_number=1,
            swimmer_id=lina.id,
            stroke="Backstroke",
            equipment="Platta",
            failed_start_time=58
        ),
        KlockanResult(
            session_id=session1.id,
            round_number=2,
            swimmer_id=elias.id,
            stroke="Butterfly",
            equipment="Paddlar",
            failed_start_time=45
        ),
        KlockanResult(
            session_id=session1.id,
            round_number=2,
            swimmer_id=anna.id,
            stroke="Freestyle",
            equipment="Dolme",
            failed_start_time=52
        ),
        KlockanResult(
            session_id=session1.id,
            round_number=3,
            swimmer_id=elias.id,
            stroke="Medley",
            equipment="Ingen",
            failed_start_time=40
        )
    ]

    db.session.add_all(results)
    db.session.commit()

    print("Database seeded successfully.")