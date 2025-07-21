join_views = {
    "person": {
        "base_table": "person",
        "base_alias": "p",
        "primary_key": "id",
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "p.created_at",
            "p.comment"
        ]
    },

    "building": {
        "base_table": "building",
        "base_alias": "b",
        "primary_key": "id",
        "columns": [
            "b.id AS id",
            "b.name",
            "b.building_number",
            "b.address"
        ]
    },
    "room": {
        "base_table": "room",
        "base_alias": "r",
        "primary_key": "id",
        "columns": [
            "r.id AS id",
            "r.building_id",
            "r.name",
            "r.floor"
        ]
    },

    "person_abteilung": {
        "base_table": "person",
        "base_alias": "p",
        "primary_key": "id",
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "p.created_at",
            "p.comment",
            "a.id AS abteilung_id",
            "a.name AS abteilungsname",
            "a.abteilungsleiter_id"
        ],
        "joins": [
            {"table": "person_to_abteilung", "alias": "pta", "type": "LEFT", "on": "p.id = pta.person_id"},
            {"table": "abteilung", "alias": "a", "type": "LEFT", "on": "pta.abteilung_id = a.id"}
        ],
        "writable_tables": {
            "person": "p",
            "person_to_abteilung": "pta",
            "abteilung": "a"
        }
    },

    "person_contact": {
        "base_table": "person",
        "base_alias": "p",
        "primary_key": "id",
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "pc.phone",
            "pc.fax",
            "pc.email",
            "pc.comment AS contact_comment"
        ],
        "joins": [
            {"table": "person_contact", "alias": "pc", "type": "LEFT", "on": "p.id = pc.person_id"}
        ]
    },

    "abteilung": {
        "base_table": "abteilung",
        "base_alias": "a",
        "primary_key": "id",
        "columns": [
            "a.id AS id",
            "a.name",
            "a.abteilungsleiter_id",
            "p.first_name AS abteilungsleiter_first_name",
            "p.last_name AS abteilungsleiter_last_name"
        ],
        "joins": [
            {"table": "person", "alias": "p", "type": "LEFT", "on": "a.abteilungsleiter_id = p.id"}
        ]
    },

    "kostenstelle": {
        "base_table": "kostenstelle",
        "base_alias": "k",
        "primary_key": "id",
        "columns": [
            "k.id AS id",
            "k.name"
        ]
    },

    "professorship": {
        "base_table": "professorship",
        "base_alias": "pr",
        "primary_key": "id",
        "columns": [
            "pr.id AS id",
            "pr.name",
            "pr.kostenstelle_id",
            "k.name AS kostenstelle_name"
        ],
        "joins": [
            {"table": "kostenstelle", "alias": "k", "type": "LEFT", "on": "pr.kostenstelle_id = k.id"}
        ]
    },

    "professorship_to_person": {
        "base_table": "professorship_to_person",
        "base_alias": "ptp",
        "primary_key": "id",
        "columns": [
            "ptp.id AS id",
            "ptp.professorship_id",
            "pr.name AS professorship_name",
            "ptp.person_id",
            "p.first_name",
            "p.last_name"
        ],
        "joins": [
            {"table": "professorship", "alias": "pr", "type": "LEFT", "on": "ptp.professorship_id = pr.id"},
            {"table": "person", "alias": "p", "type": "LEFT", "on": "ptp.person_id = p.id"}
        ]
    },

    "building": {
        "base_table": "building",
        "base_alias": "b",
        "primary_key": "id",
        "columns": [
            "b.id AS id",
            "b.name",
            "b.building_number",
            "b.address"
        ]
    },

    "room": {
        "base_table": "room",
        "base_alias": "r",
        "primary_key": "id",
        "columns": [
            "r.id AS id",
            "r.name",
            "r.floor",
            "r.building_id",
            "b.name AS building_name",
            "b.building_number"
        ],
        "joins": [
            {"table": "building", "alias": "b", "type": "LEFT", "on": "r.building_id = b.id"}
        ]
    },

    "person_to_room": {
        "base_table": "person_to_room",
        "base_alias": "ptr",
        "primary_key": "id",
        "columns": [
            "ptr.id AS id",
            "ptr.person_id",
            "p.first_name",
            "p.last_name",
            "r.name AS room_name",
            "r.floor"
        ],
        "joins": [
            {"table": "person", "alias": "p", "type": "LEFT", "on": "ptr.person_id = p.id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "ptr.room_id = r.id"}
        ]
    },

    "transponder": {
        "base_table": "transponder",
        "base_alias": "t",
        "primary_key": "id",
        "columns": [
            "t.id AS id",
            "t.serial_number",
            "t.got",
            "t.return",
            "t.comment",
            "t.issuer_id",
            "issuer.first_name AS issuer_first_name",
            "issuer.last_name AS issuer_last_name",
            "t.owner_id",
            "owner.first_name AS owner_first_name",
            "owner.last_name AS owner_last_name"
        ],
        "joins": [
            {"table": "person", "alias": "issuer", "type": "LEFT", "on": "t.issuer_id = issuer.id"},
            {"table": "person", "alias": "owner", "type": "LEFT", "on": "t.owner_id = owner.id"}
        ]
    },

    "transponder_to_room": {
        "base_table": "transponder_to_room",
        "base_alias": "ttr",
        "primary_key": "id",
        "columns": [
            "ttr.id AS id",
            "ttr.transponder_id",
            "t.serial_number",
            "ttr.room_id",
            "r.name AS room_name",
            "r.floor"
        ],
        "joins": [
            {"table": "transponder", "alias": "t", "type": "LEFT", "on": "ttr.transponder_id = t.id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "ttr.room_id = r.id"}
        ]
    },

    "object_category": {
        "base_table": "object_category",
        "base_alias": "oc",
        "primary_key": "id",
        "columns": [
            "oc.id AS id",
            "oc.name"
        ]
    },

    "object": {
        "base_table": "object",
        "base_alias": "o",
        "primary_key": "id",
        "columns": [
            "o.id AS id",
            "o.name",
            "o.price",
            "o.category_id",
            "oc.name AS category_name"
        ],
        "joins": [
            {"table": "object_category", "alias": "oc", "type": "LEFT", "on": "o.category_id = oc.id"}
        ]
    },

    "lager": {
        "base_table": "lager",
        "base_alias": "l",
        "primary_key": "id",
        "columns": [
            "l.id AS id",
            "l.raum_id",
            "r.name AS room_name",
            "r.floor"
        ],
        "joins": [
            {"table": "room", "alias": "r", "type": "LEFT", "on": "l.raum_id = r.id"}
        ]
    },

    "object_to_lager": {
        "base_table": "object_to_lager",
        "base_alias": "otl",
        "primary_key": "id",
        "columns": [
            "otl.id AS id",
            "otl.object_id",
            "o.name AS object_name",
            "otl.lager_id",
            "l.id AS lager_id",
            "r.name AS room_name"
        ],
        "joins": [
            {"table": "object", "alias": "o", "type": "LEFT", "on": "otl.object_id = o.id"},
            {"table": "lager", "alias": "l", "type": "LEFT", "on": "otl.lager_id = l.id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "l.raum_id = r.id"}
        ]
    },

    "inventory": {
        "base_table": "inventory",
        "base_alias": "inv",
        "primary_key": "id",
        "columns": [
            "inv.id AS id",
            "inv.owner_id",
            "owner.first_name AS owner_first_name",
            "owner.last_name AS owner_last_name",
            "inv.object_id",
            "o.name AS object_name",
            "inv.issuer_id",
            "issuer.first_name AS issuer_first_name",
            "issuer.last_name AS issuer_last_name",
            "inv.acquisition_date",
            "inv.got",
            "inv.return",
            "inv.serial_number",
            "inv.kostenstelle_id",
            "k.name AS kostenstelle_name",
            "inv.anlagennummer",
            "inv.comment",
            "inv.price",
            "inv.raum_id",
            "r.name AS room_name",
            "inv.professorship_id",
            "pr.name AS professorship_name",
            "inv.abteilung_id",
            "a.name AS abteilung_name"
        ],
        "joins": [
            {"table": "person", "alias": "owner", "type": "LEFT", "on": "inv.owner_id = owner.id"},
            {"table": "object", "alias": "o", "type": "LEFT", "on": "inv.object_id = o.id"},
            {"table": "person", "alias": "issuer", "type": "LEFT", "on": "inv.issuer_id = issuer.id"},
            {"table": "kostenstelle", "alias": "k", "type": "LEFT", "on": "inv.kostenstelle_id = k.id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "inv.raum_id = r.id"},
            {"table": "professorship", "alias": "pr", "type": "LEFT", "on": "inv.professorship_id = pr.id"},
            {"table": "abteilung", "alias": "a", "type": "LEFT", "on": "inv.abteilung_id = a.id"}
        ]
    },
}

