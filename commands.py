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
        print(",".join("NULL" if v is None else str(v) for v in row))


def _writer(fn):
    def wrapper(conn, *args):
        try:
            cur = conn.cursor()
            ok = fn(cur, *args)
            if ok:
                conn.commit()
            else:
                conn.rollback()
            _print_bool(ok)
        except Exception:
            conn.rollback()
            _print_bool(False)
    return wrapper


@_writer
def import_data(cur, folder):
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
            cur.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
    return True


@_writer
def insert_admin(cur, uid, email, username, joined, firstname, lastname):
    cur.execute(
        "INSERT INTO User (uid, email, username, joined) VALUES (%s, %s, %s, %s)",
        (uid, email, username, joined),
    )
    cur.execute(
        "INSERT INTO Administrator (uid, firstname, lastname) VALUES (%s, %s, %s)",
        (uid, firstname, lastname),
    )
    return True


@_writer
def add_venue(cur, eid, vid, is_primary):
    is_primary_int = 1 if is_primary.lower() == "true" else 0

    cur.execute("SELECT 1 FROM Hosting WHERE eid = %s AND vid = %s", (eid, vid))
    if cur.fetchone():
        return False

    if is_primary_int == 1:
        cur.execute(
            "SELECT 1 FROM Hosting WHERE eid = %s AND is_primary = 1",
            (eid,),
        )
        if cur.fetchone():
            return False

    cur.execute(
        "INSERT INTO Hosting (eid, vid, is_primary) VALUES (%s, %s, %s)",
        (eid, vid, is_primary_int),
    )
    return True


@_writer
def reserve_slot(cur, eid, snum, uid):
    cur.execute(
        "UPDATE Slot SET is_reserved = 1, uid = %s "
        "WHERE eid = %s AND snum = %s AND is_reserved = 0",
        (uid, eid, snum),
    )
    return cur.rowcount == 1


@_writer
def cancel_reservation(cur, eid, snum, uid):
    cur.execute(
        "UPDATE Slot SET is_reserved = 0, uid = NULL "
        "WHERE eid = %s AND snum = %s AND uid = %s AND is_reserved = 1",
        (eid, snum, uid),
    )
    return cur.rowcount == 1


@_writer
def update_event(cur, eid, title, dt):
    cur.execute(
        "UPDATE Event SET title = %s, datetime = %s WHERE eid = %s",
        (title, dt, eid),
    )
    return cur.rowcount == 1


@_writer
def delete_organizer(cur, uid):
    cur.execute("DELETE FROM Organizer WHERE uid = %s", (uid,))
    return cur.rowcount == 1


def _query(conn, query, params):
    cur = conn.cursor()
    cur.execute(query, params)
    _print_table(cur.fetchall())


def available_events(conn, date):
    query = """
        SELECT e.eid, e.title, e.type, e.datetime, COUNT(*)
        FROM Event e JOIN Slot s ON e.eid = s.eid
        WHERE e.datetime > %s AND s.is_reserved = 0
        GROUP BY e.eid, e.title, e.type, e.datetime
        ORDER BY e.datetime ASC, e.eid ASC
        """
    _query(conn, query, (date,))


def popular_event_types(conn, n):
    query = """
        SELECT e.type, COUNT(*) AS reservedCount
        FROM Event e JOIN Slot s ON e.eid = s.eid
        WHERE s.is_reserved = 1
        GROUP BY e.type
        HAVING reservedCount >= %s
        ORDER BY reservedCount DESC, e.type ASC
        """
    _query(conn, query, (int(n),))


def participant_schedule(conn, uid):
    query = """
        SELECT e.eid, e.title, e.type, e.datetime, s.snum,
               v.vid, v.street, v.city, v.state, v.zip
        FROM Slot s
        JOIN Event e ON s.eid = e.eid
        LEFT JOIN Hosting h ON e.eid = h.eid AND h.is_primary = 1
        LEFT JOIN Venue v ON h.vid = v.vid
        WHERE s.uid = %s
        ORDER BY e.datetime ASC
        """
    _query(conn, query, (uid,))


def organizer_stats(conn, n):
    query = """
        SELECT o.uid, u.username, o.department, COUNT(e.eid) AS eventCount
        FROM Organizer o
        JOIN User u ON o.uid = u.uid
        LEFT JOIN Event e ON e.creator_uid = o.uid
        GROUP BY o.uid, u.username, o.department
        HAVING eventCount >= %s
        ORDER BY eventCount DESC, o.uid ASC
        """
    _query(conn, query, (int(n),))


def venue_events(conn, vid):
    query = """
        SELECT e.eid, e.title, e.type, e.datetime, h.is_primary
        FROM Hosting h
        JOIN Event e ON h.eid = e.eid
        WHERE h.vid = %s
        ORDER BY e.datetime ASC, e.eid ASC
        """
    _query(conn, query, (vid,))
