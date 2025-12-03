import streamlit as st

def main():
    # Set page configuration
    st.set_page_config(
        page_title="AI Chat Assistant",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for consistent sidebar width across all pages
    st.markdown("""
    <style>
        /* Target all possible sidebar containers with fixed width */
        .css-1d391kg, .css-1lcbmhc, .css-17eq0hr, 
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div,
        .stSidebar, .stSidebar > div,
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
            width: 500px !important;
            min-width: 500px !important;
            max-width: 500px !important;
        }
        
        /* Keep main content area left-aligned, not centered */
        .main .block-container {
            max-width: none !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            margin-left: 0 !important;
            margin-right: auto !important;
        }
        
        /* Ensure text inputs in sidebar use full width */
        .css-1d391kg .stTextInput > div > div > input,
        section[data-testid="stSidebar"] .stTextInput > div > div > input {
            width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Define available pages: title, path, and icon
    pages = {
        "Chat": ("chat.py", "💬"),
        "Upload": ("pages/upload.py", "📤"),
        "Settings": ("pages/settings.py", "⚙️"),
    }

    # Build navigation items dynamically with capitalized titles
    nav_items = [
        st.Page(path, title=name, icon=icon, default=(name == "Chat"))
        for name, (path, icon) in pages.items()
    ]
    
    # Render navigation with our pages
    pg = st.navigation({"AI Chat Assistant": nav_items}, expanded=True)
    pg.run()


if __name__ == "__main__":
    main()