"""One step at a time: gentle tax help, one step at a time (hackathon project).

Screens and navigation only. The questions, documents, rules and prices live in
engine/case_types/<case type>/ and the logic lives in engine/. Nothing here knows about one case type.
The accountant's screens are in inbox.py.
"""

from datetime import date
from html import escape

import streamlit as st

import inbox
from engine import extract, flow, pack, rules, store

DEFAULT_CASE_TYPE = "after_a_death"  # the service shown first

st.set_page_config(page_title="One step at a time", layout="centered", initial_sidebar_state="collapsed")

CSS = """
<style>
h1, h2, h3 { color: #154618 !important; }
[data-testid="stToolbar"], footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stHeaderActionElements"] { display: none !important; }
.block-container { padding-top: 2.5rem; max-width: 760px; }
[class*="st-key-card"] { background: #FFFFFF; border-radius: 14px; padding: 1.4rem 1.6rem; border: 1px solid #D5E6D7; }
.stButton button, .stDownloadButton button, .stFormSubmitButton button { min-height: 3.1rem; border-radius: 10px; }
.stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"] { border-color: #154618; color: #154618; }
.stRadio [role="radiogroup"] { gap: 0.5rem; }
.tag { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-size: 15px; font-weight: 600; }
.tag-likely { background: #CFE6D1; color: #154618; }
table.quote { width: 100%; border-collapse: collapse; margin: 0.4rem 0; }
table.quote td { border: none; border-bottom: 1px solid #E4EEE5; padding: 0.55rem 0.2rem; }
table.quote td.price { text-align: right; white-space: nowrap; color: #475467; }
table.quote tr.total td { font-weight: 700; border-bottom: none; color: #154618; }
table.quote td.when { white-space: nowrap; font-weight: 600; width: 11.5rem; }
table.dates tr:last-child td { border-bottom: none; }
.muted { color: #475467 !important; font-size: 16px !important; }
.centre { text-align: center; }
.q-label { font-weight: 600; margin-bottom: 0.2rem; }
.hint { margin-top: 0; margin-bottom: 0.3rem; }
.note { background: #E6F2E7; border-left: 4px solid #154618; color: #154618; border-radius: 8px;
        padding: 0.8rem 1rem; margin-top: 0.4rem; margin-bottom: 0.6rem; }
</style>
"""


# ---------- state: a new case, or one loaded from the return code in the address ----------

def init_state():
    if "case" in st.session_state:
        return
    saved = None
    code = store.normalise_code(st.query_params.get("case", ""))
    if code:
        saved = store.load(code)
        if not saved:
            del st.query_params["case"]
            st.session_state.notice = "We could not find a case with that code. Please check it and try again."
    case_type = saved["case_type"] if saved else st.session_state.get("case_type", DEFAULT_CASE_TYPE)
    case = flow.load_case_type(case_type)
    st.session_state.case_type = case_type
    st.session_state.case = case
    st.session_state.code = saved["code"] if saved else None
    st.session_state.email = (saved["email"] or "") if saved else ""
    st.session_state.answers = flow.restore_answers(case, saved["answers"]) if saved else {}
    st.session_state.extracted = saved["extracted"] if saved else {}
    st.session_state.screen = min(saved["screen"], len(flow.screens(case)) - 1) if saved else 0
    st.session_state.family = case["questions"]["default_family"]
    if saved and store.open_requests(code):
        # The accountant has asked for something, so start on the documents screen.
        st.session_state.screen = flow.kind_index(case, "documents")


def ensure_code():
    """Every case gets a return code as soon as the person starts."""
    if not st.session_state.get("code"):
        st.session_state.code = store.create(st.session_state.case_type)
    return st.session_state.code


def autosave(index):
    """Save after every step, and keep the return code in the address so a refresh loses nothing."""
    if index == 0 and not st.session_state.get("code"):
        return
    code = ensure_code()
    if st.query_params.get("case") != code:
        st.query_params["case"] = code
    store.save(code, index, st.session_state.answers, st.session_state.extracted,
               st.session_state.get("email") or None)


def sidebar(case):
    families = case["questions"]["sample_families"]
    with st.sidebar:
        st.markdown("**Settings**")
        st.session_state.family = st.radio(
            "Sample family for document reading", families, index=families.index(st.session_state.family),
            format_func=lambda f: f"Family {f.upper()}", key="family_picker")
        st.caption("Used when an uploaded file name does not start with a family letter, like b_. "
                   "The sample files are in data/families/.")
        st.button("Open the accountant inbox", on_click=inbox.open_inbox, width="stretch")


