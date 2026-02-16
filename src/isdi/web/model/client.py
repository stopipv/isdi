# If changes are made to this model, please run
# `flask db migrate` and then delete the drops to other tables from the upgrade() method in
# migrations/versions/<version>.py
# before running `flask db upgrade` and re-launching the server.
# if the migrations folder isn't present, run `flask db init` first.
# _order in ClientForm should be modified .

from isdi.web import sa
from wtforms.validators import Email, InputRequired


class Client(sa.Model):
    __tablename__ = "clients_notes"
    _d = {"default": "", "server_default": ""}  # makes migrations smooth
    _d0 = {"default": "0", "server_default": "0"}
    _lr = lambda label, req: {
        "label": label + "*" if req == "r" else label,
        "validators": InputRequired() if req == "r" else "",
    }
    id = sa.Column(sa.Integer, primary_key=True)
    created_at = sa.Column(
        sa.DateTime,
        # default=datetime.now()
        # TODO: timestamp off by 4 hours? investigate.
        default=sa.func.current_timestamp(),
        # server_default=sa.func.current_timestamp()
        # server_default=str(datetime.now()),
    )

    # TODO: link to session ClientID for scans, with foreignkey? across different db?
    # try using fieldstudy.db, creating table not dropping existing things. use ~test.
    clientid = sa.Column(sa.String(100), nullable=False, **_d)

    consultant_initials = sa.Column(
        sa.String(100),
        nullable=False,
        info=_lr("Consultant Names (separate with commas)", "r"),
        **_d
    )

    fjc = sa.Column(
        sa.Enum("", "Brooklyn", "Queens", "The Bronx", "Manhattan", "Staten Island"),
        nullable=False,
        info=_lr("FJC", "r"),
        **_d
    )

    preferred_language = sa.Column(
        sa.String(100),
        nullable=False,
        info=_lr("Preferred language", "r"),
        default="English",
        server_default="English",
    )

    referring_professional = sa.Column(
        sa.String(100),
        nullable=False,
        info=_lr("Name of Referring Professional", "r"),
        **_d
    )

    referring_professional_email = sa.Column(
        sa.String(255),
        nullable=True,
        info={
            "label": "Email of Referring Professional (Optional)",
            "validators": Email(),
        },
    )

    referring_professional_phone = sa.Column(
        sa.String(50),
        nullable=True,
        info={"label": "Phone number of Referring Professional (Optional)"},
    )

    caseworker_present = sa.Column(
        sa.Enum("", "For entire consult", "For part of the consult", "No"),
        nullable=False,
        info=_lr("Caseworker present", "r"),
        **_d
    )

    caseworker_present_safety_planning = sa.Column(
        sa.Enum("", "Yes", "No"),
        nullable=False,
        info=_lr("Caseworker present for safety planning", "r"),
        **_d
    )

    caseworker_recorded = sa.Column(
        sa.Enum("", "Yes", "No"),
        nullable=False,
        info=_lr("If caseworker present, permission to audio-record them", "r"),
        **_d
    )

    recorded = sa.Column(
        sa.Enum("", "Yes", "No"),
        nullable=False,
        info=_lr("Permission to audio-record clinic", "r"),
        **_d
    )

    chief_concerns = sa.Column(
        sa.String(400), nullable=False, info=_lr("Chief concerns", "r"), **_d
    )

    chief_concerns_other = sa.Column(
        sa.Text,
        nullable=False,
        info=_lr("Chief concerns if not listed above (Optional)", ""),
        **_d
    )

    android_phones = sa.Column(
        sa.Integer,
        nullable=False,
        info=_lr("# of Android phones brought in", "r"),
        **_d0
    )

    android_tablets = sa.Column(
        sa.Integer,
        nullable=False,
        info=_lr("# of Android tablets brought in", "r"),
        **_d0
    )

    iphone_devices = sa.Column(
        sa.Integer, nullable=False, info=_lr("# of iPhones brought in", "r"), **_d0
    )

    ipad_devices = sa.Column(
        sa.Integer, nullable=False, info=_lr("# of iPads brought in", "r"), **_d0
    )

    macbook_devices = sa.Column(
        sa.Integer, nullable=False, info=_lr("# of MacBooks brought in", "r"), **_d0
    )

    windows_devices = sa.Column(
        sa.Integer,
        nullable=False,
        info=_lr("# of Windows laptops brought in", "r"),
        **_d0
    )

    echo_devices = sa.Column(
        sa.Integer,
        nullable=False,
        info=_lr("# of Amazon Echoes brought in", "r"),
        **_d0
    )

    other_devices = sa.Column(
        sa.String(400),
        nullable=True,
        info=_lr("Other devices brought in if not listed above (Optional)", ""),
        **_d
    )

    # consider adding checkboxes for this
    checkups = sa.Column(
        sa.String(400),
        nullable=True,
        info=_lr("List apps/accounts manually checked (Optional)", ""),
        **_d
    )

    checkups_other = sa.Column(
        sa.String(400),
        nullable=True,
        info=_lr("Other apps/accounts manually checked (Optional)", ""),
        **_d
    )

    vulnerabilities = sa.Column(
        sa.String(600),
        nullable=False,
        info=_lr("Vulnerabilities discovered", "r"),
        **_d
    )

    vulnerabilities_trusted_devices = sa.Column(
        sa.Text,
        nullable=True,
        info=_lr(
            "List accounts with unknown trusted devices if discovered (Optional)", ""
        ),
        **_d
    )

    vulnerabilities_other = sa.Column(
        sa.Text,
        nullable=True,
        info=_lr("Other vulnerabilities discovered (Optional)", ""),
        **_d
    )

    safety_planning_onsite = sa.Column(
        sa.Enum("", "Yes", "No", "Not applicable"),
        nullable=False,
        info=_lr("Safety planning conducted onsite", "r"),
        **_d
    )

    changes_made_onsite = sa.Column(
        sa.Text, nullable=True, info=_lr("Changes made onsite (Optional)", ""), **_d
    )

    unresolved_issues = sa.Column(
        sa.Text, nullable=True, info=_lr("Unresolved issues (Optional)", ""), **_d
    )

    follow_ups_todo = sa.Column(
        sa.Text, nullable=True, info=_lr("Follow-ups To-do (Optional)", ""), **_d
    )

    general_notes = sa.Column(
        sa.Text, nullable=True, info=_lr("General notes (Optional)", ""), **_d
    )

    case_summary = sa.Column(
        sa.Text,
        nullable=True,
        info=_lr(
            'Case Summary (Can fill out after consult, see "Edit previous forms")', ""
        ),
        **_d
    )

    # way to edit data/add case summaries afterwards? Or keep text files.

    def __repr__(self):
        return "client seen on {}".format(self.created_at)
