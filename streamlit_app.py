import streamlit as st
import pandas as pd
import sys
import os
from io import BytesIO
import tempfile

# Tilføj stien til vores generate_dashboard script
sys.path.insert(0, os.path.dirname(__file__))

# Import alle funktioner fra generate_dashboard
from generate_dashboard import (
    process_leje_data, 
    process_ejer_data, 
    generate_html
)

# Page config
st.set_page_config(
    page_title="Underwriting Dashboard Generator",
    page_icon="🏠",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #3498db;
        color: white;
        font-weight: bold;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2980b9;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🏠 Bolig Dashboard Generator")
st.markdown("---")

# Sidebar with instructions
with st.sidebar:
    st.header("📖 Vejledning")
    st.markdown("""
    ### 📋 Trin 1: Upload Filer
    Upload dine to Excel-filer:
    - **Lejedata** - Udlejningsboliger
    - **Ejerdata** - Salgsboliger
    
    ### ⚙️ Trin 2: Generér
    Klik på "Generér Dashboard" knappen
    
    ### 💾 Trin 3: Download
    Download din færdige HTML-fil
    
    ### 🎯 Trin 4: Åbn
    Åbn HTML-filen i din browser
    
    ---
    
    ### 📊 Excel Krav
    
    **Lejedata skal have:**
    - Adresse, By, Lat, Lng
    - Areal, Leje/m2, Årsleje
    - Liggedage, Antal værelser
    
    **Ejerdata skal have:**
    - Fane: Stamdata
    - Fane: Enheder
    - (Valgfri: Ejendomme)
    
    [Se fuld dokumentation](https://github.com/...)
    """)
    
    st.markdown("---")
    st.markdown("**Version:** 2.0")
    

# Main content
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📊 Lejedata")
    leje_file = st.file_uploader(
        "Upload lejedata Excel-fil",
        type=['xlsx', 'xls'],
        help="Excel-fil med udlejningsboliger (skal indeholde: Adresse, By, Lat, Lng, Areal, Leje/m2, Årsleje, Liggedage, Antal værelser)"
    )
    
    if leje_file:
        st.markdown('<div class="success-box">✅ Lejedata uploadet!</div>', unsafe_allow_html=True)
        
        # Preview
        with st.expander("👁️ Se data preview"):
            try:
                df_preview = pd.read_excel(leje_file, nrows=5)
                st.dataframe(df_preview)
                st.caption(f"Total rækker: {len(pd.read_excel(leje_file))}")
            except Exception as e:
                st.error(f"Kunne ikke læse fil: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("🏠 Ejerdata")
    ejer_file = st.file_uploader(
        "Upload ejerdata Excel-fil",
        type=['xlsx', 'xls'],
        help="Excel-fil med salgsboliger (skal have faner: Stamdata, Enheder)"
    )
    
    if ejer_file:
        st.markdown('<div class="success-box">✅ Ejerdata uploadet!</div>', unsafe_allow_html=True)
        
        # Preview
        with st.expander("👁️ Se data preview"):
            try:
                excel_file = pd.ExcelFile(ejer_file)
                st.write(f"📑 Faner: {', '.join(excel_file.sheet_names)}")
                df_preview = pd.read_excel(ejer_file, sheet_name=0, nrows=5)
                st.dataframe(df_preview)
                st.caption(f"Total rækker: {len(pd.read_excel(ejer_file, sheet_name=0))}")
            except Exception as e:
                st.error(f"Kunne ikke læse fil: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Generate button
if leje_file and ejer_file:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 GENERÉR DASHBOARD", type="primary"):
            with st.spinner("⏳ Genererer dashboard... Dette tager 10-30 sekunder..."):
                try:
                    # Save uploaded files to temporary files
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_leje:
                        tmp_leje.write(leje_file.getvalue())
                        leje_path = tmp_leje.name
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_ejer:
                        tmp_ejer.write(ejer_file.getvalue())
                        ejer_path = tmp_ejer.name
                    
                    # Process data
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("📊 Læser lejedata...")
                    progress_bar.progress(20)
                    leje_data = process_leje_data(leje_path)
                    
                    status_text.text("🏠 Læser ejerdata...")
                    progress_bar.progress(50)
                    ejer_data = process_ejer_data(ejer_path)
                    
                    status_text.text("🎨 Genererer dashboard...")
                    progress_bar.progress(80)
                    
                    # Generate HTML
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_html:
                        output_path = tmp_html.name
                    
                    generate_html(leje_data, ejer_data, output_path)
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Dashboard genereret!")
                    
                    # Read generated HTML
                    with open(output_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Clean up temp files
                    os.unlink(leje_path)
                    os.unlink(ejer_path)
                    
                    # Success message
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.markdown("### 🎉 Dashboard Genereret!")
                    st.markdown(f"""
                    - **📊 Lejeboliger:** {leje_data['total_boliger']}
                    - **🏠 Ejerboliger:** {ejer_data['total_boliger']}
                    - **📈 Grafer:** Scatter plot, Heatmap, Summary tabel
                    - **🎛️ Filtre:** Værelser, By, Type, Opførelsesår
                    """)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Download button
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            label="💾 DOWNLOAD DASHBOARD",
                            data=html_content,
                            file_name="bolig_dashboard.html",
                            mime="text/html",
                            help="Download HTML-filen og åbn den i din browser"
                        )
                    
                    # Preview in iframe
                    st.markdown("---")
                    st.subheader("👁️ Preview")
                    st.markdown('<div class="info-box">ℹ️ Preview viser kun en del af dashboardet. Download filen for fuld funktionalitet.</div>', unsafe_allow_html=True)
                    
                    # Show in iframe (limited functionality)
                    st.components.v1.html(html_content, height=800, scrolling=True)
                    
                    # Clean up HTML temp file
                    os.unlink(output_path)
                    
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ <b>Fejl:</b> {str(e)}</div>', unsafe_allow_html=True)
                    st.error("Se detaljer ovenfor. Tjek at dine Excel-filer har de korrekte kolonner.")
                    
                    # Show error details in expander
                    with st.expander("🔍 Se tekniske detaljer"):
                        st.exception(e)

else:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### ℹ️ Upload begge filer for at komme i gang")
    st.markdown("Upload både lejedata og ejerdata Excel-filerne ovenfor.")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #7f8c8d; padding: 2rem;'>
        <p><b>Bolig Dashboard Generator v2.0</b></p>
        <p>Udviklet med Streamlit og python</p>
        <p style='font-size: 0.8rem;'>📧 Spørgsmål? Kontakt IT support</p>
    </div>
""", unsafe_allow_html=True)
