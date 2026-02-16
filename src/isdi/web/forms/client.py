from wtforms_alchemy import ModelForm
from isdi.web.model import Client
from wtforms.fields import SelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget
from wtforms import TextAreaField


class ClientForm(ModelForm):
    class Meta:
        model = Client

    chief_concerns = SelectMultipleField(
        "Chief concerns*",
        choices=[
            ("spyware", "Worried about spyware/tracking"),
            ("hacked", "Abuser hacked accounts or knows secrets"),
            ("location", "Worried abuser was tracking their location"),
            ("glitchy", "Phone is glitchy"),
            ("unknown_calls", "Abuser calls/texts from unknown numbers"),
            ("social_media", "Social media concerns (e.g., fake accounts, harassment)"),
            ("child_devices", "Concerns about child device(s), e.g., unknown apps"),
            (
                "financial_concerns",
                "Financial concerns, e.g., fraud, money missing from bank account",
            ),
            ("curious", "Curious and want to learn about privacy"),
            ("sms", "SMS texts"),
            ("other", "Other chief concern (write in next question)"),
        ],
        coerce=str,
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )

    checkups = SelectMultipleField(
        "List apps/accounts manually checked (Optional)",
        choices=[
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("snapchat", "SnapChat"),
            ("google", "Google (including GMail)"),
            ("icloud", "iCloud"),
            ("whatsapp", "WhatsApp"),
            ("other", "Other apps/accounts (write in next question)"),
        ],
        coerce=str,
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )

    vulnerabilities = SelectMultipleField(
        "Vulnerabilities discovered*",
        choices=[
            ("none", "None"),
            ("shared plan", "Shared plan / abuser pays for plan"),
            (
                "password:observed compromise",
                "Observed compromise (e.g., client reports abuser shoulder-surfed, or told them password)",
            ),
            ("password:guessable", "Surfaced guessable passwords"),
            (
                "cloud:stored passwords",
                "Stored passwords in app that is synced to cloud (e.g., passwords written in Notes and backed up)",
            ),
            (
                "cloud:passwords synced/password manager",
                "Password syncing (e.g., iCloud Keychain)",
            ),
            (
                "unknown trusted device",
                "Found an account with an active login from a device not under client's control; trusted device",
            ),
            ("ISDi:found dual-use apps/spyware", "ISDi found dual-use apps/spyware"),
            ("ISDi:false positive", "ISDi false positive as confirmed by client"),
            ("browser extension", "Browser extension potential spyware"),
            ("desktop potential spyware", "Desktop application potential spyware"),
        ],
        coerce=str,
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )

    __order = (
        "fjc",
        "consultant_initials",
        "preferred_language",
        "referring_professional",
        "referring_professional_email",
        "referring_professional_phone",
        "caseworker_present",
        "caseworker_present_safety_planning",
        "recorded",
        "caseworker_recorded",
        "chief_concerns",
        "chief_concerns_other",
        "android_phones",
        "android_tablets",
        "iphone_devices",
        "ipad_devices",
        "macbook_devices",
        "windows_devices",
        "echo_devices",
        "other_devices",
        "checkups",
        "checkups_other",
        "vulnerabilities",
        "vulnerabilities_trusted_devices",
        "vulnerabilities_other",
        "safety_planning_onsite",
        "changes_made_onsite",
        "unresolved_issues",
        "follow_ups_todo",
        "general_notes",
        "case_summary",
    )

    chief_concerns_other = TextAreaField(
        "Chief concerns if not listed above (Optional)",
        render_kw={"rows": 5, "cols": 70},
    )
    vulnerabilities_trusted_devices = TextAreaField(
        "List accounts with unknown trusted devices if discovered (Optional)",
        render_kw={"rows": 5, "cols": 70},
    )
    vulnerabilities_other = TextAreaField(
        "Other vulnerabilities discovered (Optional)", render_kw={"rows": 5, "cols": 70}
    )
    changes_made_onsite = TextAreaField(
        "Changes made onsite (Optional)", render_kw={"rows": 5, "cols": 70}
    )
    unresolved_issues = TextAreaField(
        "Unresolved issues (Optional)", render_kw={"rows": 5, "cols": 70}
    )
    follow_ups_todo = TextAreaField(
        "Follow-ups To-do (Optional)", render_kw={"rows": 5, "cols": 70}
    )
    general_notes = TextAreaField(
        "General notes (Optional)", render_kw={"rows": 10, "cols": 70}
    )
    case_summary = TextAreaField(
        'Case Summary (Can fill out after consult, see "Edit previous forms")',
        render_kw={"rows": 10, "cols": 70},
    )

    def __iter__(self):  # https://stackoverflow.com/a/25323199
        fields = list(super(ClientForm, self).__iter__())
        get_field = lambda field_id: next((fld for fld in fields if fld.id == field_id))
        return (get_field(field_id) for field_id in self.__order)
