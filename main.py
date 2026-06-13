import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Cloud CRM", layout="wide")
st.title("💼 Cloud CRM — Lead Tracker")

# 1. Connect to Google Sheets (Our Cloud Database)
# The connection automatically reads a sheet URL provided in your secrets configuration
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl="0") # ttl="0" ensures data is fresh on every refresh
except Exception:
    # Fallback template if sheet is empty or newly setup
    df = pd.DataFrame(columns=['id', 'name', 'company', 'email', 'status', 'prospectus_notes', 'followup_date', 'last_updated'])

# 2. Sidebar Form to Add Leads
st.sidebar.header("➕ Add New Prospect/Lead")
with st.sidebar.form("lead_form", clear_on_submit=True):
    name = st.text_input("Lead / Contact Name *")
    company = st.text_input("Company Name")
    email = st.text_input("Email Address")
    status = st.selectbox("Pipeline Stage", ["New Prospect", "Contacted", "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"])
    prospectus = st.text_area("Prospectus Details (Deal Value, Needs)")
    followup = st.date_input("Set Next Reminder Date", value=date.today())
    
    submit_button = st.form_submit_button("Save Lead")
    
    if submit_button and name:
        new_id = int(df['id'].max() + 1) if not df.empty and df['id'].max() == df['id'].max() else 1
        new_row = pd.DataFrame([{
            "id": new_id, "name": name, "company": company, "email": email,
            "status": status, "prospectus_notes": prospectus, 
            "followup_date": str(followup), "last_updated": str(date.today())
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=df)
        st.sidebar.success(f"Recorded: {name}")
        st.sidebar.button("Refresh Board")

# 3. Smart Reminders Alert System
st.subheader("🚨 Priority Follow-up Notifications")
if not df.empty:
    today_str = str(date.today())
    reminders = df[(df['followup_date'] <= today_str) & (~df['status'].isin(["Closed Won", "Closed Lost"]))]
    
    if not reminders.empty:
        for _, row in reminders.iterrows():
            st.error(f"⏰ **Follow-up Due:** {row['name']} ({row['company']}) | Schedule: {row['followup_date']}")
    else:
        st.success("✅ No outstanding follow-ups for today!")

st.markdown("---")

# 4. Pipeline Table Dashboard
st.subheader("📊 Your Active Pipeline")
if not df.empty:
    st.dataframe(df[['id', 'name', 'company', 'email', 'status', 'followup_date']], use_container_width=True, hide_index=True)
    
    # Quick Status Editor
    st.markdown("### 🔍 Quick Profile Update")
    selected_lead = st.selectbox("Select a Prospect to modify:", df['name'].unique())
    if selected_lead:
        lead_idx = df[df['name'] == selected_lead].index[0]
        row_details = df.loc[lead_idx]
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Prospectus:** {row_details['prospectus_notes']}")
        with col2:
            new_stage = st.selectbox("Move Stage:", ["New Prospect", "Contacted", "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"], index=["New Prospect", "Contacted", "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"].index(row_details['status']))
            new_date = st.date_input("New Follow-up:", value=datetime.strptime(row_details['followup_date'], "%Y-%m-%d").date())
            
            if st.button("Commit Changes"):
                df.at[lead_idx, 'status'] = new_stage
                df.at[lead_idx, 'followup_date'] = str(new_date)
                df.at[lead_idx, 'last_updated'] = str(date.today())
                conn.update(data=df)
                st.toast("Updated cloud file!")
                st.rerun()
