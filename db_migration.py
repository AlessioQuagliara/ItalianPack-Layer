from sqlalchemy import inspect, text


def migrate_schema(db):
    """Migra mappatura_bancale dallo schema vecchio (commessa_id diretto) al nuovo
    schema con Contenitore (contenitore_id). Va chiamata DOPO db.create_all(), così
    la tabella 'contenitore' esiste già. Idempotente: se lo schema è già aggiornato
    (o se il DB è nuovo) non fa nulla. Non elimina mai dati esistenti."""
    inspector = inspect(db.engine)

    if "mappatura_bancale" not in inspector.get_table_names():
        return

    colonne = {c["name"] for c in inspector.get_columns("mappatura_bancale")}

    if "commessa_id" not in colonne:
        return  # già completamente migrato

    with db.engine.begin() as conn:
        ha_contenitore_id = "contenitore_id" in colonne

        if not ha_contenitore_id:
            commesse_ids = [
                row[0]
                for row in conn.execute(
                    text("SELECT DISTINCT commessa_id FROM mappatura_bancale")
                ).fetchall()
            ]

            conn.execute(text("ALTER TABLE mappatura_bancale ADD COLUMN contenitore_id INTEGER"))

            for commessa_id in commesse_ids:
                result = conn.execute(
                    text(
                        "INSERT INTO contenitore (commessa_id, tipo, numero, etichetta) "
                        "VALUES (:cid, 'bancale', 1, NULL)"
                    ),
                    {"cid": commessa_id},
                )
                nuovo_contenitore_id = result.lastrowid
                conn.execute(
                    text(
                        "UPDATE mappatura_bancale SET contenitore_id = :cont_id "
                        "WHERE commessa_id = :cid"
                    ),
                    {"cont_id": nuovo_contenitore_id, "cid": commessa_id},
                )

        # La vecchia colonna commessa_id ha sia un vincolo NOT NULL sia una FOREIGN
        # KEY ereditati dalla tabella originale: SQLite non permette un semplice
        # DROP COLUMN su una colonna coinvolta in una FK, quindi ricostruiamo la
        # tabella nella forma finale (pattern standard SQLite per ALTER complessi).
        conn.execute(text("ALTER TABLE mappatura_bancale RENAME TO mappatura_bancale_old"))
        conn.execute(
            text(
                """
                CREATE TABLE mappatura_bancale (
                    id INTEGER NOT NULL PRIMARY KEY,
                    contenitore_id INTEGER NOT NULL REFERENCES contenitore (id),
                    tipo VARCHAR(20) NOT NULL,
                    x FLOAT NOT NULL,
                    y FLOAT NOT NULL,
                    gruppo VARCHAR(100),
                    aggiornato_il DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO mappatura_bancale (id, contenitore_id, tipo, x, y, gruppo, aggiornato_il)
                SELECT id, contenitore_id, tipo, x, y, gruppo, aggiornato_il FROM mappatura_bancale_old
                """
            )
        )
        conn.execute(text("DROP TABLE mappatura_bancale_old"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_mappatura_bancale_contenitore_id "
                "ON mappatura_bancale (contenitore_id)"
            )
        )


def migrate_rotazione(db):
    """Aggiunge la colonna 'ruotata' a mappatura_bancale se non esiste già.
    Semplice ADD COLUMN (nessun vincolo FK coinvolto): SQLite la gestisce
    nativamente, backfillando le righe esistenti con il DEFAULT indicato."""
    inspector = inspect(db.engine)

    if "mappatura_bancale" not in inspector.get_table_names():
        return

    colonne = {c["name"] for c in inspector.get_columns("mappatura_bancale")}
    if "ruotata" in colonne:
        return

    with db.engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE mappatura_bancale ADD COLUMN ruotata BOOLEAN NOT NULL DEFAULT 0")
        )
