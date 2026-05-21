import csv
import os

DDL = [
    "DROP TABLE IF EXISTS Approval",
    "DROP TABLE IF EXISTS Hosting",
    "DROP TABLE IF EXISTS OffCampus",
    "DROP TABLE IF EXISTS OnCampus",
    "DROP TABLE IF EXISTS Venue",
    "DROP TABLE IF EXISTS Slot",
    "DROP TABLE IF EXISTS Event",
    "DROP TABLE IF EXISTS Administrator",
    "DROP TABLE IF EXISTS Participant",
    "DROP TABLE IF EXISTS Organizer",
    "DROP TABLE IF EXISTS User",
    """CREATE TABLE User (
        uid INT,
        email TEXT NOT NULL,
        username TEXT NOT NULL,
        joined DATE NOT NULL,
        PRIMARY KEY (uid)
    )""",
    """CREATE TABLE Organizer (
        uid INT,
        department TEXT NOT NULL,
        experience INT NOT NULL,
        PRIMARY KEY (uid),
        FOREIGN KEY (uid) REFERENCES User(uid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Participant (
        uid INT,
        type TEXT,
        PRIMARY KEY (uid),
        FOREIGN KEY (uid) REFERENCES User(uid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Administrator (
        uid INT,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        PRIMARY KEY (uid),
        FOREIGN KEY (uid) REFERENCES User(uid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Event (
        eid INT,
        creator_uid INT NOT NULL,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        datetime DATETIME NOT NULL,
        PRIMARY KEY (eid),
        FOREIGN KEY (creator_uid) REFERENCES Organizer(uid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Slot (
        eid INT,
        snum INT NOT NULL,
        is_reserved BOOLEAN NOT NULL,
        uid INT,
        PRIMARY KEY (eid, snum),
        FOREIGN KEY (eid) REFERENCES Event(eid) ON DELETE CASCADE,
        FOREIGN KEY (uid) REFERENCES Participant(uid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Venue (
        vid INT,
        street TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        zip TEXT NOT NULL,
        PRIMARY KEY (vid)
    )""",
    """CREATE TABLE OnCampus (
        vid INT,
        code TEXT NOT NULL,
        PRIMARY KEY (vid),
        FOREIGN KEY (vid) REFERENCES Venue(vid) ON DELETE CASCADE
    )""",
    """CREATE TABLE OffCampus (
        vid INT,
        distance INT NOT NULL,
        PRIMARY KEY (vid),
        FOREIGN KEY (vid) REFERENCES Venue(vid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Hosting (
        eid INT NOT NULL,
        vid INT NOT NULL,
        is_primary BOOLEAN NOT NULL,
        PRIMARY KEY (eid, vid),
        FOREIGN KEY (eid) REFERENCES Event(eid) ON DELETE CASCADE,
        FOREIGN KEY (vid) REFERENCES Venue(vid) ON DELETE CASCADE
    )""",
    """CREATE TABLE Approval (
        uid INT NOT NULL,
        vid INT NOT NULL,
        valid_from DATE NOT NULL,
        valid_until DATE NOT NULL,
        PRIMARY KEY (uid, vid),
        FOREIGN KEY (uid) REFERENCES Administrator(uid) ON DELETE CASCADE,
        FOREIGN KEY (vid) REFERENCES OffCampus(vid) ON DELETE CASCADE
    )""",
]

LOAD_ORDER = [
    ("User", "User.csv", 4),
    ("Organizer", "Organizer.csv", 3),
    ("Participant", "Participant.csv", 2),
    ("Administrator", "Administrator.csv", 3),
    ("Event", "Event.csv", 5),
    ("Slot", "Slot.csv", 4),
    ("Venue", "Venue.csv", 5),
    ("OnCampus", "OnCampus.csv", 2),
    ("OffCampus", "OffCampus.csv", 2),
    ("Hosting", "Hosting.csv", 3),
    ("Approval", "Approval.csv", 4),
]


def _print_bool(success):
    print("Success" if success else "Fail")


def _print_table(rows):
    for row in rows:
        print(",".join("None" if v is None else str(v) for v in row))


def import_data(conn, folder):
    try:
        cur = conn.cursor()
        for stmt in DDL:
            cur.execute(stmt)

        for table, filename, num_cols in LOAD_ORDER:
            path = os.path.join(folder, filename)
            rows = []
            with open(path) as f:
                for row in csv.reader(f):
                    rows.append([None if v == "NULL" else v for v in row])
            if rows:
                placeholders = ",".join(["%s"] * num_cols)
                cur.executemany(
                    f"INSERT INTO {table} VALUES ({placeholders})", rows
                )

        conn.commit()
        _print_bool(True)
    except Exception:
        conn.rollback()
        _print_bool(False)


