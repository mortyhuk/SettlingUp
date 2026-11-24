"""One step at a time: gentle tax help after a death (hackathon demo).

Screens and navigation only. The questions, documents, rules and prices live in
engine/case_types/<case type>/ and the logic lives in engine/.
"""

from datetime import date

import streamlit as st

from engine import extract, flow, pack, rules

CASE_TYPE = "after_a_death"

st.set_page_config(page_title="One step at a time", layout="centered", initial_sidebar_state="collapsed")

CSS = """
<style>
h1, h2, h3 { color: #134E4A !important; }
[data-testid="stToolbar"], footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stHeaderActionElements"] { display: none !important; }
.block-container { padding-top: 2.5rem; max-width: 760px; }
[class*="st-key-card"] { background: #FFFFFF; border-radius: 14px; padding: 1.4rem 1.6rem; border: 1px solid #D5E6DE; }
.stButton button, .stDownloadButton button { min-height: 3.1rem; border-radius: 10px; }
.stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"] { border-color: #0F766E; color: #0F766E; }
.stRadio [role="radiogroup"] { gap: 0.5rem; }
.demo-banner { background: #FFFFFF; border: 1px dashed #0F766E; color: #134E4A; border-radius: 8px;
               padding: 0.35rem 0.8rem; font-size: 15px; display: inline-block; margin-bottom: 1rem; }
.tag { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-size: 15px; font-weight: 600; }
.tag-likely { background: #CCE7E1; color: #134E4A; }
.demo-rules { background: #FDF1D6; color: #7A4B00; border-radius: 8px; padding: 0.6rem 0.9rem;
              font-weight: 600; margin-bottom: 1rem; }
table.quote { width: 100%; border-collapse: collapse; margin: 0.4rem 0; }
table.quote td { border: none; border-bottom: 1px solid #E4EEE9; padding: 0.55rem 0.2rem; }
table.quote td.price { text-align: right; white-space: nowrap; color: #475467; }
table.quote tr.total td { font-weight: 700; border-bottom: none; color: #134E4A; }
.muted { color: #475467 !important; font-size: 16px !important; }
.centre { text-align: center; }
.q-label { font-weight: 600; margin-bottom: 0.2rem; }
.hint { margin-top: 0; margin-bottom: 0.3rem; }
.note { background: #E6F2EE; border-left: 4px solid #0F766E; color: #134E4A; border-radius: 8px;
        padding: 0.8rem 1rem; margin-top: 0.4rem; }
</style>
"""


def init_state():
    if "case" not in st.session_state:
        st.session_state.case = flow.load_case_type(CASE_TYPE)
        st.session_state.screen = 0
        st.session_state.answers = {}
        st.session_state.extracted = {}
        st.session_state.family = "b"


def demo_sidebar():
    with st.sidebar:
        st.markdown("**Demo settings**")
        st.session_state.family = st.radio(
            "Sample family for document reading", ["a", "b", "c"], index=["a", "b", "c"].index(st.session_state.family),
            format_func=lambda f: f"Family {f.upper()}", key="family_picker")
        st.caption("Used when an uploaded file name does not start with a_, b_ or c_. "
                   "The sample files are in data/families/.")


def go(index):
    st.session_state.screen = index
    st.session_state.pop("pack", None)  # rebuilt next time the pack screen is shown


def start_again():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------- small helpers ----------

def demo_banner(case):
    st.markdown(f'<div class="demo-banner">{case["questions"]["demo_banner"]}</div>', unsafe_allow_html=True)


def progress(case, screen):
    if "step" in screen:
        total = case["questions"]["steps_total"]
        st.progress(screen["step"] / total, text=f"Step {screen['step']} of {total}")


def nav_buttons(case, index, can_continue=True, continue_label="Continue"):
    st.write("")
    with st.container(horizontal=True, gap="medium"):  # stays side by side on narrow screens
        st.button("Back", on_click=go, args=(flow.back_index(index),), width="stretch", key=f"back_{index}")
        st.button(continue_label, type="primary", disabled=not can_continue, on_click=go,
                  args=(flow.next_index(case, index),), width="stretch", key=f"next_{index}")
    if not can_continue:
        st.markdown('<p class="muted centre">Please answer the questions above to continue.</p>',
                    unsafe_allow_html=True)


# ---------- question widgets ----------

