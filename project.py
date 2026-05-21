import sys
import mysql.connector

import commands

DISPATCH = {
    "import": commands.import_data,
    "insertAdmin": commands.insert_admin,
    "addVenue": commands.add_venue,
    "reserveSlot": commands.reserve_slot,
    "cancelReservation": commands.cancel_reservation,
    "updateEvent": commands.update_event,
    "deleteOrganizer": commands.delete_organizer,
    "availableEvents": commands.available_events,
    "popularEventTypes": commands.popular_event_types,
    "participantSchedule": commands.participant_schedule,
    "organizerStats": commands.organizer_stats,
    "venueEvents": commands.venue_events,
}


def main():
    func = DISPATCH[sys.argv[1]]
    conn = mysql.connector.connect(
        user="test", password="password", database="cs122a"
    )
    try:
        func(conn, *sys.argv[2:])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
