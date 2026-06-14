import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# 1. Page Configuration
st.set_page_config(
    page_title="Cloud CRM — Lead Tracker",
    page_icon="💼",
    layout="wide"
)

st.title("💼 Cloud CRM — Lead & Prospectus Tracker")
st.markdown("### Powered by Google Sheets Sync")

# 2. Establish Cloud Database Connection
# This links to the Google Sheet URL you will place in your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # ttl="0" disables caching so data is instantly read fresh on every action
    df = conn.read(ttl="0")
except Exception:
    # Fallback structure if the Google Sheet is completely blank/newly initialized
    df = pd.DataFrame(columns=[
        'id', 'name', 'company', 'email', 'status', 
        'prospectus_notes', 'followup_date', 'last_updated'
    ])

# Ensure numeric ID column doesn't break if it contains NaN values
if not df.empty:
    df['id'] = pd.to_numeric(df['id'], errors='coerce')

# 3. Sidebar Setup: Adding New Leads
st.sidebar.header("➕ Add New Prospect/Lead")
with st.sidebar.form("lead_form", clear_on_submit=True):
    name = st.text_input("Lead / Contact Name *")
    company = st.text_input("Company Name")
    email = st.text_input("Email Address")
    status = st.selectbox(
        "Pipeline Stage", 
        ["New Prospect", "Contacted", "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"]
    )
    
    st.subheader("📄 Prospectus Information")
    prospectus = st.text_area("Deal Value, Key Requirements, or Account Pain Points")
    
    st.subheader("📅 Follow-up Action")
    followup = st.date_input("Set Next Reminder Date", value=date.today())
    
    submit_button = st.form_submit_button("Save Lead to Cloud")
    
    if submit_button:
        if name:
            # Generate automated incremental ID
            if df.empty or df['id'].isnull().all():
                new_id = 1
            else:
                new_id = int(df['id'].max() + 1)
                
            # Create a new row DataFrame matching the sheet schema
            new_row = pd.DataFrame([{
                "id": new_id,
                "name": name,
                "company": company,
                "email": email,
                "status": status,
                "prospectus_notes": prospectus,
                "followup_date": str(followup),
                "last_updated": str(date.today())
            }])
            
            # Append rows and update the Google Sheet live
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.sidebar.success(f"🎉 Successfully recorded: '{name}'")
            st.rerun()
        else:
            st.sidebar.error("⚠️ Lead Name is a required field.")

# 4. Smart Follow-up Reminder Alerts Dashboard
st.subheader("🚨 Priority Follow-up Notifications")
if not df.empty:
    today_str = str(date.today())
    
    # Filter for active items due today or overdue
    reminders = df[
        (df['followup_date'] <= today_str) & 
        (~df['status'].isin(["Closed Won", "Closed Lost"]))
    ]
    
    if not reminders.empty:
        for idx, row in reminders.iterrows():
            st.error(
                f"⏰ **Follow-up Due:** Contact **{row['name']}** ({row['company'] or 'No Company'}). "
                f"Scheduled Date: `{row['followup_date']}` | Current Stage: *{row['status']}*"
            )
    else:
        st.success("✅ Clear schedule! No outstanding lead follow-ups due today.")
else:
    st.info("💡 Your CRM pipeline is currently empty. Use the sidebar menu to add your first lead.")

st.markdown("---")

# 5. Core Pipeline Analytics & Interactive Grid Viewer
st.subheader("📊 Your Active Pipeline")
if not df.empty:
    # Top-Level Pipeline Metrics
    total_deals = len(df)
    active_deals = len(df[~df['status'].isin(["Closed Won", "Closed Lost"])])
    won_deals = len(df[df['status'] == "Closed Won"])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Logged Prospects", total_deals)
    col2.metric("Active Pipeline Deals", active_deals)
    col3.metric("Closed Won Deals", won_deals)
    
    # Interactive Data Table Presentation
    st.dataframe(
        df[['id', 'name', 'company', 'email', 'status', 'followup_date', 'last_updated']], 
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # 6. Deep-Dive Profile Inspection & In-Line Status Editing
    st.markdown("### 🔍 Drill Down Prospectus Details & Status Editor")
    
    # Dropdown selector to choose which specific lead file to examine
    selected_lead_name = st.selectbox("Select a Prospect profile to view or edit:", df['name'].unique())
    
    if selected_lead_name:
        # Isolate the data corresponding to the selected individual
        lead_idx = df[df['name'] == selected_lead_name].index[0]
        lead_details = df.loc[lead_idx]
        
        detail_col1, detail_col2 = st.columns([2, 1])
        
        with detail_col1:
            st.markdown(f"#### 📄 Prospectus File for **{lead_details['name']}**")
            st.markdown(f"**Company Profile:** {lead_details['company'] or '*Not specified*'}")
            st.markdown(f"**Contact Info:** {lead_details['email'] or '*Not specified*'}")
            
            # Display text box for note records
            notes_display = lead_details['prospectus_notes'] if pd.notnull(lead_details['prospectus_notes']) and lead_details['prospectus_notes'] != "" else "*No prospectus or notes logged for this deal yet.*"
            st.info(notes_display)
            st.caption(f"Profile records last updated on: {lead_details['last_updated']}")
            
        with detail_col2:
            st.markdown("#### ⚡ Quick Pipeline Status Update")
            
            # Fetch current index value to match the default selector options smoothly
            pipeline_options = ["New Prospect", "Contacted", "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"]
            current_status_idx = pipeline_options.index(lead_details['status']) if lead_details['status'] in pipeline_options else 0
            
            new_stage = st.selectbox("Transition Stage to:", pipeline_options, index=current_status_idx)
            
            # Parse saved date correctly so data inputs don't crash the widget layout
            try:
                current_followup_date = datetime.strptime(str(lead_details['followup_date']), "%Y-%m-%d").date()
            except ValueError:
                current_followup_date = date.today()
                
            new_date = st.date_input("Reschedule Next Follow-up:", value=current_followup_date)
            
            if st.button("Commit Status & Follow-up"):
                # Apply changes locally into the data frame mapping
                df.at[lead_idx, 'status'] = new_stage
                df.at[lead_idx, 'followup_date'] = str(new_date)
                df.at[lead_idx, 'last_updated'] = str(date.today())
                
                # Push the revised data frame straight up to your Google Sheet database
                conn.update(data=df)
                st.toast(f"🔒 CRM cloud profile updated for {selected_lead_name}!")
                st.rerun()