def insert_admin(conn, uid, email, username, joined, firstname, lastname):
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO User (uid, email, username, joined) VALUES (%s, %s, %s, %s)",
            (uid, email, username, joined),
        )
        cur.execute(
            "INSERT INTO Administrator (uid, firstname, lastname) VALUES (%s, %s, %s)",
            (uid, firstname, lastname),
        )
        conn.commit()
        _print_bool(True)
    except Exception:
        conn.rollback()
        _print_bool(False)


def add_venue(conn, eid, vid, is_primary):
    try:
        cur = conn.cursor()
        is_primary_int = 1 if is_primary.lower() == "true" else 0

        cur.execute(
            "SELECT 1 FROM Hosting WHERE eid = %s AND vid = %s", (eid, vid)
        )
        if cur.fetchone():
            _print_bool(False)
            return

        if is_primary_int == 1:
            cur.execute(
                "SELECT 1 FROM Hosting WHERE eid = %s AND is_primary = 1",
                (eid,),
            )
            if cur.fetchone():
                _print_bool(False)
                return

        cur.execute(
            "INSERT INTO Hosting (eid, vid, is_primary) VALUES (%s, %s, %s)",
            (eid, vid, is_primary_int),
        )
        conn.commit()
        _print_bool(True)
    except Exception:
        conn.rollback()
        _print_bool(False)


def reserve_slot(conn, eid, snum, uid):
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE Slot SET is_reserved = 1, uid = %s "
            "WHERE eid = %s AND snum = %s AND is_reserved = 0",
            (uid, eid, snum),
        )
        success = cur.rowcount == 1
        if success:
            conn.commit()
        else:
            conn.rollback()
        _print_bool(success)
    except Exception:
        conn.rollback()
        _print_bool(False)


def cancel_reservation(conn, eid, snum, uid):
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE Slot SET is_reserved = 0, uid = NULL "
            "WHERE eid = %s AND snum = %s AND uid = %s AND is_reserved = 1",
            (eid, snum, uid),
        )
        success = cur.rowcount == 1
        if success:
            conn.commit()
        else:
            conn.rollback()
        _print_bool(success)
    except Exception:
        conn.rollback()
        _print_bool(False)


def update_event(conn, eid, title, dt):
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE Event SET title = %s, datetime = %s WHERE eid = %s",
            (title, dt, eid),
        )
        success = cur.rowcount == 1
        if success:
            conn.commit()
        else:
            conn.rollback()
        _print_bool(success)
    except Exception:
        conn.rollback()
        _print_bool(False)


def delete_organizer(conn, uid):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM Organizer WHERE uid = %s", (uid,))
        success = cur.rowcount == 1
        if success:
            conn.commit()
        else:
            conn.rollback()
        _print_bool(success)
    except Exception:
        conn.rollback()
        _print_bool(False)


def available_events(conn, date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.eid, e.title, e.type, e.datetime, COUNT(*)
        FROM Event e JOIN Slot s ON e.eid = s.eid
        WHERE e.datetime > %s AND s.is_reserved = 0
        GROUP BY e.eid, e.title, e.type, e.datetime
        ORDER BY e.datetime ASC, e.eid ASC
        """,
        (date,),
    )
    _print_table(cur.fetchall())


def popular_event_types(conn, n):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.type, COUNT(*) AS reservedCount
        FROM Event e JOIN Slot s ON e.eid = s.eid
        WHERE s.is_reserved = 1
        GROUP BY e.type
        HAVING reservedCount >= %s
        ORDER BY reservedCount DESC, e.type ASC
        """,
        (int(n),),
    )
    _print_table(cur.fetchall())


def participant_schedule(conn, uid):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.eid, e.title, e.type, e.datetime, s.snum,
               v.vid, v.street, v.city, v.state, v.zip
        FROM Slot s
        JOIN Event e ON s.eid = e.eid
        LEFT JOIN Hosting h ON e.eid = h.eid AND h.is_primary = 1
        LEFT JOIN Venue v ON h.vid = v.vid
        WHERE s.uid = %s
        ORDER BY e.datetime ASC
        """,
        (uid,),
    )
    _print_table(cur.fetchall())


def organizer_stats(conn, n):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.uid, u.username, o.department, COUNT(e.eid) AS eventCount
        FROM Organizer o
        JOIN User u ON o.uid = u.uid
        JOIN Event e ON e.creator_uid = o.uid
        GROUP BY o.uid, u.username, o.department
        HAVING eventCount >= %s
        ORDER BY eventCount DESC, o.uid ASC
        """,
        (int(n),),
    )
    _print_table(cur.fetchall())


def venue_events(conn, vid):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.eid, e.title, e.type, e.datetime, h.is_primary
        FROM Hosting h
        JOIN Event e ON h.eid = e.eid
        WHERE h.vid = %s
        ORDER BY e.datetime ASC, e.eid ASC
        """,
        (vid,),
    )
    _print_table(cur.fetchall())
