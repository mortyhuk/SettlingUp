"""The accountant's inbox: packs people have sent, where each one is, and asking for a document.

Screens only. Cases are read and changed through engine/store.py. There is no sign-in yet, so anyone
who opens this screen can see it. Made-up data only.
"""

from datetime import datetime
from html import escape

import streamlit as st

from engine import pack, store


def is_open():
    return st.query_params.get("view") == "accountant"


def open_inbox():
    st.query_params["view"] = "accountant"


def close_inbox():
    del st.query_params["view"]
    st.session_state.pop("inbox_case", None)


def open_case(code):
    st.session_state.inbox_case = code


def back_to_list():
    st.session_state.pop("inbox_case", None)


def when(text):
    """'2026-11-24T15:10:00' becomes '24 November 2026 at 15:10'."""
    moment = datetime.fromisoformat(text)
    return f"{moment.day} {moment:%B %Y} at {moment:%H:%M}"


def change_status(code):
    store.set_status(code, st.session_state[f"status_{code}"])


def ask_for_document(code, labels):
    doc_id = st.session_state[f"ask_doc_{code}"]
    store.ask_for(code, doc_id, labels[doc_id], st.session_state.get(f"ask_message_{code}", ""))
    st.session_state[f"ask_message_{code}"] = ""


def show():
    code = st.session_state.get("inbox_case")
    case = store.load(code) if code else None
    if case and case["status"]:
        show_case(case)
    else:
        show_list()


def show_list():
    st.title("Accountant inbox")
    st.markdown('<p class="muted">Packs people have sent, newest first.</p>', unsafe_allow_html=True)
    cases = store.sent_cases()
    if not cases:
        st.info("No packs have been sent yet.")
    for case in cases:
        data, code = case["pack"], case["code"]
        added = sum(1 for d in data["documents"] if d["status"] != "missing")
        points = len(data["points_to_check"])
        with st.container(key=f"card_inbox_{code}"):
            st.markdown(f"**{data['service']}** · {code}")
            st.markdown(f'<span class="tag tag-likely">{store.STATUSES[case["status"]][0]}</span>',
                        unsafe_allow_html=True)
            st.markdown(f'<p class="muted">Sent {when(case["sent"])}. {added} of {len(data["documents"])} '
                        f'documents. {points} {"point" if points == 1 else "points"} to check.</p>',
                        unsafe_allow_html=True)
            st.button("Open", key=f"open_{code}", on_click=open_case, args=(code,), width="stretch")
    st.write("")
    st.button("Back to the customer's screens", type="tertiary", on_click=close_inbox, width="stretch")


def table(rows):
    """A plain two-column table, in the same style as the quote."""
    html = "".join(f"<tr><td>{escape(str(left))}</td><td><b>{escape(str(right))}</b></td></tr>"
                   for left, right in rows)
    st.markdown(f"<table class='quote dates'>{html}</table>", unsafe_allow_html=True)


def show_case(case):
    data, code = case["pack"], case["code"]
    results = data["results"]
    st.button("Back to the inbox", type="tertiary", on_click=back_to_list)
    st.header(f"{data['service']} · {code}")
    st.markdown(f'<p class="muted">Sent {when(case["sent"])}. Rules version {results["rules_version"]}.</p>',
                unsafe_allow_html=True)
    statuses = list(store.STATUSES)
    st.selectbox("Status", statuses, index=statuses.index(case["status"]), key=f"status_{code}",
                 format_func=lambda s: store.STATUSES[s][0], on_change=change_status, args=(code,))

    with st.container(key="card_inbox_points"):
        st.markdown("**Points to check**")
        if data["points_to_check"]:
            st.markdown("\n".join(f"- {point}" for point in data["points_to_check"]))
        else:
            st.write("No extra points were flagged from the answers or documents.")

    with st.container(key="card_inbox_results"):
        st.markdown("**Results**")
        for item in results["returns"]:
            period = f" {item['period']['text']}" if item["period"] else ""
            st.markdown(f"**{item['title']}: {item['status']}.** {item['text']}{period}")
        if results["key_dates"]["dates"]:
            st.markdown("**Key dates**")
            table((d["text"], d["label"]) for d in results["key_dates"]["dates"])

    with st.container(key="card_inbox_documents"):
        st.markdown("**Documents**")
        for doc in data["documents"]:
            st.markdown(f"**{doc['label']}** · {pack.STATUS_WORDS[doc['status']]}")
            if doc["summary"]:
                st.write(doc["summary"])
            original = store.read_file(code, doc["stored_file"]) if doc.get("stored_file") else None
            if original:
                st.download_button(f"Download {doc['file_name']}", original, file_name=doc["file_name"],
                                   key=f"file_{code}_{doc['id']}", on_click="ignore", type="tertiary")

    with st.container(key="card_inbox_ask"):
        st.markdown("**Ask for a document**")
        for request in case["requests"]:
            state = "received" if request["done"] else "waiting"
            st.markdown(f"- {request['label']}: asked {when(request['asked'])}, {state}")
        docs = sorted(data["documents"], key=lambda d: d["status"] != "missing")  # missing ones first
        labels = {d["id"]: d["label"] for d in docs}
        st.selectbox("Which document?", list(labels), key=f"ask_doc_{code}",
                     format_func=lambda i: f"{labels[i]} ({pack.STATUS_WORDS[next(d['status'] for d in docs if d['id'] == i)].lower()})")
        st.text_area("Message to the person (optional)", key=f"ask_message_{code}")
        st.button("Ask for this document", type="primary", on_click=ask_for_document, args=(code, labels),
                  width="stretch")
        st.caption("The person sees this the next time they open their case.")

    with st.container(key="card_inbox_answers"):
        st.markdown("**About the case**")
        table((row["question"], row["answer"]) for row in data["answers_in_words"])

    quote = data["quote"]
    with st.container(key="card_inbox_quote"):
        st.markdown(f"**{quote['title']}**")
        table([(line["label"], line["price"]) for line in quote["lines"]] + [(quote["total_label"], quote["total"])])

    st.download_button("Download the pack (PDF)", pack.to_pdf(data), file_name=f"handover-pack-{code}.pdf",
                       mime="application/pdf", on_click="ignore", width="stretch")
