from __future__ import annotations

from app.db import PUBLIC_STATUS, PUBLIC_VISIBILITY, connect, init_db


def seed() -> None:
    init_db()
    with connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM ecosystems").fetchone()[0]:
            return
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ecosystems(name, location, theme, description, status, admin_owner)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                "River City Independent Music",
                "River City Region",
                "Independent musicians, venues, studios, promoters, and community resources",
                "Pilot ecosystem for testing community asset discovery and relationship mapping.",
                "Active",
                "Prototype Admin",
            ),
        )
        ecosystem_id = cur.lastrowid
        entities = [
            ("Maya Rivera", "Artist", "Singer-songwriter blending folk, soul, and regional storytelling.", "Eastside", "https://example.org/maya", "artist,folk,soul"),
            ("The Lantern Room", "Venue", "Small listening-room venue hosting independent musicians and workshops.", "Downtown", "https://example.org/lantern", "venue,live music,workshops"),
            ("Northbank Studio", "Studio", "Recording and rehearsal space with sliding-scale community hours.", "Northbank", "https://example.org/northbank", "studio,recording,rehearsal"),
            ("Local Sound Cooperative", "Organization", "Volunteer-led group connecting artists with resources, gigs, and mutual aid.", "Regional", "https://example.org/soundcoop", "nonprofit,mutual aid,artist support"),
            ("June First Friday Showcase", "Event Organizer", "Monthly showcase highlighting emerging regional artists.", "Arts District", "https://example.org/firstfriday", "events,showcase"),
        ]
        ids = {}
        for row in entities:
            cur.execute(
                """INSERT INTO entities(ecosystem_id, name, type, description, location, website, tags, publication_status, visibility, source, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ecosystem_id, *row, PUBLIC_STATUS, PUBLIC_VISIBILITY, "Seed dataset", "Verified"),
            )
            ids[row[0]] = cur.lastrowid
        rels = [
            ("Maya Rivera", "performs at", "The Lantern Room", "Played spring acoustic showcase.", "Seed example", "Verified"),
            ("Maya Rivera", "records at", "Northbank Studio", "Recorded demo sessions at Northbank.", "Seed example", "Suggested"),
            ("Local Sound Cooperative", "provides support to", "Maya Rivera", "Shared equipment lending and gig board access.", "Seed example", "Verified"),
            ("June First Friday Showcase", "hosts artists at", "The Lantern Room", "Recurring showcase venue.", "Seed example", "Verified"),
            ("Local Sound Cooperative", "collaborates with", "Northbank Studio", "Sliding-scale studio hours for members.", "Seed example", "Suggested"),
        ]
        for source, typ, target, desc, evidence, confidence in rels:
            cur.execute(
                """INSERT INTO relationships(ecosystem_id, source_entity_id, relationship_type, target_kind, target_entity_id, description, evidence, confidence, publication_status, visibility)
                   VALUES (?, ?, ?, 'entity', ?, ?, ?, ?, ?, ?)""",
                (ecosystem_id, ids[source], typ, ids[target], desc, evidence, confidence, PUBLIC_STATUS, PUBLIC_VISIBILITY),
            )
        cur.execute(
            """INSERT INTO events(ecosystem_id, name, starts_at, location, host_entity_id, category, link, publication_status, visibility, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ecosystem_id, "First Friday Listening Room", "2026-07-03 19:00", "The Lantern Room", ids["June First Friday Showcase"], "Showcase", "https://example.org/firstfriday", PUBLIC_STATUS, PUBLIC_VISIBILITY, "Monthly showcase for emerging regional artists."),
        )
        cur.execute(
            """INSERT INTO resources(ecosystem_id, name, type, description, provider_entity_id, eligibility, location, url, tags, publication_status, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ecosystem_id, "Sliding-scale rehearsal hours", "Space", "Discounted rehearsal blocks for independent artists.", ids["Northbank Studio"], "Independent artists in the region", "Northbank", "https://example.org/rehearsal", "space,rehearsal", PUBLIC_STATUS, PUBLIC_VISIBILITY),
        )
        cur.execute(
            """INSERT INTO opportunities(ecosystem_id, name, type, deadline, sponsor_entity_id, eligibility, link, description, publication_status, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ecosystem_id, "Summer showcase artist call", "Gig", "2026-06-30", ids["June First Friday Showcase"], "Solo and duo independent acts", "https://example.org/apply", "Call for artists for summer showcase slots.", PUBLIC_STATUS, PUBLIC_VISIBILITY),
        )
        cur.execute(
            """INSERT INTO needs(ecosystem_id, need_type, description, requester_entity_id, urgency, location, status, publication_status, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ecosystem_id, "Equipment", "Portable PA needed for outdoor community sets.", ids["Maya Rivera"], "Medium", "Regional", "Open", PUBLIC_STATUS, PUBLIC_VISIBILITY),
        )
        cur.execute(
            """INSERT INTO offers(ecosystem_id, offer_type, description, provider_entity_id, availability, location, status, publication_status, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ecosystem_id, "Mentorship", "Volunteer booking mentorship for newer artists.", ids["Local Sound Cooperative"], "Monthly office hours", "Regional", "Open", PUBLIC_STATUS, PUBLIC_VISIBILITY),
        )
        cur.execute(
            """INSERT INTO submissions(ecosystem_id, submitter_name, submitter_email, submission_type, raw_data, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ecosystem_id, "Demo Submitter", "demo@example.org", "Relationship suggestion", "Maya Rivera collaborated with Northbank Studio on demo recordings. Source: public flyer.", "Pending Review"),
        )
        conn.commit()


if __name__ == "__main__":
    seed()
    print("Seeded ecosystem.db")
