"""
ProspectKeeper Dashboard — Streamlit Frontend
Four views:
  1. All Contacts — filterable table
  2. Human Review Queue — flagged contacts needing attention
  3. Run Agent — trigger a batch verification job
  4. Value-Proof Receipt — ROI telemetry from the latest batch
"""

import asyncio
import sys
import os
from pathlib import Path

import streamlit as st
import pandas as pd

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prospectkeeper.infrastructure.config import Config
from prospectkeeper.infrastructure.container import Container
from prospectkeeper.use_cases.process_batch import ProcessBatchRequest
from prospectkeeper.domain.entities.contact import ContactStatus

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ProspectKeeper",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_container() -> Container:
    config = Config.from_env()
    return Container(config)


def run_async(coro):
    """Run an async coroutine from sync Streamlit context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


STATUS_COLORS = {
    "active":    "🟢",
    "inactive":  "🔴",
    "unknown":   "🟡",
    "opted_out": "⚫",
}

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.title("🔍 ProspectKeeper")
st.sidebar.caption("Autonomous B2B Contact Maintenance")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["All Contacts", "Human Review Queue", "Run Agent", "Value-Proof Receipt"],
    index=0,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page: All Contacts
# ─────────────────────────────────────────────────────────────────────────────
if page == "All Contacts":
    st.title("📋 All Contacts")

    try:
        container = get_container()
        contacts = run_async(container.repository.get_all_contacts())

        if not contacts:
            st.info("No contacts found. Add contacts via the Supabase dashboard or seed data.")
            st.stop()

        # Convert to DataFrame
        rows = [
            {
                "Status":        STATUS_COLORS.get(c.status.value, "❓") + " " + c.status.value.capitalize(),
                "Name":          c.name,
                "Email":         c.email,
                "Title":         c.title,
                "Organization":  c.organization,
                "Review":        "⚠️ Yes" if c.needs_human_review else "",
                "ID":            c.id,
            }
            for c in contacts
        ]
        df = pd.DataFrame(rows)

        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.multiselect(
                "Filter by status",
                options=["active", "inactive", "unknown"],
                default=["active", "inactive", "unknown"],
            )
        with col2:
            search = st.text_input("Search name or org", "")

        filtered = df[
            df["Status"].str.lower().str.contains("|".join(status_filter), na=False)
        ]
        if search:
            mask = (
                filtered["Name"].str.contains(search, case=False, na=False)
                | filtered["Organization"].str.contains(search, case=False, na=False)
            )
            filtered = filtered[mask]

        st.dataframe(
            filtered.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(filtered)} of {len(df)} contacts shown")

    except EnvironmentError as e:
        st.error(f"Configuration error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Page: Human Review Queue
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Human Review Queue":
    st.title("⚠️ Human Review Queue")
    st.caption(
        "Contacts the agent could not resolve confidently. "
        "Resolve each by updating their status in Supabase."
    )

    try:
        container = get_container()
        contacts = run_async(container.repository.get_contacts_needing_review())

        if not contacts:
            st.success("Queue is empty — no contacts need review right now.")
            st.stop()

        st.metric("Contacts awaiting review", len(contacts))

        for contact in contacts:
            with st.expander(f"**{contact.name}** — {contact.organization}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title:** {contact.title}")
                    st.write(f"**Email:** {contact.email}")
                    st.write(f"**Status:** {contact.status.value}")
                with col2:
                    st.write(f"**Review reason:**")
                    st.warning(contact.review_reason or "No reason provided")
                    if contact.district_website:
                        st.write(f"**Website:** {contact.district_website}")

    except EnvironmentError as e:
        st.error(f"Configuration error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Page: Run Agent
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Run Agent":
    st.title("🤖 Run Batch Verification")

    st.markdown("""
    The agent processes contacts through two cost-aware tiers:
    | Tier | Method | Cost |
    |------|--------|------|
    | 1 | Website scraping | $0.00 |
    | 2 | AI deep research via Claude (Langfuse-traced) | ~$0.01-0.05/contact |
    """)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        batch_size = st.slider("Contacts to process", min_value=1, max_value=200, value=50)
    with col2:
        concurrency = st.slider("Parallel workers", min_value=1, max_value=10, value=5)

    if st.button("▶ Run Batch Now", type="primary", use_container_width=True):
        try:
            container = get_container()

            with st.spinner(f"Processing {batch_size} contacts..."):
                response = run_async(
                    container.process_batch_use_case.execute(
                        ProcessBatchRequest(
                            limit=batch_size,
                            concurrency=concurrency,
                        )
                    )
                )

            st.success("Batch complete!")
            st.session_state["last_receipt"] = response.receipt

            if response.errors:
                st.warning(f"{len(response.errors)} errors occurred:")
                for err in response.errors[:5]:
                    st.code(err)

            # Quick summary
            r = response.receipt
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Processed", r.contacts_processed)
            c2.metric("Active", r.contacts_verified_active)
            c3.metric("Replacements", r.replacements_found)
            c4.metric("Flagged", r.flagged_for_review)

            st.info("View the full Value-Proof Receipt in the sidebar →")

        except EnvironmentError as e:
            st.error(f"Configuration error: {e}")
        except Exception as e:
            st.error(f"Batch failed: {e}")
            raise

# ─────────────────────────────────────────────────────────────────────────────
# Page: Value-Proof Receipt
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Value-Proof Receipt":
    st.title("💰 Value-Proof Receipt")
    st.caption("Live ROI telemetry — auto-generated after each batch run")

    receipt = st.session_state.get("last_receipt")

    if receipt is None:
        st.info("No batch has been run in this session. Go to **Run Agent** to start one.")
        st.stop()

    r = receipt

    # ── Hero ROI number ──────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1a1a2e, #16213e);
                    padding: 32px; border-radius: 16px; text-align: center; margin-bottom: 24px;">
            <p style="color: #aaa; margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 2px;">Net ROI This Run</p>
            <p style="color: #00ff88; font-size: 72px; font-weight: 900; margin: 8px 0;">
                +{r.net_roi_percentage:,.0f}%
            </p>
            <p style="color: #ccc; font-size: 14px; margin: 0;">
                ${r.total_value_generated_usd:.2f} value generated
                vs ${r.total_api_cost_usd:.4f} API cost
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── KPI metrics grid ─────────────────────────────────────────────────────
    st.subheader("Batch Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Contacts Processed",   r.contacts_processed)
    c2.metric("Verified Active",       r.contacts_verified_active)
    c3.metric("Marked Inactive",       r.contacts_marked_inactive)
    c4.metric("Replacements Found",    r.replacements_found)
    c5.metric("Flagged for Review",    r.flagged_for_review)

    st.divider()

    # ── Economics breakdown ──────────────────────────────────────────────────
    st.subheader("Economics Breakdown")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Costs**")
        cost_data = {
            "Item": ["Total API Cost", "Cost per Contact", "Cost per Replacement"],
            "Amount": [
                f"${r.total_api_cost_usd:.4f}",
                f"${r.cost_per_contact_usd:.6f}",
                f"${r.cost_per_replacement_usd:.4f}" if r.replacements_found else "N/A",
            ],
        }
        st.table(pd.DataFrame(cost_data))

    with col_b:
        st.markdown("**Value Generated**")
        value_data = {
            "Item": ["SDR Hours Saved", "Value at $30/hr", "Tokens Used"],
            "Amount": [
                f"{r.total_labor_hours_saved:.2f} hrs",
                f"${r.total_value_generated_usd:.2f}",
                f"{r.total_tokens_used:,}",
            ],
        }
        st.table(pd.DataFrame(value_data))

    st.divider()

    # ── Simulated Invoice ────────────────────────────────────────────────────
    st.subheader("📄 Simulated Outcome-Based Invoice")
    st.markdown(
        f"""
        | Line Item | Qty | Unit Price | Total |
        |-----------|-----|-----------|-------|
        | Contact Verifications | {r.contacts_processed} | $0.10 | ${r.contacts_processed * 0.10:.2f} |
        | Replacement Contacts Found | {r.replacements_found} | $2.50 | ${r.replacements_found * 2.50:.2f} |
        | **Total Invoice** | | | **${r.simulated_invoice_usd:.2f}** |
        """
    )
    st.caption(
        "Outcome-based pricing: you only pay for verified results. "
        "Compare to ZoomInfo's $10,000+/year flat fee."
    )

    st.divider()

    # ── Raw receipt string ───────────────────────────────────────────────────
    st.subheader("Receipt Text")
    st.code(r.format_receipt(), language=None)

    # ── Helicone link ────────────────────────────────────────────────────────
    st.info(
        "🔭 LLM observability: View token costs, latency, and per-contact traces in your "
        "[Helicone dashboard](https://helicone.ai/dashboard).",
        icon="📡",
    )
