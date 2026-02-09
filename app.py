import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import xml.etree.ElementTree as ET
from xml.dom import minidom
import hmac
import json

# --- 1. CONFIGURATION & AUTHENTICATION ---
st.set_page_config(page_title="Customs XML Generator", page_icon="⚖️")

def logout():
    """Clears the session state and logs the user out."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def check_password():
    """Returns True if the user has the correct password."""
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["APP_PASSWORD"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Broker Portal Login")
    st.text_input("Enter Broker Password", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect")
    return False

# --- 2. MAIN APPLICATION LOGIC ---
if check_password():
    # Sidebar with Logout
    with st.sidebar:
        st.header("Broker Menu")
        st.button("🔓 Logout", on_click=logout)

    st.title("⚖️ Broker XML Tool: Gemini 2.0 Flash")
    
    # API Setup
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("Please add your GOOGLE_API_KEY to Streamlit Secrets.")
        st.stop()
    
    client = genai.Client(api_key=api_key)

    # File Uploader
    uploaded_file = st.file_uploader("Upload Jewelry Invoice (PDF, CSV, or XLSX)", type=["pdf", "csv", "xlsx"])

    def generate_xml(line_items):
        """Converts extracted data into NetCHB XML format."""
        root = ET.Element("EntrySummary")
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "Currency").text = "USD"
        
        items_node = ET.SubElement(root, "LineItems")
        for li in line_items:
            item = ET.SubElement(items_node, "LineItem")
            desc = str(li.get('Description', 'N/A')).upper()
            # Logic for HTS 10-digit codes
            hts = "7113.19.2900" if "MLN" in desc else "7113.19.5085"
            
            ET.SubElement(item, "HTSCode").text = hts
            ET.SubElement(item, "Description").text = desc
            ET.SubElement(item, "Quantity").text = str(li.get('Quantity', 0))
            ET.SubElement(item, "Value").text = str(li.get('Total_Value', 0))
        
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
        return xml_str

    if uploaded_file:
        line_data = []

        # Handle PDF with AI
        if uploaded_file.type == "application/pdf":
            st.info("AI is analyzing PDF content...")
            file_bytes = uploaded_file.read()
            
            prompt = "Extract all line items. Return ONLY a JSON list of objects: 'Description', 'Quantity', 'Total_Value'."
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                    prompt
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            line_data = json.loads(response.text)

        # Handle CSV/Excel
        else:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("Preview of data:", df.head())
            for _, row in df.dropna(subset=['CLASS']).iterrows():
                line_data.append({
                    'Description': str(row.get('Descriptions', 'N/A')),
                    'Quantity': row.get("Q'ty", 0),
                    'Total_Value': row.get('amount (U.S.$)', 0)
                })

        # Generate Download Button
        if line_data:
            final_xml = generate_xml(line_data)
            st.download_button(
                label="📥 Download NetCHB XML",
                data=final_xml,
                file_name="broker_import.xml",
                mime="text/xml"
            )
            st.success(f"Processed {len(line_data)} items successfully.")
