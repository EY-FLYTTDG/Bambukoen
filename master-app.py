import streamlit as st
from datetime import datetime
import pytz
import json
import os

try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=10000, key="daterefresh")
except ImportError:
    st.warning("Husk 'pip install streamlit-autorefresh'")

# 1. Sette opp siden og tid
st.set_page_config(page_title="Bambulab Køsystem", page_icon="🖨️", layout="centered")

norsk_tidssone = pytz.timezone("Europe/Oslo")
naa_tid = datetime.now(norsk_tidssone)
naa_tid_streng = naa_tid.strftime("%H:%M")
dagens_dato_streng = naa_tid.strftime("%Y-%m-%d")

st.title("🖨️ Bambulab MEK print kø")
st.subheader(f"🕒 Gjeldende klokkeslett: {naa_tid_streng}")

st.info("💡 **HUSK:** Legg fra deg de fysiske tokens ved printeren med en gang printen din starter!")
st.error("🔧 **Printerkrøll eller misnøye?** Hvis du ikke klarer å fikse det selv, henvend deg til **Automasjons Avd.**")

# --- PARAMETERE FOR FIL-MINNE ---
FILNAVN_KOE = "koe_data.json"
FILNAVN_FEEDBACK = "feedback_data.json"


def initialiser_blank_koe():
    """Lager en helt tom dagsplan."""
    ny_koe = []
    for i in range(1, 24 + 1):
        timer_streng = f"{i:02d}:00" if i < 24 else "24:00"
        er_nattskift = 1 <= i <= 7
        ny_koe.append({
            "id": i,
            "tid": timer_streng,
            "bruker": "Ledig",
            "status": "Ledig",
            "nattskift": er_nattskift,
            "time_verdi": i,
            "dag": "i_dag"
        })
    return ny_koe


