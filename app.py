import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Broker XML Tool", layout="centered")
st.title("💎 Jewelry XML Generator for NetCHB")

uploaded_file = st.file_uploader("Upload Jewelry Invoice (CSV)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df_cleaned = df.dropna(subset=['CLASS'])

    # Build XML structure
    root = ET.Element("EntrySummary")
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "Currency").text = "USD"
    
    line_items = ET.SubElement(root, "LineItems")
    for _, row in df_cleaned.iterrows():
        item = ET.SubElement(line_items, "LineItem")
        # Logic to assign 10-digit HTS based on your specific 'CLASS' or 'Description'
        hts = "7113.19.2900" if "MLN" in str(row['Descriptions']) else "7113.19.5085"
        
        ET.SubElement(item, "HTSCode").text = hts
        ET.SubElement(item, "Description").text = str(row['Descriptions'])
        ET.SubElement(item, "Quantity").text = str(row["Q'ty"])
        ET.SubElement(item, "Value").text = str(row['amount (U.S.$)'])

    # Format XML
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
    
    st.download_button(
        label="📥 Download XML for NetCHB",
        data=xml_str,
        file_name="netchb_import.xml",
        mime="text/xml"
    )