def ask(question, answers):
    """Show one question and store the answer in answers."""
    qid = question["id"]
    label = flow.personalise(question["label"], answers)
    kind = question["type"]
    options = question.get("options", [])
    values = [o["value"] for o in options]
    labels = {o["value"]: o["label"] for o in options}

    # Show the label (and hint) ourselves, so every question looks the same.
    st.markdown(f'<p class="q-label">{label}</p>', unsafe_allow_html=True)
    if question.get("hint"):
        st.markdown(f'<p class="muted hint">{question["hint"]}</p>', unsafe_allow_html=True)
    show_label = "collapsed"

    if kind == "radio":
        current = answers.get(qid)
        answers[qid] = st.radio(label, values, index=values.index(current) if current in values else None,
                                format_func=labels.get, key=f"q_{qid}", label_visibility=show_label)
    elif kind == "checkboxes":
        chosen = set(answers.get(qid) or [])
        answers[qid] = [v for v in values if st.checkbox(labels[v], value=v in chosen, key=f"q_{qid}_{v}")]
    elif kind == "text":
        answers[qid] = st.text_input(label, value=answers.get(qid, ""), key=f"q_{qid}",
                                     label_visibility=show_label)
    elif kind == "date":
        answers[qid] = st.date_input(label, value=answers.get(qid), format="DD/MM/YYYY",
                                     min_value=date(2015, 1, 1), max_value=date.today(), key=f"q_{qid}",
                                     label_visibility=show_label)

    note = question.get("notes", {}).get(answers.get(qid)) if kind == "radio" else None
    if note:
        st.markdown(f'<div class="note">{note}</div>', unsafe_allow_html=True)


# ---------- screens ----------

def show_welcome(case, screen, index):
    st.title(screen["title"])
    with st.container(key="card_welcome"):
        st.markdown(screen["body"])
    st.write("")
    st.button(screen["button"], type="primary", on_click=go, args=(flow.next_index(case, index),),
              width="stretch")


def show_questions(case, screen, index):
    answers = st.session_state.answers
    st.header(screen["title"])
    if screen.get("intro"):
        st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)
    with st.container(key=f"card_{screen['id']}"):
        for i, question in enumerate(screen["questions"]):
            if i:
                st.write("")
            ask(question, answers)
    nav_buttons(case, index, can_continue=flow.is_complete(screen, answers))


def remove_document(doc_id):
    st.session_state.extracted.pop(doc_id, None)


def show_found(doc, result):
    file_name = result["file_name"]
    if not doc.get("reads_as"):
        st.success(f"Added **{file_name}**. Your accountant will go through these records.")
    elif not result["read_ok"]:
        st.warning(f"Added **{file_name}**. We could not read this one automatically. "
                   "That is fine. Your accountant will look at it.")
    else:
        st.success(f"**What we found:** {extract.describe(doc['found'], result['fields'])}")
        st.caption(f"Read from {file_name}")
        if result["missing_fields"]:
            missing = ", ".join(f.replace("_", " ") for f in result["missing_fields"])
            st.caption(f"Some details were not clear ({missing}). Your accountant will check them.")


def show_documents(case, screen, index):
    answers = st.session_state.answers
    extracted = st.session_state.extracted
    st.header(screen["title"])
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)

    items = flow.checklist(case, answers)
    added = sum(1 for doc in items if doc["id"] in extracted)
    st.markdown(f"**{added} of {len(items)} added**")

    for doc in items:
        with st.container(key=f"card_doc_{doc['id']}"):
            st.markdown(f"**{doc['label']}**")
            st.markdown(f'<p class="muted">{doc["hint"]}</p>', unsafe_allow_html=True)
            result = extracted.get(doc["id"])
            if result:
                show_found(doc, result)
                st.button("Remove", key=f"remove_{doc['id']}", on_click=remove_document, args=(doc["id"],),
                          type="tertiary")
                continue
            upload = st.file_uploader(f"Add your {doc['label'].lower()}", type=["pdf", "png", "jpg", "jpeg"],
                                      key=f"upload_{doc['id']}", label_visibility="collapsed")
            if upload is not None:
                if doc.get("reads_as"):
                    with st.spinner("Reading your document..."):
                        result = extract.read_document(doc["reads_as"], upload.name, st.session_state.family)
                else:
                    result = {"read_ok": None}
                result["file_name"] = upload.name
                extracted[doc["id"]] = result
                st.rerun()

    st.caption("Demo: document reading shows prepared sample results. No real documents are used.")
    nav_buttons(case, index)


