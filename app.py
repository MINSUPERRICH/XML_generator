import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import xml.etree.ElementTree as ET
from xml.dom import minidom
import hmac

# --- AUTHENTICATION SYSTEM ---
def check_password():
    """Returns True if the user has the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["APP_PASSWORD"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    st.title("🔒 Broker Portal Login")
    st.text_input("Enter Broker Password", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

# Only run the app if password is correct
if check_password():
    # --- MAIN APP START ---
    st.set_page_config(page_title="Customs XML Generator", page_icon="⚖️")
    st.title("⚖️ Broker XML Tool: Gemini 2.0 Flash Edition")

    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("Please add your GOOGLE_API_KEY to Streamlit Secrets.")
        st.stop()

    client = genai.Client(api_key=api_key)

    # File Upload Widget
    uploaded_file = st.file_uploader("Upload Jewelry Invoice", type=["pdf", "csv", "xlsx"])

    def generate_xml(line_items):
        root = ET.Element("EntrySummary")
        items_node = ET.SubElement(root, "LineItems")
        for li in line_items:
            item = ET.SubElement(items_node, "LineItem")
            desc = li.get('Description', '').upper()
            hts = "7113.19.2900" if "MLN" in desc else "7113.19.5085"
            ET.SubElement(item, "HTSCode").text = hts
            ET.SubElement(item, "Description").text = li.get('Description', 'N/A')
            ET.SubElement(item, "Quantity").text = str(li.get('Quantity', 0))
            ET.SubElement(item, "Value").text = str(li.get('Total_Value', 0))
        return minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")

    if uploaded_file:
        line_data = []
        if uploaded_file.type == "application/pdf":
            st.info("AI is analyzing PDF...")
            file_bytes = uploaded_file.read()
            prompt = "Extract all line items as JSON: 'Description', 'Quantity', 'Total_Value'."
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            import json
            line_data = json.loads(response.text)
        else:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            for _, row in df.dropna(subset=['CLASS']).iterrows():
                line_data.append({
                    'Description': str(row.get('Descriptions', 'N/A')),
                    'Quantity': row.get("Q'ty", 0),
                    'Total_Value': row.get('amount (U.S.$)', 0)
                })

        if line_data:
            final_xml = generate_xml(line_data)
            st.download_button("📥 Download NetCHB XML", final_xml, "broker_import.xml", "text/xml")
            st.success(f"Processed {len(line_data)} items.")
