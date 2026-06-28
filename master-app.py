import streamlit as st
from datetime import datetime

# Tvinger Streamlit til å oppdatere siden automatisk hvert 10. sekund
try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=10000, key="daterefresh")
except ImportError:
    st.warning("Husk å kjøre 'pip install streamlit-autorefresh' i terminalen!")

# 1. Sette opp siden
st.set_page_config(page_title="Bambulab Køsystem", page_icon="🖨️", layout="centered")

naa_tid = datetime.now()
naa_tid_streng = naa_tid.strftime("%H:%M")

st.title("🖨️ Bambulab køen for GK MEK verksted")
st.subheader(f"🕒 Gjeldende klokkeslett: {naa_tid_streng}")

# Avdelingsinfo og Husk-meldinger
st.info("💡 **HUSK:** Legg fra deg de fysiske tokens ved printeren med en gang printen din starter!")
st.error("🔧 **Printerkrøll eller misnøye?** Hvis du ikke klarer å fikse det selv, henvend deg to **Automasjons Avd.**")

# 2. Sette opp "State" (Dataminne)
if "tokens" not in st.session_state:
    st.session_state.tokens = []
    # Genererer 24 tokens strukturert etter ønske
    for i in range(1, 25):
        time_tall = i
        timer_streng = f"{time_tall:02d}:00" if time_tall < 24 else "24:00"

        # KUN Token 1 til 7 er nattskift
        er_nattskift = 1 <= i <= 7

        st.session_state.tokens.append({
            "id": i,
            "tid": timer_streng,
            "bruker": "Ledig",
            "status": "Ledig",
            "nattskift": er_nattskift,
            "time_verdi": time_tall,
            "dag": "i_dag"
        })

if "logg" not in st.session_state:
    st.session_state.logg = ["Systemet startet. Alt klart for print!"]

if "ratings" not in st.session_state:
    st.session_state.ratings = [5, 5, 4]

# 3. Automatisk frigjøring av gamle timer (KUN for brikker merket med "i_dag")
naa_time = naa_tid.hour
if naa_time == 0:
    naa_time = 24

for slot in st.session_state.tokens:
    if slot["dag"] == "i_dag" and slot["time_verdi"] < naa_time and slot["status"] == "Booket":
        gammel_bruker = slot["bruker"]
        slot["bruker"] = "Ledig"
        slot["status"] = "Ledig"
        st.session_state.logg.insert(0,
                                     f"🤖 Automatisk frigjort: Tiden for Token #{slot['id']} ({slot['tid']}) har passert.")

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

        if book_for_i_morgen:
            start_soke_time = 8  # Starter på Token 8 neste dag
        else:
            start_soke_time = naa_time  # Starter fra nå-timen i dag

        # Lag en uavbrutt tidsrekke på 24 sammenhengende timer fremover
        for i in range(24):
            sjekk_time = ((start_soke_time - 1 + i) % 24) + 1
            token_obj = next(slot for slot in st.session_state.tokens if slot["time_verdi"] == sjekk_time)
            kronologisk_soke_koe.append((i, token_obj))

        # Sjekk og bygg listen over tillatte timer på rad
        valgte_slots = []
        antall_frigjort_pga_nattskift = 0

        for soke_index, slot in kronologisk_soke_koe:
            # Stopp letingen helt hvis vi har funnet nok timer
            if len(valgte_slots) == antall_tokens:
                break

            if slot["status"] == "Ledig":
                # KRITISK ENDRING: Hvis brikken er nattskift, og de IKKE har huket av:
                # Da KUTTES bookingen her. De resterende timene de ba om blir "frigjort/avvist".
                if slot["nattskift"] and not godkjent_nattskift:
                    antall_frigjort_pga_nattskift = antall_tokens - len(valgte_slots)
                    break  # Går rett ut av løkken, ingen flere timer tillates!

                valgte_slots.append((soke_index, slot))
            else:
                # Hvis en time midt i rekken allerede er booket av noen andre, må vi også stoppe (sammenhengende tid)
                break

        # Gjennomfør booking for de timene som faktisk ble godkjent
        if len(valgte_slots) > 0:
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

            # Loggføring og tilbakemelding
            logg_melding = f"⏱️ {medarbeider} booket {len(valgte_slots)} tokens (Kl. {første_token['tid']} til {siste_token['tid']})."
            if antall_frigjort_pga_nattskift > 0:
                logg_melding += f" ⚠️ {antall_frigjort_pga_nattskift} timer automatisk frigjort pga manglende nattskift-avtale."
                st.warning(
                    f"Du fikk booket {len(valgte_slots)} timer frem til nattskiftet startet, men de siste {antall_frigjort_pga_nattskift} timene ble automatisk frigjort/avvist fordi du ikke har huket av for avtale med nattskift!")
            else:
                st.success(f"Suksess! Du har booket {len(valgte_slots)} sammenhengende timer.")

            st.session_state.logg.insert(0, logg_melding)
            st.rerun()
        else:
            st.error(
                "Kunne ikke booke noen plasser. Enten er neste time opptatt, eller så starter nattskiftet umiddelbart og blokkerer søket ditt.")
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
st.header("⭐ Gi tilbakemelding på systemet")
gjennomsnitt = sum(st.session_state.ratings) / len(st.session_state.ratings)
st.subheader(f"Gjennomsnittlig rating: {gjennomsnitt:.1f} / 5.0 stjerner ({len(st.session_state.ratings)} stemmer)")

stjerner = st.slider("Hvor mange stjerner gir du dette køsystemet?", min_value=1, max_value=5, value=5)
tilbakemelding_tekst = st.text_area("Kommentar (valgfri):", placeholder="Hva kan forbedres?")

if st.button("Send tilbakemelding"):
    st.session_state.ratings.append(stjerner)
    st.success("Tusen takk for tilbakemeldingen din!")
    st.rerun()

st.write("---")

# 9. Signatur
st.markdown("<center><h4>Vibet av EY-FLYTTDG 🤘</h4></center>", unsafe_allow_html=True)