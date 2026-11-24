"""One step at a time: gentle tax help after a death (hackathon demo).

Screens and navigation only. The questions, documents, rules and prices live in
engine/case_types/<case type>/ and the logic lives in engine/.
"""

from datetime import date

import streamlit as st

from engine import flow

CASE_TYPE = "after_a_death"

st.set_page_config(page_title="One step at a time", layout="centered", initial_sidebar_state="collapsed")

CSS = """
<style>
h1, h2, h3 { color: #134E4A !important; }
[data-testid="stToolbar"], footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; max-width: 760px; }
[class*="st-key-card"] { background: #FFFFFF; border-radius: 14px; padding: 1.4rem 1.6rem; border: 1px solid #D5E6DE; }
.stButton button, .stDownloadButton button { min-height: 3.1rem; border-radius: 10px; }
.stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"] { border-color: #0F766E; color: #0F766E; }
.stRadio [role="radiogroup"] { gap: 0.5rem; }
.demo-banner { background: #FFFFFF; border: 1px dashed #0F766E; color: #134E4A; border-radius: 8px;
               padding: 0.35rem 0.8rem; font-size: 15px; display: inline-block; margin-bottom: 1rem; }
.tag { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-size: 15px; font-weight: 600; }
.tag-likely { background: #CCE7E1; color: #134E4A; }
.tag-check { background: #FDF1D6; color: #7A4B00; }
.muted { color: #475467 !important; font-size: 16px !important; }
</style>
"""


def init_state():
    if "case" not in st.session_state:
        st.session_state.case = flow.load_case_type(CASE_TYPE)
        st.session_state.screen = 0
        st.session_state.answers = {}


def go(index):
    st.session_state.screen = index


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
    left, right = st.columns(2)
    with left:
        st.button("Back", on_click=go, args=(flow.back_index(index),), width="stretch", key=f"back_{index}")
    with right:
        st.button(continue_label, type="primary", disabled=not can_continue, on_click=go,
                  args=(flow.next_index(case, index),), width="stretch", key=f"next_{index}")


# ---------- question widgets ----------

def ask(question, answers):
    """Show one question and store the answer in answers."""
    qid = question["id"]
    label = flow.personalise(question["label"], answers)
    kind = question["type"]
    options = question.get("options", [])
    values = [o["value"] for o in options]
    labels = {o["value"]: o["label"] for o in options}

    if kind == "radio":
        current = answers.get(qid)
        answers[qid] = st.radio(label, values, index=values.index(current) if current in values else None,
                                format_func=labels.get, key=f"q_{qid}")
    elif kind == "checkboxes":
        st.markdown(f"**{label}**")
        chosen = set(answers.get(qid) or [])
        answers[qid] = [v for v in values if st.checkbox(labels[v], value=v in chosen, key=f"q_{qid}_{v}")]
    elif kind == "text":
        answers[qid] = st.text_input(label, value=answers.get(qid, ""), key=f"q_{qid}")
    elif kind == "date":
        answers[qid] = st.date_input(label, value=answers.get(qid), format="DD/MM/YYYY",
                                     min_value=date(2015, 1, 1), max_value=date.today(), key=f"q_{qid}")

    note = question.get("notes", {}).get(answers.get(qid)) if kind == "radio" else None
    if note:
        st.info(note)


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


def show_placeholder(case, screen, index):
    st.header(screen["title"])
    with st.container(key=f"card_{screen['id']}"):
        st.write("This screen is coming next.")
    nav_buttons(case, index)


def show_thanks(case, screen, index):
    st.title(screen["title"])
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)
    with st.container(key="card_thanks"):
        for n, text in enumerate(screen["steps"], start=1):
            st.markdown(f"**{n}.** {text}")
    st.caption("Demo: nothing has been sent to anyone.")
    st.write("")
    st.button("Start again", type="primary", on_click=start_again, width="stretch")


SCREENS = {
    "welcome": show_welcome,
    "questions": show_questions,
    "documents": show_placeholder,
    "results": show_placeholder,
    "pack": show_placeholder,
    "thanks": show_thanks,
}


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    case = st.session_state.case
    index = st.session_state.screen
    screen = flow.screens(case)[index]
    demo_banner(case)
    progress(case, screen)
    SCREENS[screen["kind"]](case, screen, index)


main()