def last_lagrede_data():
    """Henter kø-data og ruller over 'i morgen'-bookingene hvis det er ny dag."""
    if os.path.exists(FILNAVN_KOE):
        try:
            with open(FILNAVN_KOE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # HVIS DET ER EN NY DAG: Flytt morgendagens kø over til i dag!
            if data.get("dato") != dagens_dato_streng:
                gamle_tokens = data.get("tokens", [])
                oppdaterte_tokens = initialiser_blank_koe()

                for gammel_slot in gamle_tokens:
                    # Hvis en time var booket for "i morgen", blir den nå til "i dag"
                    if gammel_slot.get("dag") == "i_morgen" and gammel_slot.get("status") == "Booket":
                        matchende_ny_slot = next(s for s in oppdaterte_tokens if s["id"] == gammel_slot["id"])
                        matchende_ny_slot["bruker"] = gammel_slot["bruker"]
                        matchende_ny_slot["status"] = "Booket"
                        matchende_ny_slot["dag"] = "i_dag"  # Nå er det blitt i dag!

                # Lagre den nye oppdaterte planen med en gang
                with open(FILNAVN_KOE, "w", encoding="utf-8") as f:
                    json.dump({"dato": dagens_dato_streng, "tokens": oppdaterte_tokens,
                               "logg": ["📅 Ny dag! 'I morgen'-køen er flyttet over til i dag."]}, f, ensure_ascii=False,
                              indent=4)
                return {"dato": dagens_dato_streng, "tokens": oppdaterte_tokens,
                        "logg": ["📅 Ny dag! 'I morgen'-køen er flyttet over til i dag."]}

            return data
        except Exception:
            pass
    return None


def last_feedback_data():
    """Henter all feedback. Nullstilles ALDRI av dato-endringer."""
    if os.path.exists(FILNAVN_FEEDBACK):
        try:
            with open(FILNAVN_FEEDBACK, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ratings": [5, 5, 4], "kommentarer": []}


def lagre_koe_til_fil():
    with open(FILNAVN_KOE, "w", encoding="utf-8") as f:
        json.dump({"dato": dagens_dato_streng, "tokens": st.session_state.tokens, "logg": st.session_state.logg}, f,
                  ensure_ascii=False, indent=4)


def lagre_feedback_til_fil():
    with open(FILNAVN_FEEDBACK, "w", encoding="utf-8") as f:
        json.dump({"ratings": st.session_state.ratings, "kommentarer": st.session_state.feedback_kommentarer}, f,
                  ensure_ascii=False, indent=4)


# Last inn minner stabilt
lagret_koe = last_lagrede_data()
lagret_feedback = last_feedback_data()

# Sette opp session_state stabilt
if "tokens" not in st.session_state:
    if lagret_koe:
        st.session_state.tokens = lagret_koe["tokens"]
        st.session_state.logg = lagret_koe["logg"]
    else:
        st.session_state.tokens = initialiser_blank_koe()
        st.session_state.logg = ["Systemet startet. Alt klart for print!"]
        lagre_koe_til_fil()

if "ratings" not in st.session_state:
    st.session_state.ratings = lagret_feedback["ratings"]
    st.session_state.feedback_kommentarer = lagret_feedback["kommentarer"]

# 3. Automatisk frigjøring av gamle timer (Kun for i_dag)
naa_time = naa_tid.hour
if naa_time == 0:
    naa_time = 24

endring_skjedd = False
for slot in st.session_state.tokens:
    if slot["dag"] == "i_dag" and slot["time_verdi"] < naa_time and slot["status"] == "Booket":
        gammel_bruker = slot["bruker"]
        slot["bruker"] = "Ledig"
        slot["status"] = "Ledig"
        st.session_state.logg.insert(0,
                                     f"🤖 Automatisk frigjort: Tiden for Token #{slot['id']} ({slot['tid']}) har passert.")
        endring_skjedd = True

if endring_skjedd:
    lagre_koe_til_fil()

# 4. Brukerfunksjoner: Booke tokens
st.header("🛒 Book printertid")
medarbeider = st.text_input("Ditt navn:", placeholder="f.eks. Mathias")
antall_tokens = st.number_input("Hvor mange timer/tokens trenger du?", min_value=1, max_value=24, value=1)

col1, col2 = st.columns(2)
with col1:
    godkjent_nattskift = st.checkbox("🌙 Jeg har avtalt med nattskift")
with col2:
    book_for_i_morgen = st.checkbox("📅 Book for i morgen (fra Token 8 / 08:00)")

if st.button("Sjekk tilgjengelighet og book plass"):
    if medarbeider:
        kronologisk_soke_koe = []
        start_soke_time = 8 if book_for_i_morgen else naa_time

        for i in range(24):
            sjekk_time = ((start_soke_time - 1 + i) % 24) + 1
            token_obj = next(slot for slot in st.session_state.tokens if slot["time_verdi"] == sjekk_time)
            kronologisk_soke_koe.append((i, token_obj))

        lovlige_og_ledige = []
        antall_avvist_pga_nattskift = 0

        for soke_index, slot in kronologisk_soke_koe:
            if len(lovlige_og_ledige) == antall_tokens:
                break
            if slot["status"] == "Ledig":
                if slot["nattskift"] and not godkjent_nattskift:
                    if len(lovlige_og_ledige) > 0:
                        antall_avvist_pga_nattskift = antall_tokens - len(lovlige_og_ledige)
                    break
                lovlige_og_ledige.append((soke_index, slot))
            else:
                if len(lovlige_og_ledige) > 0:
                    break
                continue

        if len(lovlige_og_ledige) > 0:
            valgte_slots = lovlige_og_ledige[:antall_tokens]
            for soke_index, slot in valgte_slots:
                slot["bruker"] = medarbeider
                slot["status"] = "Booket"
                if book_for_i_morgen:
                    slot["dag"] = "i_morgen"
                else:
                    if start_soke_time + soke_index > 24:
                        slot["dag"] = "i_morgen"
                    else:
                        slot["dag"] = "i_dag"

            første_token = valgte_slots[0][1]
            siste_token = valgte_slots[-1][1]
            logg_melding = f"⏱️ {medarbeider} booket {len(valgte_slots)} tokens (Kl. {første_token['tid']} til {siste_token['tid']})."

            if antall_avvist_pga_nattskift > 0:
                logg_melding += f" ⚠️ {antall_avvist_pga_nattskift} timer automatisk frigjort pga nattskift-sperre."
                st.warning(
                    f"Du fikk booket {len(valgte_slots)} timer, men de siste {antall_avvist_pga_nattskift} timene ble avvist!")
            else:
                st.success(f"Suksess! Du har booket {len(valgte_slots)} sammenhengende timer.")

            st.session_state.logg.insert(0, logg_melding)
            lagre_koe_til_fil()
            st.rerun()
        else:
            st.error("Kunne ikke finne noen ledige timer etter hverandre.")
    else:
        st.warning("Du må skrive inn navnet ditt først.")

# 5. Brukerfunksjoner: Justere/Frigjøre tid manuelt
st.header("🔧 Endre pågående print")

avbestillings_valg = ["-- Velg et token --"]
for slot in st.session_state.tokens:
    if slot["status"] == "Booket":
        dag_label = "I morgen" if slot["dag"] == "i_morgen" else "I dag"
        avbestillings_valg.append(f"Token #{slot['id']} ({slot['tid']} - {dag_label}) - {slot['bruker']}")

valgt_streng = st.selectbox("Hvilket Token vil du avbryte/skyve?", options=avbestillings_valg)
kommentar = st.text_input("Obligatorisk årsak/kommentar til endringen:")

if st.button("Frigjør token manuelt"):
    if valgt_streng != "-- Velg et token --" and kommentar:
        token_id_valgt = int(valgt_streng.split("#")[1].split(" ")[0])

        target_token = st.session_state.tokens[token_id_valgt - 1]
        gammel_bruker = target_token["bruker"]

        target_token["bruker"] = "Ledig"
        target_token["status"] = "Ledig"
        target_token["dag"] = "i_dag"
        st.session_state.logg.insert(0, f"⚠️ Token #{token_id_valgt} frigjort av {gammel_bruker}. Årsak: {kommentar}")
        st.success(f"Token #{token_id_valgt} er frigjort!")
        lagre_koe_til_fil()
        st.rerun()
    else:
        st.warning("Du må både velge et token og skrive en kommentar!")

# 6. Visning av rutetabellen / Timelisten
st.header("📅 Dagens Timetabell (24 Timer)")

for slot in st.session_state.tokens:
    if slot["bruker"] != "Ledig":
        status_ikon = "🔴"
        dag_info = " [I MORGEN]" if slot["dag"] == "i_morgen" else ""
        tilleggs_tekst = f"-> Booket av {slot['bruker']}{dag_info}"
    elif slot["nattskift"]:
        status_ikon = "🌙"
        tilleggs_tekst = "(Ledig - KUN FOR NATTSKIFT)"
    else:
        status_ikon = "🟢"
        tilleggs_tekst = "(Ledig)"

    st.text(f"{status_ikon} Token #{slot['id']:02d} | Kl. {slot['tid']} {tilleggs_tekst}")

# 7. Hendelseslogg
st.header("📋 Siste hendelser")
for hendelse in st.session_state.logg[:3]:
    st.caption(hendelse)

st.write("---")

# 8. Feedback-seksjon
st.header("⭐ Tilbakemeldinger på systemet")
gjennomsnitt = sum(st.session_state.ratings) / len(st.session_state.ratings)
st.subheader(f"Gjennomsnittlig rating: {gjennomsnitt:.1f} / 5.0 stjerner ({len(st.session_state.ratings)} stemmer)")

stjerner = st.slider("Hvor mange stjerner gir du dette køsystemet?", min_value=1, max_value=5, value=5)
tilbakemelding_tekst = st.text_area("Kommentar (valgfri):", placeholder="Hva kan forbedres?")

if st.button("Send tilbakemelding"):
    st.session_state.ratings.append(stjerner)
    if tilbakemelding_tekst.strip():
        tidspunkt_streng = naa_tid.strftime("%d.%m %H:%M")
        st.session_state.feedback_kommentarer.insert(0, f"[{tidspunkt_streng}] ⭐{stjerner}: {tilbakemelding_tekst}")

    lagre_feedback_til_fil()
    st.success("Tusen takk for tilbakemeldingen din!")
    st.rerun()

with st.expander("💬 Vis/gjem tekstkommentarer fra kolleger"):
    if st.session_state.feedback_kommentarer:
        for kommentar_linje in st.session_state.feedback_kommentarer:
            st.write(kommentar_linje)
    else:
        st.write("*Ingen tekstkommentarer har kommet inn ennå. Bli den første!*")

st.write("---")

# 9. Signatur
st.markdown("<center><h4>Vibet av EY-FLYTTDG 🤘</h4></center>", unsafe_allow_html=True)