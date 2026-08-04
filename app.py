import os
import re
import shlex
import subprocess
import streamlit as st

st.set_page_config(
    page_title="svtplay-dl Web UI",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 svtplay-dl Web UI")
st.markdown("Ladda ner video från SVT Play och andra understödda tjänster.")

def clean_log_line(line: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    line = ansi_escape.sub('', line)
    if '\r' in line:
        line = line.split('\r')[-1]
    return line.strip()

# --- FORMULÄR OCH INPUTS ---
with st.form(key="download_form"):
    st.markdown("**Länkar:**")
    
    # Filuppladdning för .txt-filer
    uploaded_file = st.file_uploader(
        "Ladda upp en textfil (.txt) med länkarna (en per rad)",
        type=["txt"]
    )

    urls_input = st.text_area(
        "Eller klistra in URL:er (En per rad)",
        placeholder="https://www.svtplay.se/video/...\nhttps://www.svtplay.se/video/..."
    )

    col1, col2 = st.columns(2)

    with col1:
        quality = st.selectbox(
            "Kvalitet / Upplösning",
            options=["Bästa tillgängliga", "1080", "720", "480", "360"],
            index=0
        )
        all_episodes = st.checkbox("Ladda ned alla avsnitt / hel serie (-A)", value=False)
        subtitles = st.checkbox("Ladda ner undertexter (-S)", value=True)
        all_subtitles = st.checkbox("Alla undertexter (--all-subtitles)", value=False)

    with col2:
        output_dir = st.text_input(
            "Utdatamapp (--output)",
            value=os.path.expanduser("~/Downloads")
        )
        merge_subtitle = st.checkbox("Baka in undertext i videon (--merge-subtitle)", value=True)
        audio_only = st.checkbox("Endast ljud (--audio-only)", value=False)

    extra_flags = st.text_input("Extra flaggor (valfritt)", placeholder="--force")
    submit_button = st.form_submit_button(label="🚀 Starta nedladdning", type="primary")

# --- KÖRNING OCH LOGIK ---
if submit_button:
    urls = []

    # 1. Om en fil har laddats upp, läs URL:er från den
    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8")
        file_urls = [u.strip() for u in file_content.splitlines() if u.strip()]
        urls.extend(file_urls)

    # 2. Lägg till eventuella URL:er från textrutan också
    if urls_input.strip():
        text_urls = [u.strip() for u in urls_input.split('\n') if u.strip()]
        urls.extend(text_urls)

    # Ta bort eventuella dubbletter om samma länk råkade finnas i både fil och textruta
    urls = list(dict.fromkeys(urls))

    if not urls:
        st.error("Du måste antingen ladda upp en fil eller klistra in minst en URL.")
    else:
        expanded_output_dir = os.path.expanduser(output_dir.strip())
        os.makedirs(expanded_output_dir, exist_ok=True)

        st.info(f"Hittade totalt {len(urls)} URL:er att ladda ner.")

        # Loopa igenom varje URL i listan
        for index, url in enumerate(urls, start=1):
            st.markdown(f"### 📥 Laddar ner fil {index} av {len(urls)}")
            st.write(f"**URL:** `{url}`")

            cmd = ["svtplay-dl"]
            if all_episodes: cmd.append("-A")
            cmd.append(url)
            cmd.extend(["--output", expanded_output_dir])
            if quality != "Bästa tillgängliga": cmd.extend(["--quality", quality])
            if subtitles: cmd.append("-S")
            if all_subtitles: cmd.append("--all-subtitles")
            if merge_subtitle: cmd.append("--merge-subtitle")
            if audio_only: cmd.append("--audio-only")
            if extra_flags.strip(): cmd.extend(shlex.split(extra_flags.strip()))

            log_box = st.empty()
            log_lines = []

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                with st.spinner(f"Bearbetar länk {index}..."):
                    for raw_line in iter(process.stdout.readline, ""):
                        cleaned = clean_log_line(raw_line)
                        if cleaned:
                            log_lines.append(cleaned)
                            log_box.code("\n".join(log_lines[-15:]), language="text")

                    process.stdout.close()
                    return_code = process.wait()

                if return_code == 0:
                    st.success(f"✅ Klar med fil {index}!")
                else:
                    st.error(f"❌ Misslyckades med fil {index}. Felkod: {return_code}")

            except Exception as e:
                st.error(f"Ett fel uppstod med länk {index}: {e}")
        
        st.balloons()
        st.success("🎉 Alla nedladdningar i kön är slutförda!")
