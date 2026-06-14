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
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Read live values directly from your connected Google Sheet secrets link
    df = conn.read(ttl="0")
except Exception:
    # Blank template generation fallback
    df = pd.DataFrame(columns=[
        'id', 'name', 'company', 'email', 'status', 
        'prospectus_notes', 'followup_date', 'last_updated'
    ])

# Ensure table schema integrity
if not df.empty:
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
else:
    df = pd.DataFrame(columns=['id', 'name', 'company', 'email', 'status', 'prospectus_notes', 'followup_date', 'last_updated'])

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
            # Generate ID
            if df.empty or df['id'].isnull().all():
                new_id = 1
            else:
                new_id = int(df['id'].max() + 1)
                
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
            
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.sidebar.success(f"🎉 Successfully recorded: '{name}'")
            st.hierarchy_update = True
            st.rerun()
        else:
            st.sidebar.error("⚠️ Lead Name is a required field.")

# 4. Follow-up Reminder Alerts Dashboard
st.subheader("🚨 Priority Follow-up Notifications")
if not df.empty and 'followup_date' in df.columns:
    today_str = str(date.today())
    # Identify items requiring follow-up action today or overdue
    reminders = df[
        (df['followup_date'].astype(str) <= today_str) & 
        (~df['status'].isin(["Closed Won", "Closed Lost"]))
    ]
    
    if not reminders.empty:
        for idx, row in reminders.iterrows():
            st.error(
                f"⏰ **Follow-up Due:** Contact **{row['name']}** ({row['company'] if pd.notnull(row['company']) else 'No Company'}). "
                f"Target: `{row['followup_date']}` | Status: *{row['status']}*"
            )
    else:
        st.success("✅ Clean schedule! No outstanding lead follow-ups due today.")
else:
    st.info("💡 Your CRM pipeline is currently empty. Use the sidebar menu to add your first lead.")

st.markdown("---")

# 5. Core Pipeline Table presentation
st.subheader("📊 Your Active Pipeline")
if not df.empty and len(df) > 0:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Logged Prospects", len(df))
    col2.metric("Active Deals", len(df[~df['status'].isin(["Closed Won", "Closed Lost"])]))
    col3.metric("Closed Won", len(df[df['status'] == "Closed Won"]))
    
    st.dataframe(
        df[['id', 'name', 'company', 'email', 'status', 'followup_date']], 
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # 6. Deep-Dive Profile Inspection & Status Adjustments
    st.markdown("### 🔍 Drill Down Prospectus Details & Status Editor")
    selected_lead_name = st.selectbox("Select a Prospect profile to view or edit:", df['name'].unique())
    
    if selected_lead_name:
        lead_idx = df[df['name'] == selected_lead_name].index[0]
        lead_details = df.loc[lead_idx]
        
        detail_col1, detail_col2 = st.columns([2, 1])
        
        with detail_col1:
            st.markdown(f"#### 📄 Prospectus File for **{lead_details['name']}**")
            st.markdown(f"**Company Profile:** {lead_details['company'] or '*Not specified*'}")
            st.markdown(f"**Contact Info:** {lead_details['email'] or '*Not specified*'}")
            
            notes_display = lead_details['prospectus_notes'] if pd.notnull(lead_details['prospectus_notes']) and lead_details['prospectus_notes'] != "" else "*No prospectus details logged.*"
            st.info(notes_display)
            
        with detail_col2:
            st.markdown("#### ⚡ Quick Pipeline Status Update")
            pipeline_options = ["New Prospect", "Contacted", "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"]
            current_status_idx = pipeline_options.index(lead_details['status']) if lead_details['status'] in pipeline_options else 0
            
            new_stage = st.selectbox("Transition Stage to:", pipeline_options, index=current_status_idx)
            
            try:
                current_followup_date = datetime.strptime(str(lead_details['followup_date']), "%Y-%m-%d").date()
            except Exception:
                current_followup_date = date.today()
                
            new_date = st.date_input("Reschedule Next Follow-up:", value=current_followup_date)
            
            if st.button("Commit Status & Follow-up"):
                df.at[lead_idx, 'status'] = new_stage
                df.at[lead_idx, 'followup_date'] = str(new_date)
                df.at[lead_idx, 'last_updated'] = str(date.today())
                
                conn.update(data=df)
                st.toast(f"🔒 CRM profile updated for {selected_lead_name}!")
                st.rerun()
