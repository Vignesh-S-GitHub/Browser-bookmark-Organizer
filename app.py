import streamlit as st
import os
import time
from bookmark_manager import get_browser_path, consolidate_bookmarks
from ai_classifier import categorize_bookmarks, verify_gemini_connection
from utils import generate_netscape_html

# Page Config
st.set_page_config(
    page_title="AI Bookmark Organizer",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Aesthetic
st.markdown("""
<style>
    /* Global Theme */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: black;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(255, 215, 0, 0.4);
    }
    
    /* Headers */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #FFD700 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #00ffca;
        font-family: 'Courier New', monospace;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #00ffca, #00bfff);
    }
</style>
""", unsafe_allow_html=True)

# Application Logic
def main():
    """
    Main entry point for the Streamlit application.
    Handles UI rendering, state management, and user interactions.
    """
    
    # --- Custom CSS for Aesthetic ---
    # We use the Outfit font and a dark/neon theme to give it a modern, tech-focused aesthetic.
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
        
        html, body, [class*="css"]  {
            font-family: 'Outfit', sans-serif;
        }
        
        /* Hero Section */
        .hero-title {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        
        @media (max-width: 600px) {
            .hero-title {
                font-size: 2rem;
            }
        }
        
        .hero-subtitle {
            text-align: center;
            color: #b0b0b0;
            margin-bottom: 2rem;
            font-size: 1.2rem;
        }
        
        /* Cards & Metrics - Make them responsive */
        div[data-testid="metric-container"] {
            background-color: #1a1f2e;
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid #30363d;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            width: 100%;
        }
        
        /* DataFrame */
        [data-testid="stDataFrame"] {
            border: 1px solid #30363d;
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # --- Hero Section ---
    st.markdown('<p class="hero-title">AI Browser Organizer</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Effortlessly organize your bookmarks using Google\'s Gemini AI.</p>', unsafe_allow_html=True)
    
    # --- Sidebar Config ---
    with st.sidebar:
        st.header("⚙️ Settings")
        
        api_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            help="Required to access Google's AI. Get your free key from [Google AI Studio](https://aistudio.google.com/)."
        )
        
        if not api_key:
            st.warning("⚠️ API Key required!")
            
        st.markdown("---")
        st.subheader("🤖 Model Control")
        
        model_name = st.text_input(
            "Model Name", 
            value="gemini-2.5-flash",
            help="Specify the Gemini model version. 'gemini-2.5-flash' is fast and cost-effective. 'gemini-2.5-pro' provides higher accuracy."
        )
        
        col_limit, col_batch = st.columns(2)
        with col_limit:
            limit_count = st.number_input(
                "Max Bookmarks", 
                min_value=0, 
                value=0, 
                help="Limit the number of bookmarks to process. Useful for testing (e.g., set to 20). Set to 0 to process ALL."
            )
        with col_batch:
            batch_size = st.number_input(
                "Batch Size", 
                min_value=5, 
                value=25, 
                step=5,
                help="How many bookmarks to send to the AI at once. Lower this (e.g., 10-20) if you experience timeouts."
            )
            
    # --- Session State Management ---
    # Initialize state variables if they don't exist
    if "bookmarks" not in st.session_state:
        st.session_state.bookmarks = []
    if "organized_bookmarks" not in st.session_state:
        st.session_state.organized_bookmarks = []
        
    # --- Workflow Tabs ---
    # Using tabs to guide the user through the 3-step process
    tab_scan, tab_organize, tab_export = st.tabs(["1️⃣ Scan & Filter", "2️⃣ AI Organization", "3️⃣ Export"])
    
    # --- TAB 1: Scan ---
    with tab_scan:
        st.markdown("### 🕵️ Detect Bookmarks")
        st.markdown("We'll automatically find bookmarks from specific Chrome, Edge, Brave, and Firefox profiles.")
        
        col_scan_btn, col_scan_stats = st.columns([1, 3])
        
        with col_scan_btn:
            if st.button("🔍 Scan All Browsers", use_container_width=True, help="Click to search default paths for bookmark files."):
                with st.spinner("Hunting for bookmarks..."):
                    # Attempt to locate bookmark files
                    chrome_path = get_browser_path("chrome")
                    edge_path = get_browser_path("edge")
                    brave_path = get_browser_path("brave")
                    firefox_path = get_browser_path("firefox")
                    
                    found_sources = []
                    if chrome_path: found_sources.append("Chrome")
                    if edge_path: found_sources.append("Edge")
                    if brave_path: found_sources.append("Brave")
                    if firefox_path: found_sources.append("Firefox")
                    
                    if found_sources:
                        # Consolidate and deduplicate
                        bookmarks = consolidate_bookmarks(chrome_path, edge_path, brave_path, firefox_path)
                        st.session_state.bookmarks = bookmarks
                        st.toast(f"Success! Found {len(bookmarks)} bookmarks from {', '.join(found_sources)}.", icon="🎉")
                    else:
                        st.error("No bookmarks found. Do you have Chrome, Edge, Brave, or Firefox installed?")
        
        with col_scan_stats:
            if st.session_state.bookmarks:
                st.metric("Total Bookmarks Found", len(st.session_state.bookmarks))
            else:
                st.info("Ready to scan. Click the button to begin.")
                
        if st.session_state.bookmarks:
            st.markdown("#### Preview Data")
            st.dataframe(
                st.session_state.bookmarks,
                column_config={
                    "source": st.column_config.TextColumn("Browser", width="small"),
                    "url": st.column_config.LinkColumn("URL"),
                    "date_added": "Date Added",
                    "title": "Title"
                },
                height=300,
                hide_index=True
            )

    # --- TAB 2: Organize ---
    with tab_organize:
        st.markdown("### 🧠 AI Categorization")
        
        if not st.session_state.bookmarks:
            st.warning("⚠️ Please scan your bookmarks in Tab 1 first.", icon="👈")
        else:
            col_org_opts, col_org_action = st.columns([2, 1])
            
            with col_org_opts:
                total_bms = len(st.session_state.bookmarks)
                # Determine effective limit based on user input
                effective_limit = limit_count if limit_count > 0 else total_bms
                effective_limit = min(effective_limit, total_bms)
                
                st.markdown(f"**Ready to Process:** {effective_limit} bookmarks.")
                if effective_limit < total_bms:
                    st.info(f"⚡ Testing Mode Active: Only processing the first {effective_limit} items.")
            
            with col_org_action:
                start_organize = st.button(
                    "🚀 Start AI Magic", 
                    type="primary", 
                    use_container_width=True, 
                    disabled=not api_key,
                    help="Begin the AI categorization process. This may take a few minutes."
                )
            
            if start_organize:
                
                # Pre-flight check: Verify API Connection
                with st.spinner("🔌 Verifying API Connection..."):
                    try:
                        verify_gemini_connection(api_key, model_name)
                    except Exception as e:
                        st.error(f"❌ Connection Failed: {e}")
                        st.stop() # HALT execution here

                # Slice the data based on limit
                target_bookmarks = st.session_state.bookmarks[:effective_limit]
                
                # UI Feedback elements
                progress_bar = st.progress(0)
                status_box = st.empty()
                
                try:
                    status_box.markdown("`Initializing connection to Gemini...`")
                    
                    # Run the classification loop
                    organized = categorize_bookmarks(
                        target_bookmarks, 
                        api_key, 
                        model_name=model_name, 
                        batch_size=batch_size,
                        progress_callback=lambda p: progress_bar.progress(p),
                        status_callback=lambda msg: status_box.markdown(f"`{msg}`")
                    )
                    
                    st.session_state.organized_bookmarks = organized
                    status_box.markdown("`✅ Organization Complete!`")
                    st.balloons()
                    st.success("All done! Head over to Tab 3 to see the results.")
                    
                    # Short delay to let user see the success message before potential rerun
                    time.sleep(1.5)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ An error occurred during AI processing: {e}")
                    st.markdown("**Troubleshooting Tip:** Check your API Key and ensure you have quota available.")

    # --- TAB 3: Export ---
    with tab_export:
        st.markdown("### 📂 Your Organized Library")
        
        if not st.session_state.organized_bookmarks:
            st.info("AI organization results will appear here after completion.")
        else:
            # Check for any "Error" categories which indicate API failures
            errors = [b for b in st.session_state.organized_bookmarks if str(b.get("category","")).startswith("Error")]
            if errors:
                st.warning(f"⚠️ {len(errors)} bookmarks could not be categorized due to errors. Check the list below.")
            
            st.dataframe(
                st.session_state.organized_bookmarks,
                column_config={
                    "source": st.column_config.TextColumn("Source", width="small"),
                    "url": st.column_config.LinkColumn("URL"),
                    "category": st.column_config.TextColumn("AI Category", width="medium"),
                    "title": "Title"
                },
                use_container_width=True,
                height=500,
                hide_index=True
            )
            
            html_content = generate_netscape_html(st.session_state.organized_bookmarks)
            
            st.download_button(
                label="📥 Download Organized HTML",
                data=html_content,
                file_name="ai_organized_bookmarks.html",
                mime="text/html",
                type="primary",
                help="Download a standard bookmarks file you can import into Chrome, Edge, or Firefox."
            )
            st.markdown("_Import this file via your browser's 'Import Bookmarks' settings._")

if __name__ == "__main__":
    main()