def go(index):
    st.session_state.screen = index
    st.session_state.pop("pack", None)  # rebuilt next time the pack screen is shown


def start_again(case_type=None):
    """Clear this browser's session and go back to the welcome screen, for the same service or another.
    A saved case stays saved: the person can come back to it with their return code."""
    case_type = case_type or st.session_state.get("case_type", DEFAULT_CASE_TYPE)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.session_state.case_type = case_type


def open_case():
    """Carry on with a saved case, using the return code typed on the welcome screen."""
    code = store.normalise_code(st.session_state.get("return_code", ""))
    if code and store.load(code):
        start_again()
        st.query_params["case"] = code  # init_state loads it on the next run
    else:
        st.session_state.notice = "We could not find a case with that code. Please check it and try again."
        st.session_state.show_return = True


def delete_case():
    store.delete(st.session_state.code)
    start_again()
    st.session_state.notice = "Your case and documents have been deleted."


# ---------- small helpers ----------

def progress(case, screen):
    if "step" in screen:
        total = case["questions"]["steps_total"]
        st.progress(screen["step"] / total, text=f"Step {screen['step']} of {total}")


def nav_buttons(case, index, can_continue=True, continue_label="Continue", on_continue=go):
    st.write("")
    with st.container(horizontal=True, gap="medium"):  # stays side by side on narrow screens
        st.button("Back", on_click=go, args=(flow.back_index(index),), width="stretch", key=f"back_{index}")
        st.button(continue_label, type="primary", disabled=not can_continue, on_click=on_continue,
                  args=(flow.next_index(case, index),), width="stretch", key=f"next_{index}")
    if not can_continue:
        st.markdown('<p class="muted centre">Please answer the questions above to continue.</p>',
                    unsafe_allow_html=True)


def toggle(key):
    """Open or close a section. (An expander would close itself each time the person types in it.)"""
    st.session_state[key] = not st.session_state.get(key)


def save_email():
    st.session_state.email = st.session_state.get("email_input", "").strip()
    st.session_state.link_shown = True


def come_back_later():
    """Under every step: the return code, a link by email, and deleting the case."""
    code = st.session_state.get("code")
    if not code:
        return
    st.write("")
    st.button("Come back later", type="tertiary", on_click=toggle, args=("show_come_back",), width="stretch")
    if not st.session_state.get("show_come_back"):
        return
    with st.container(key="card_come_back"):
        st.markdown(f"Your answers are saved as you go. To carry on another time, enter this code on the "
                    f"first screen: **{code}**")
        st.text_input("Email address (optional)", value=st.session_state.email, key="email_input")
        st.button("Send me a link to come back", on_click=save_email)
        if st.session_state.get("link_shown"):
            st.markdown(f'<div class="note">No email is sent in this version. This is the link it would '
                        f'contain: <a href="?case={code}" target="_self">open my case</a></div>',
                        unsafe_allow_html=True)
        st.divider()
        if not st.session_state.get("confirm_delete"):
            st.button("Delete my case and documents", type="tertiary", key="ask_delete",
                      on_click=lambda: st.session_state.update(confirm_delete=True))
        else:
            st.markdown("This removes your answers and documents for good. It cannot be undone.")
            st.button("Yes, delete everything", on_click=delete_case, key="do_delete")
            st.button("No, keep my case", type="tertiary", key="keep_case",
                      on_click=lambda: st.session_state.update(confirm_delete=False))


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
    # escape: the label can include the first name the person typed.
    st.markdown(f'<p class="q-label">{escape(label)}</p>', unsafe_allow_html=True)
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
    notice = st.session_state.pop("notice", None)
    if notice:
        st.info(notice)
    with st.container(key="card_welcome"):
        st.markdown(screen["body"])
    st.write("")
    st.button(screen["button"], type="primary", on_click=go, args=(flow.next_index(case, index),),
              width="stretch")
    st.button("Already started? Carry on where you left off", type="tertiary", on_click=toggle,
              args=("show_return",), width="stretch")
    if st.session_state.get("show_return"):
        with st.container(key="card_return"):
            st.text_input("Your return code", key="return_code", placeholder="For example KTRM-4729")
            st.button("Open my case", on_click=open_case, width="stretch")
    others = [name for name in flow.case_type_names() if name != st.session_state.case_type]
    if others:
        st.write("")
        st.markdown('<p class="muted centre">Other services</p>', unsafe_allow_html=True)
        for name in others:
            st.button(flow.service_name(name), type="tertiary", on_click=start_again, args=(name,),
                      key=f"switch_{name}", width="stretch")


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
    result = st.session_state.extracted.pop(doc_id, None)
    if result and result.get("stored_file"):
        store.delete_file(st.session_state.code, result["stored_file"])
    st.session_state.pop(f"editing_{doc_id}", None)


