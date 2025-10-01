"""Streamlit app for Excel Agent."""

import streamlit as st
import pandas as pd
from pathlib import Path
from excel_agent.config import DATA_DIR, OUTPUT_DIR, OPENAI_API_KEY
from excel_agent.graph import process_excel_file


def main():
    st.set_page_config(
        page_title="Excel Agent",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Excel Agent")
    st.markdown("""
    Extract data from multiple Excel files with varying structures.
    
    This tool uses AI to automatically identify and extract:
    - **Номер заявки** (Order/Application Number)
    - **Итоговая Стоимость Заявки** (Total Cost)
    """)
    
    # Check API key
    if not OPENAI_API_KEY:
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        st.info(f"Data directory: `{DATA_DIR}`")
        st.info(f"Output directory: `{OUTPUT_DIR}`")
        
        if st.button("🔄 Refresh Files"):
            st.rerun()
    
    # Main content
    tab1, tab2 = st.tabs(["📁 Process Files", "📤 Upload Files"])
    
    with tab1:
        st.header("Process Excel Files")
        
        # Get list of Excel files in data directory
        excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
        
        if not excel_files:
            st.warning(f"No Excel files found in `{DATA_DIR}`. Please add files to the data folder or upload them in the 'Upload Files' tab.")
        else:
            st.success(f"Found {len(excel_files)} Excel file(s)")
            
            # Display files
            with st.expander("📋 Files to process"):
                for f in excel_files:
                    st.text(f"• {f.name}")
            
            if st.button("🚀 Process All Files", type="primary"):
                process_files(excel_files)
    
    with tab2:
        st.header("Upload Excel Files")
        
        uploaded_files = st.file_uploader(
            "Choose Excel files",
            type=["xlsx", "xls"],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.info(f"Selected {len(uploaded_files)} file(s)")
            
            if st.button("💾 Save to Data Folder"):
                for uploaded_file in uploaded_files:
                    file_path = DATA_DIR / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                st.success("Files saved! Go to 'Process Files' tab to process them.")
                st.rerun()


def process_files(excel_files):
    """Process all Excel files and combine results."""
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file_path in enumerate(excel_files):
        status_text.text(f"Processing: {file_path.name}")
        
        with st.expander(f"📄 {file_path.name}", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.text(f"File: {file_path.name}")
            
            with col2:
                status = st.empty()
                status.info("🔄 Processing...")
            
            try:
                # Process the file
                result = process_excel_file(file_path)
                
                if result.get("error"):
                    status.error("❌ Error")
                    st.error(f"Error: {result['error']}")
                elif result.get("extracted_data") is not None:
                    df = result["extracted_data"]
                    status.success("✅ Success")
                    
                    # Display mapping info
                    mapping = result.get("column_mapping", {})
                    st.info(f"""
                    **Sheet:** {mapping.get('sheet_name', 'N/A')}  
                    **Order Column:** {mapping.get('order_column', 'N/A')}  
                    **Cost Column:** {mapping.get('cost_column', 'N/A')}  
                    **Confidence:** {mapping.get('confidence', 'N/A')}
                    """)
                    
                    # Display data preview
                    st.dataframe(df.head(10), use_container_width=True)
                    st.caption(f"Total rows: {len(df)}")
                    
                    all_results.append(df)
                else:
                    status.warning("⚠️ No data")
                    st.warning("No data extracted")
                    
            except Exception as e:
                status.error("❌ Error")
                st.error(f"Unexpected error: {str(e)}")
        
        progress_bar.progress((i + 1) / len(excel_files))
    
    status_text.text("Processing complete!")
    
    # Combine all results
    if all_results:
        st.header("📊 Combined Results")
        
        combined_df = pd.concat(all_results, ignore_index=True)
        st.dataframe(combined_df, use_container_width=True)
        st.success(f"Total rows extracted: {len(combined_df)}")
        
        # Save to CSV
        output_path = OUTPUT_DIR / "combined_results.csv"
        combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        st.success(f"💾 Results saved to: `{output_path}`")
        
        # Download button
        csv = combined_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name="combined_results.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data was extracted from any files.")


if __name__ == "__main__":
    main()

