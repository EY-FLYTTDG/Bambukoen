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

st.title("🖨️ Bambulab MEK Print kø")
st.subheader(f"🕒 Gjeldende klokkeslett: {naa_tid_streng}")

st.info(
    "💡 **HUSK:** ta med deg fysiske tokens når du booker print tid og Legg fra deg de ved printeren med en gang printen din starter!")
st.info("print tid for morgendagen blir frigitt 24Timer i forkant")
st.error("🔧 **Printerkrøll eller misnøye?** Hvis du ikke klarer å fikse det selv, henvend deg til **Automasjons Avd.**")

# --- PARAMETERE FOR FIL-MINNE ---
FILNAVN_KOE = "koe_data.json"
FILNAVN_FEEDBACK = "feedback_data.json"
FILNAVN_SCOREBOARD = "scoreboard_data.json"

if "vis_secret_board" not in st.session_state:
    st.session_state.vis_secret_board = False


def initialiser_blank_koe():
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
    if os.path.exists(FILNAVN_KOE):
        try:
            with open(FILNAVN_KOE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("dato") != dagens_dato_streng:
                gamle_tokens = data.get("tokens", [])
                oppdaterte_tokens = initialiser_blank_koe()

                for gammel_slot in gamle_tokens:
                    if gammel_slot.get("dag") == "i_morgen" and gammel_slot.get("status") == "Booket":
                        matchende_ny_slot = next(s for s in oppdaterte_tokens if s["id"] == gammel_slot["id"])
                        matchende_ny_slot["bruker"] = gammel_slot["bruker"]
                        matchende_ny_slot["status"] = "Booket"
                        matchende_ny_slot["dag"] = "i_dag"

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
    if os.path.exists(FILNAVN_FEEDBACK):
        try:
            with open(FILNAVN_FEEDBACK, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ratings": [5, 5, 4], "kommentarer": []}


def last_scoreboard_data():
    if os.path.exists(FILNAVN_SCOREBOARD):
        try:
            with open(FILNAVN_SCOREBOARD, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def lagre_koe_til_fil():
    with open(FILNAVN_KOE, "w", encoding="utf-8") as f:
        json.dump({"dato": dagens_dato_streng, "tokens": st.session_state.tokens, "logg": st.session_state.logg}, f,
                  ensure_ascii=False, indent=4)


def lagre_feedback_til_fil():
    with open(FILNAVN_FEEDBACK, "w", encoding="utf-8") as f:
        json.dump({"ratings": st.session_state.ratings, "kommentarer": st.session_state.feedback_kommentarer}, f,
                  ensure_ascii=False, indent=4)


def oppdater_og_lagre_scoreboard(navn, score):
    gjeldende_scoreboard = last_scoreboard_data()
    vasket_navn = navn.strip().capitalize()

    if vasket_navn in gjeldende_scoreboard:
        gjeldende_scoreboard[vasket_navn] += score
    else:
        gjeldende_scoreboard[vasket_navn] = score

    with open(FILNAVN_SCOREBOARD, "w", encoding="utf-8") as f:
        json.dump(gjeldende_scoreboard, f, ensure_ascii=False, indent=4)
    st.session_state.scoreboard = gjeldende_scoreboard


# Last inn minner
lagret_koe = last_lagrede_data()
lagret_feedback = last_feedback_data()

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

if "scoreboard" not in st.session_state:
    st.session_state.scoreboard = last_scoreboard_data()

# 3. Automatisk frigjøring av gamle timer
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

        # Poeng registreres KUN her når timen passerer automatisk
        oppdater_og_lagre_scoreboard(gammel_bruker, 1)
        endring_skjedd = True

if endring_skjedd:
    lagre_koe_til_fil()

# 4. Brukerfunksjoner: Booke tokens (NÅ PAKKET INN I ET TRYGT FORM)
st.header("🛒 Book printertid")

# clear_on_submit tømmer skjemaet AUTOMATISK i skyen/lokalt uten å krasje session_state!
with st.form(key="booking_form", clear_on_submit=True):
    medarbeider = st.text_input("Ditt navn:", placeholder="f.eks. Thomas")
    antall_tokens = st.number_input("Hvor mange timer/tokens trenger du?", min_value=1, max_value=24, value=1)

    col1, col2 = st.columns(2)
    with col1:
        godkjent_nattskift = st.checkbox("🌙 Jeg har avtalt med nattskift")
    with col2:
        book_for_i_morgen = st.checkbox("📅 Book for i morgen (fra Token 8 / 08:00)")

    submit_booking = st.form_submit_button("book print tid")

if submit_booking:
    if medarbeider:
        # --- SJEKK ETTER HEMMELIG PASSORD ---
        if medarbeider.strip() == "AUT-ADMIN":
            st.session_state.vis_secret_board = not st.session_state.vis_secret_board
            st.rerun()

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

            naa_endring_tid = datetime.now(norsk_tidssone).strftime("%H:%M")
            logg_melding = f"[{naa_endring_tid}] ⏱️ {medarbeider} booket {len(valgte_slots)} tokens (Kl. {første_token['tid']} til {siste_token['tid']})."

            if antall_avvist_pga_nattskift > 0:
                logg_melding += f" ⚠️ {antall_avvist_pga_nattskift} timer automatisk frigjort pga nattskift-sperre."
                st.session_state[
                    "toast_melding"] = f"⚠️ Kun delvis booket! Du fikk {len(valgte_slots)} timer, men de siste {antall_avvist_pga_nattskift} ble avvist pga nattskift!"
            else:
                st.session_state[
                    "toast_melding"] = f"✅ Suksess! Du har booket {len(valgte_slots)} timer fra kl. {første_token['tid']}."

            st.session_state.logg.insert(0, logg_melding)
            lagre_koe_til_fil()
            st.rerun()
        else:
            st.error("Kunne ikke finne noen ledige timer etter hverandre.")
    else:
        st.warning("Du må skrive inn navnet ditt først.")

if "toast_melding" in st.session_state:
    st.toast(st.session_state["toast_melding"])
    del st.session_state["toast_melding"]

# 5. Brukerfunksjoner: Justere/Frigjøre tid manuelt (OGSÅ PAKKET INN I ET FORM)
st.header("🔧 Endre pågående print")

avbestillings_valg = ["-- Velg et token --"]
for slot in st.session_state.tokens:
    if slot["status"] == "Booket":
        dag_label = "I morgen" if slot["dag"] == "i_morgen" else "I dag"
        avbestillings_valg.append(f"Token #{slot['id']} ({slot['tid']} - {dag_label}) - {slot['bruker']}")

with st.form(key="rydde_form", clear_on_submit=True):
    valgt_streng = st.selectbox("Hvilket Token vil du avbryte/skyve?", options=avbestillings_valg)
    hvem_rydder = st.text_input("Hvem frigjør dette tokenet?", placeholder="Ditt navn (f.eks. Morten)")
    kommentar = st.text_input("Obligatorisk årsak/kommentar til endringen:")
    submit_rydding = st.form_submit_button("Frigjør token manuelt")

if submit_rydding:
    if valgt_streng != "-- Velg et token --" and kommentar and hvem_rydder:
        token_id_valgt = int(valgt_streng.split("#")[1].split(" ")[0])

        target_token = st.session_state.tokens[token_id_valgt - 1]
        gammel_bruker = target_token["bruker"]

        target_token["bruker"] = "Ledig"
        target_token["status"] = "Ledig"
        target_token["dag"] = "i_dag"

        naa_endring_tid = datetime.now(norsk_tidssone).strftime("%H:%M")
        st.session_state.logg.insert(0,
                                     f"[{naa_endring_tid}] ⚠️ Token #{token_id_valgt} til {gammel_bruker} frigjort av {hvem_rydder}. Årsak: {kommentar}")
        st.session_state["toast_melding"] = f"🗑️ Token #{token_id_valgt} er frigjort av {hvem_rydder}."
        lagre_koe_til_fil()
        st.rerun()
    else:
        st.warning("Du må fylle ut ALL info: Velg et token, skriv hvem du er, og oppgi en årsak!")

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

with st.expander("🔍 Vis utvidet logg (Opptil 30 hendelser i dag)"):
    if len(st.session_state.logg) > 0:
        for hendelse in st.session_state.logg[:30]:
            st.write(hendelse)
    else:
        st.write("*Ingen hendelser loggført ennå.*")

st.write("---")

# 8. Feedback-seksjon (OGSÅ PAKKET INN I ET FORM)
st.header("⭐ Tilbakemeldinger på systemet")
gjennomsnitt = sum(st.session_state.ratings) / len(st.session_state.ratings)
st.subheader(f"Gjennomsnittlig rating: {gjennomsnitt:.1f} / 5.0 stjerner ({len(st.session_state.ratings)} stemmer)")

with st.form(key="feedback_form", clear_on_submit=True):
    stjerner = st.slider("Hvor mange stjerner gir du dette køsystemet?", min_value=1, max_value=5, value=5)
    tilbakemelding_tekst = st.text_area("Kommentar (valgfri):", placeholder="Hva kan forbedres?")
    submit_feedback = st.form_submit_button("Send tilbakemelding")

if submit_feedback:
    st.session_state.ratings.append(stjerner)
    if tilbakemelding_tekst.strip():
        tidspunkt_streng = naa_tid.strftime("%d.%m %H:%M")
        st.session_state.feedback_kommentarer.insert(0, f"[{tidspunkt_streng}] ⭐{stjerner}: {tilbakemelding_tekst}")

    lagre_feedback_til_fil()
    st.session_state["toast_melding"] = "⭐ Takk for tilbakemeldingen!"
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

# --- 🛠️ DET SUPER-HEMMELIGE PASSORD-SCOREBOARDET ---
if st.session_state.vis_secret_board:
    st.write("---")
    st.subheader("🏆 Det Hemmelige Scoreboardet (Kun fullførte print-timer)")

    if st.session_state.scoreboard:
        sortert_scoreboard = sorted(st.session_state.scoreboard.items(), key=lambda item: item[1], reverse=True)
        for plassering, (navn, totalt_brukte_tokens) in enumerate(sortert_scoreboard, 1):
            medalje = "🥇" if plassering == 1 else "🥈" if plassering == 2 else "🥉" if plassering == 3 else "👤"
            st.write(f"{medalje} **{navn}**: {totalt_brukte_tokens} timer fullført")
    else:
        st.write("*Ingen tokens har overlevd til automatisk frigjøring i dag ennå.*")