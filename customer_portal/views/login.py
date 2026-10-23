"""
Login-Seite mit Demo-Anmeldung, Passwort vergessen, Registrierung und biometrischem Login (Konzept).

Es findet keine echte Authentifizierung statt; angenommen wird nur der dokumentierte Demo-Zugang.
"""
from __future__ import annotations

import re
import time

import streamlit as st

from core.data import DEMO_LOGIN
from core.state import check_login, login, notify
from ui.components import icon, logo_html, render_html

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Baut die zentrierte Login-Karte auf.
def render() -> None:
    """Rendert die Login-Seite."""
    _, center, _ = st.columns([1, 1.25, 1])
    with center, st.container(key="login_card"):
        render_html(
            f"""
            {logo_html()}
            <h1 class="dt-login-title">Willkommen zurück</h1>
            <p class="dt-login-sub">Melden Sie sich an, um Ihren Digital Twin, Ihre Verträge und persönlichen Empfehlungen zu sehen.</p>
            <div class="dt-demo-box">{icon("info", "ms-sm")}<span><b>Demo-Zugang:</b> Kundennummer <code>{DEMO_LOGIN["customer_number"]}</code>
            oder <code>{DEMO_LOGIN["email"]}</code> · Passwort <code>{DEMO_LOGIN["password"]}</code><br>
            Bitte geben Sie keine echten Zugangsdaten ein.</span></div>
            """
        )
        with st.form("login_form", border=False):
            st.text_input("Kundennummer oder E-Mail", placeholder="z. B. DT-100010", key="login_id")
            st.text_input("Passwort", type="password", placeholder="Ihr Passwort", key="login_pw")
            st.checkbox("Angemeldet bleiben", value=True, key="login_remember")
            st.form_submit_button("Anmelden", type="primary", on_click=_submit_login)
        if st.session_state.get("login_error"):
            st.error(st.session_state.login_error)

        with st.container(key="bio_login"):
            st.button("Mit Face ID / Fingerabdruck anmelden", key="bio_btn", icon=":material/fingerprint:",
                      on_click=_biometric_login)
            render_html('<p class="dt-tiny">Biometrischer Login als Konzept für die mobile App (Demo).</p>')

        _forgot_password()
        _registration()


# Callback des Login-Formulars: prüft Eingaben und Demo-Zugang, Fehler landen im Zustand.
def _submit_login() -> None:
    """Meldet bei korrekten Demo-Daten an, sonst wird eine Fehlermeldung gesetzt."""
    identifier, password = st.session_state.login_id, st.session_state.login_pw
    if not identifier.strip() or not password:
        st.session_state.login_error = "Bitte Kundennummer bzw. E-Mail und Passwort eingeben."
    elif check_login(identifier, password):
        time.sleep(0.4)  # kurze, realistische Ladezeit der Demo-Anmeldung
        st.session_state.login_error = ""
        login()
    else:
        st.session_state.login_error = "Kundennummer/E-Mail oder Passwort ist nicht korrekt. Nutzen Sie den Demo-Zugang oben."


# Simuliert einen biometrischen Login (Konzept).
def _biometric_login() -> None:
    """Meldet den Demokunden ohne Passworteingabe an."""
    login()
    notify("Biometrische Anmeldung erfolgreich (Demo)")


# „Passwort vergessen?“ – sendet scheinbar einen Link; verrät aus Sicherheitsgründen nicht, ob das Konto existiert.
def _forgot_password() -> None:
    """Zeigt das Formular zum Zurücksetzen des Passworts."""
    with st.expander("Passwort vergessen?"):
        with st.form("forgot_form", border=False):
            email = st.text_input("E-Mail-Adresse", key="forgot_email")
            if st.form_submit_button("Link anfordern"):
                if not EMAIL_PATTERN.match(email.strip()):
                    st.error("Bitte eine gültige E-Mail-Adresse eingeben.")
                else:
                    st.success("Falls ein Konto existiert, erhalten Sie in Kürze eine E-Mail (Demo – es wird nichts versendet).")


# Registrierung mit Formularvalidierung; im Prototyp wird kein Konto angelegt.
def _registration() -> None:
    """Zeigt das Registrierungsformular für neue Kundinnen und Kunden."""
    with st.expander("Neu hier? Jetzt registrieren"):
        with st.form("register_form", border=False):
            name = st.text_input("Vor- und Nachname", key="reg_name")
            email = st.text_input("E-Mail-Adresse", key="reg_email")
            customer_number = st.text_input("Kundennummer (optional)", key="reg_number")
            pw1 = st.text_input("Passwort", type="password", key="reg_pw1", help="Mindestens 8 Zeichen, eine Ziffer")
            pw2 = st.text_input("Passwort wiederholen", type="password", key="reg_pw2")
            consent = st.checkbox(key="reg_consent", label="Ich akzeptiere die Nutzungsbedingungen und die Datenschutzhinweise (Demo).")
            if st.form_submit_button("Konto erstellen"):
                errors = []
                if len(name.split()) < 2:
                    errors.append("Bitte Vor- und Nachnamen angeben.")
                if not EMAIL_PATTERN.match(email.strip()):
                    errors.append("Bitte eine gültige E-Mail-Adresse eingeben.")
                if customer_number and not re.fullmatch(r"DT-\d{6}", customer_number.strip()):
                    errors.append("Die Kundennummer hat das Format DT-123456.")
                if len(pw1) < 8 or not any(c.isdigit() for c in pw1):
                    errors.append("Das Passwort braucht mindestens 8 Zeichen und eine Ziffer.")
                if pw1 != pw2:
                    errors.append("Die Passwörter stimmen nicht überein.")
                if not consent:
                    errors.append("Bitte stimmen Sie den Nutzungsbedingungen zu.")
                for error in errors:
                    st.error(error)
                if not errors:
                    st.success("Registrierung simuliert. Bitte melden Sie sich mit dem Demo-Zugang an.")