def confirm_document(doc_id):
    st.session_state.extracted[doc_id]["confirmed"] = "yes"


def edit_document(doc_id):
    st.session_state[f"editing_{doc_id}"] = True


def save_corrections(doc, result, typed):
    """Keep what the person typed. For each value they changed, also keep what the document said."""
    corrections = dict(result.get("corrections") or {})
    for field, text in typed.items():
        text = text.strip().lstrip("£").strip()
        before = result["fields"].get(field)
        if text and text != extract.show_value("" if before is None else before):
            corrections.setdefault(field, {"read": before})["given"] = text
            result["fields"][field] = text
    result["corrections"] = corrections
    result["confirmed"] = "corrected" if corrections else "yes"
    result["missing_fields"] = [f for f in result.get("missing_fields", []) if not result["fields"].get(f)]
    st.session_state.pop(f"editing_{doc['id']}", None)


def show_confirm(doc, result):
    """Ask the person whether what we read is right, and let them change it."""
    doc_id = doc["id"]
    if result.get("confirmed") == "yes":
        st.caption("You told us this is right.")
    elif result.get("confirmed") == "corrected":
        changed = ", ".join(flow.field_label(f).lower() for f in result["corrections"])
        st.caption(f"You changed the {changed}. Your accountant will see both what the document said and "
                   "what you told us.")
    elif st.session_state.get(f"editing_{doc_id}"):
        with st.form(f"edit_{doc_id}", border=False):
            st.markdown('<p class="q-label">Change anything that is not right</p>', unsafe_allow_html=True)
            typed = {}
            for field in doc["fields"]:
                value = result["fields"].get(field)
                typed[field] = st.text_input(flow.field_label(field),
                                             value=extract.show_value("" if value is None else value))
            if st.form_submit_button("Save", type="primary", width="stretch"):
                save_corrections(doc, result, typed)
                st.rerun()
    else:
        st.markdown('<p class="q-label">Is this right?</p>', unsafe_allow_html=True)
        with st.container(horizontal=True, gap="medium"):
            st.button("Yes, that is right", key=f"confirm_{doc_id}", on_click=confirm_document,
                      args=(doc_id,), width="stretch")
            st.button("Change something", key=f"edit_button_{doc_id}", on_click=edit_document,
                      args=(doc_id,), width="stretch")


def show_found(doc, result, answers):
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
        check = rules.date_check(doc, result, answers)
        if check and check["same"]:
            st.caption(check["text"])
        elif check:
            st.markdown(f'<div class="note">{check["text"]}</div>', unsafe_allow_html=True)
        show_confirm(doc, result)


def show_requests(extracted):
    """Anything the accountant has asked for that has not been added since."""
    for request in store.open_requests(st.session_state.get("code") or ""):
        added = (extracted.get(request["doc_id"]) or {}).get("added", "")
        if added >= request["asked"]:
            continue  # added since the accountant asked; it goes with the next send
        message = f'<br>"{escape(request["message"])}"' if request["message"] else ""
        again = " If it is already listed below, remove it and add the new one." if added else ""
        st.markdown(f'<div class="note"><b>Your accountant has asked for this:</b> '
                    f'{escape(request["label"])}.{again}{message}</div>', unsafe_allow_html=True)


