import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- CONFIGURATION ---
ADMIN_PASSWORD = "ptes_admin_123"
# Link to your Google Sheet (replace with yours)
# SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit?usp=sharing"
# Replace the old placeholder with your actual link
SHEET_URL = "https://docs.google.com/spreadsheets/d/1F54XWB0QE3BXwVyz_RTJtexd9tyWuVpSJ7D8geOqadw/edit?usp=sharing"

st.set_page_config(page_title="PTES Smart Classroom", layout="wide")
st.title("🏫 PTES Smart Classroom LOG Booking")


# Connect to Google Sheets
#conn = st.connection("gsheets", type=GSheetsConnection)
# The app now automatically connects using the secrets file

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # No need to pass the URL here anymore!
    return conn.read(ttl=0)

# Function to load data from Google Sheets
# Change this part:
#def load_data():
    # We use ttl=0 to ensure we always get the latest bookings from the sheet
#    return conn.read(spreadsheet=SHEET_URL, ttl=0)

df_bookings = load_data()

# Admin Sidebar
st.sidebar.header("Admin Controls")
admin_key = st.sidebar.text_input("Enter Admin Password", type="password")

tab1, tab2 = st.tabs(["📝 Make a Booking", "📅 View Schedule (Refresh)"])

with tab1:
    st.info(
        "💡 **Reminder:** A booking cannot be cancelled once it is confirmed. If you need to do so, please contact the Admin.")

    with st.form("booking_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Lecturer Full Name")
            dept = st.selectbox("Department", ["Others", "Physics", "Biology", "Chemistry", "Maths", "English/G.P/Malay", "History", "Geography",  "Computing", "Pychology/Sociology","Food Science", "Media Studies / ART / D&T", "Business / Accounting / Economics"])
        with col2:
            booking_date = st.date_input("Date of Booking", min_value=date.today())
            slots = ["08:00 - 09:45", "10:15 - 12:15", "13:15 - 15:15"]
            time_slot = st.selectbox("Available Time Slots", slots)

        facilities = st.multiselect("Facilities Needed",
                                    ["Smartboard", "Chromebooks", "Visualizer", "Recording Terminal",
                                     "Internet Access", "Others"])
        submitted = st.form_submit_button("CONFIRM BOOKING")

        if submitted:
            if booking_date.strftime('%A') in ['Friday', 'Sunday']:
                st.error("🚫 No bookings allowed on Fridays or Sundays.")
            else:
                # --- UPDATED CLASH CHECK ---
                # 1. Convert the new booking date to our chosen string format
                new_date_str = booking_date.strftime('%d/%m/%Y')

                # 2. Check the sheet data.
                # We make sure the 'Date' column is treated as a string for comparison
                clash = df_bookings[
                    (df_bookings['Date'].astype(str) == new_date_str) &
                    (df_bookings['Time_Slot'] == time_slot)
                    ]

                if not clash.empty:
                    st.warning(
                        f"⚠️ CLASH: This slot is already taken by {clash.iloc[0]['Name']} ({clash.iloc[0]['Department']}).")
                # ---------------------------
                elif name.strip() == "":
                    st.error("Please enter your name.")
                else:
                    # Create the new row
                    new_row = pd.DataFrame([{
                        "Name": name,
                        "Department": dept,
                        "Date": new_date_str,
                        "Time_Slot": time_slot,
                        "Facilities": ", ".join(facilities)
                    }])
                    # Update Google Sheets
                    updated_df = pd.concat([df_bookings, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, data=updated_df)
                    st.success("✅ Booking confirmed in Google Sheets!")
                    st.balloons()

with tab2:
    st.header("Upcoming Bookings")
    if not df_bookings.empty:
        # 1. Convert the 'Date' strings from the sheet into Python dates
        # dayfirst=True ensures 12/02 is read as 12th Feb
        df_bookings['Date_Obj'] = pd.to_datetime(
            df_bookings['Date'],
            dayfirst=True,
            errors='coerce'
        ).dt.date

        # 2. Filter out old bookings and sort by date/time
        upcoming = df_bookings.dropna(subset=['Date_Obj'])
        upcoming = upcoming[upcoming['Date_Obj'] >= date.today()].sort_values(by=['Date_Obj', 'Time_Slot'])

        # 3. Show the table but hide our "helper" Date_Obj column
        st.dataframe(upcoming.drop(columns=['Date_Obj']), use_container_width=True)
    else:
        st.info("No bookings found yet.")

    # Keep your Admin Delete section below this...
    if admin_key == ADMIN_PASSWORD:
        st.divider()
        st.subheader("🗑️ Admin: Delete a Booking")
        row_idx = st.number_input("Index to Delete", min_value=0, max_value=len(df_bookings) - 1, step=1)
        if st.button("DELETE BOOKING"):
            df_updated = df_bookings.drop(df_bookings.index[row_idx]).drop(columns=['Date_Obj'])
            conn.update(spreadsheet=SHEET_URL, data=df_updated)
            st.success("Removed!")

            st.rerun()

