import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io

# 1. Setup & Security
st.set_page_config(page_title="Customs XML Generator", page_icon="⚖️")
st.title("⚖️ Broker XML Tool: Gemini 2.0 Flash Edition")

# Retrieve API key securely from Streamlit Secrets
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Please add your GOOGLE_API_KEY to Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# 2. File Upload Widget
uploaded_file = st.file_uploader("Upload Jewelry Invoice", type=["pdf", "csv", "xlsx"])

def generate_xml(line_items):
    """Converts extracted line items into the NetCHB XML structure."""
    root = ET.Element("EntrySummary")
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "Currency").text = "USD"
    
    items_node = ET.SubElement(root, "LineItems")
    for li in line_items:
        item = ET.SubElement(items_node, "LineItem")
        # Example HTS logic based on keywords
        desc = li.get('Description', '').upper()
        hts = "7113.19.2900" if "MLN" in desc else "7113.19.5085"
        
        ET.SubElement(item, "HTSCode").text = hts
        ET.SubElement(item, "Description").text = li.get('Description', 'N/A')
        ET.SubElement(item, "Quantity").text = str(li.get('Quantity', 0))
        ET.SubElement(item, "Value").text = str(li.get('Total_Value', 0))
    
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
    return xml_str

if uploaded_file:
    line_data = []

    # CASE A: Processing PDF using Gemini 2.0 Flash
    if uploaded_file.type == "application/pdf":
        st.info("AI is analyzing PDF structure...")
        # Uploading file to Google's temporary Files API for high-latency reliability
        file_bytes = uploaded_file.read()
        
        prompt = """
        Extract all line items from this jewelry invoice. 
        Return ONLY a JSON list of objects with these keys: 
        'Description', 'Quantity', 'Total_Value'.
        Do not include any other text.
        """
        
        # Using Gemini 2.0 Flash for structured output
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                prompt
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        # Parse the AI's structured response
        import json
        line_data = json.loads(response.text)

    # CASE B: Processing CSV/Excel
    else:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.write("Preview of data:", df.head())
        # Mapping your specific columns from the provided jewelry file
        for _, row in df.dropna(subset=['CLASS']).iterrows():
            line_data.append({
                'Description': str(row.get('Descriptions', 'N/A')),
                'Quantity': row.get("Q'ty", 0),
                'Total_Value': row.get('amount (U.S.$)', 0)
            })

    # 3. Generate and Download XML
    if line_data:
        final_xml = generate_xml(line_data)
        st.download_button(
            label="📥 Download NetCHB XML",
            data=final_xml,
            file_name="broker_import.xml",
            mime="text/xml"
        )
        st.success(f"Processed {len(line_data)} items successfully.")