def result_card(key, item, extra=None):
    with st.container(key=f"card_{key}"):
        st.markdown(f"**{item['title']}**")
        st.markdown(f'<span class="tag tag-likely">{item["status"]}</span>', unsafe_allow_html=True)
        st.write(item["text"])
        if extra:
            st.markdown(f'<p class="muted">{extra}</p>', unsafe_allow_html=True)


def show_results(case, screen, index):
    results = rules.evaluate(case, st.session_state.answers, st.session_state.extracted)
    st.header(screen["title"])
    st.markdown(f'<div class="demo-rules">{results["label"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)

    final = results["final_return"]
    result_card("final", final, final["period"]["text"] if final["period"] else None)
    result_card("estate", results["estate_return"])
    with st.container(key="card_dates"):
        st.markdown(f"**{results['key_dates']['title']}**")
        st.write(results["key_dates"]["text"])

    if results["missing_documents"]:
        with st.container(key="card_missing"):
            st.markdown("**Still to send**")
            st.write("That is fine. You can send these to your accountant later:")
            st.markdown("\n".join(f"- {label}" for label in results["missing_documents"]))

    q = results["quote"]
    with st.container(key="card_quote"):
        st.markdown(f"**{q['title']}**")
        rows = "".join(f"<tr><td>{line['label']}</td><td class='price'>{line['price']}</td></tr>"
                       for line in q["lines"])
        rows += f"<tr class='total'><td>{q['total_label']}</td><td class='price'>{q['total']}</td></tr>"
        st.markdown(f"<table class='quote'>{rows}</table>", unsafe_allow_html=True)
        st.caption(q["note"])
    nav_buttons(case, index)


def show_pack(case, screen, index):
    if "pack" not in st.session_state:
        results = rules.evaluate(case, st.session_state.answers, st.session_state.extracted)
        data = pack.build(case, st.session_state.answers, results)
        json_bytes, pdf_bytes = pack.to_json(data), pack.to_pdf(data)
        pack.save(data, json_bytes, pdf_bytes)
        st.session_state.pack = (data, json_bytes, pdf_bytes)
    data, json_bytes, pdf_bytes = st.session_state.pack

    st.header(screen["title"])
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)
    added = sum(1 for d in data["documents"] if d["status"] != "missing")
    with st.container(key="card_pack"):
        st.markdown("**In your pack**")
        st.markdown(
            f"- Your answers, in plain words\n"
            f"- {added} of {len(data['documents'])} documents, with what we found in them\n"
            f"- Final personal tax return: **{data['results']['final_return']['status']}**\n"
            f"- Estate tax return: **{data['results']['estate_return']['status']}**\n"
            f"- Your fixed-fee quote")
        if data["missing_documents"]:
            st.markdown(f'<p class="muted">Still to send later: {", ".join(data["missing_documents"])}.</p>',
                        unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            st.download_button("Download PDF", pdf_bytes, file_name="handover-pack-demo.pdf",
                               mime="application/pdf", on_click="ignore", width="stretch")
        with right:
            st.download_button("Download JSON", json_bytes, file_name="handover-pack-demo.json",
                               mime="application/json", on_click="ignore", width="stretch")
    st.caption("Demo: the pack uses made-up data and demo rules.")
    nav_buttons(case, index, continue_label="Send to an accountant (demo)")


def show_thanks(case, screen, index):
    st.title(screen["title"])
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)
    with st.container(key="card_thanks"):
        for n, text in enumerate(screen["steps"], start=1):
            st.markdown(f"**{n}.** {text}")
    st.markdown(f'<p class="muted">{screen["closing"]}</p>', unsafe_allow_html=True)
    st.caption("Demo: nothing has been sent to anyone.")
    st.write("")
    st.button("Start again", type="primary", on_click=start_again, width="stretch")


SCREENS = {
    "welcome": show_welcome,
    "questions": show_questions,
    "documents": show_documents,
    "results": show_results,
    "pack": show_pack,
    "thanks": show_thanks,
}


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    demo_sidebar()
    case = st.session_state.case
    index = st.session_state.screen
    screen = flow.screens(case)[index]
    if st.session_state.get("shown_screen") != index:
        # A new screen: start at the top of the page.
        st.session_state.shown_screen = index
        st.html(f"<script>/* screen {index} */ window.scrollTo(0, 0);"
                "document.querySelector('[data-testid=\"stMain\"]')?.scrollTo(0, 0);</script>",
                unsafe_allow_javascript=True)
    demo_banner(case)
    progress(case, screen)
    SCREENS[screen["kind"]](case, screen, index)


main()