def show_documents(case, screen, index):
    answers = st.session_state.answers
    extracted = st.session_state.extracted
    st.header(screen["title"])
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)
    show_requests(extracted)

    items = flow.checklist(case, answers)
    added = sum(1 for doc in items if doc["id"] in extracted)
    st.markdown(f"**{added} of {len(items)} added**")

    for doc in items:
        with st.container(key=f"card_doc_{doc['id']}"):
            st.markdown(f"**{doc['label']}**")
            st.markdown(f'<p class="muted">{doc["hint"]}</p>', unsafe_allow_html=True)
            result = extracted.get(doc["id"])
            if result:
                show_found(doc, result, answers)
                st.button("Remove", key=f"remove_{doc['id']}", on_click=remove_document, args=(doc["id"],),
                          type="tertiary")
                continue
            upload = st.file_uploader(f"Add your {doc['label'].lower()}", type=["pdf", "png", "jpg", "jpeg"],
                                      key=f"upload_{doc['id']}", label_visibility="collapsed")
            if upload is not None:
                if doc.get("reads_as"):
                    with st.spinner("Reading your document..."):
                        result = extract.read_document(doc, upload.name, st.session_state.family)
                else:
                    result = {"read_ok": None}
                result["file_name"] = upload.name
                result["stored_file"] = store.save_file(ensure_code(), doc["id"], upload.name, upload.getvalue())
                result["added"] = store.now()
                extracted[doc["id"]] = result
                st.rerun()

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
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)

    for item in results["returns"]:
        result_card(item["id"], item, item["period"]["text"] if item["period"] else None)
    dates = results["key_dates"]
    with st.container(key="card_dates"):
        st.markdown(f"**{dates['title']}**")
        if dates["dates"]:
            rows = "".join(f"<tr><td class='when'>{d['text']}</td><td>{d['label']}</td></tr>"
                           for d in dates["dates"])
            st.markdown(f"<table class='quote dates'>{rows}</table>", unsafe_allow_html=True)
        st.write(dates["text"])

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


def send_pack(next_index):
    """Send the pack to the accountant inbox, then show the thank-you screen."""
    store.send(ensure_code(), st.session_state.pack[0])
    go(next_index)


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
        returns = "".join(f"- {r['title']}: **{r['status']}**\n" for r in data["results"]["returns"])
        st.markdown(
            f"- Your answers, in plain words\n"
            f"- {added} of {len(data['documents'])} documents, with what we found in them\n"
            f"{returns}"
            f"- Your fixed-fee quote")
        if data["points_to_check"]:
            st.markdown("**Points for your accountant to check**")
            st.markdown("\n".join(f"- {point}" for point in data["points_to_check"]))
        if data["missing_documents"]:
            st.markdown(f'<p class="muted">Still to send later: {", ".join(data["missing_documents"])}.</p>',
                        unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            st.download_button("Download PDF", pdf_bytes, file_name="handover-pack.pdf",
                               mime="application/pdf", on_click="ignore", width="stretch")
        with right:
            st.download_button("Download JSON", json_bytes, file_name="handover-pack.json",
                               mime="application/json", on_click="ignore", width="stretch")
    nav_buttons(case, index, continue_label="Send to an accountant", on_continue=send_pack)


def show_thanks(case, screen, index):
    code = st.session_state.get("code")
    saved = store.load(code) if code else None
    st.title(screen["title"])
    st.markdown(f'<p class="muted">{screen["intro"]}</p>', unsafe_allow_html=True)
    if saved and saved["status"]:
        st.markdown(f'<div class="note"><b>Where your case is now:</b> {store.STATUSES[saved["status"]][1]}</div>',
                    unsafe_allow_html=True)
    with st.container(key="card_thanks"):
        for n, text in enumerate(screen["steps"], start=1):
            st.markdown(f"**{n}.** {text}")
    st.markdown(f'<p class="muted">{screen["closing"]}</p>', unsafe_allow_html=True)
    if code:
        st.markdown(f'<p class="muted">Your return code is <b>{code}</b>. Enter it on the first screen to see '
                    'where your case is, or to add documents later.</p>', unsafe_allow_html=True)
    st.write("")
    st.button("Add or change documents", on_click=go, args=(flow.kind_index(case, "documents"),),
              width="stretch")
    st.button("Start a new case", type="tertiary", on_click=start_again, width="stretch")
    come_back_later()


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
    if inbox.is_open():
        inbox.show()
        return
    init_state()
    case = st.session_state.case
    index = st.session_state.screen
    screen = flow.screens(case)[index]
    if index > 0:
        ensure_code()
    sidebar(case)
    if st.session_state.get("shown_screen") != index:
        # A new screen: start at the top of the page.
        st.session_state.shown_screen = index
        st.html(f"<script>/* screen {index} */ window.scrollTo(0, 0);"
                "document.querySelector('[data-testid=\"stMain\"]')?.scrollTo(0, 0);</script>",
                unsafe_allow_javascript=True)
    progress(case, screen)
    SCREENS[screen["kind"]](case, screen, index)
    if "step" in screen:
        come_back_later()
    autosave(index)


main()
