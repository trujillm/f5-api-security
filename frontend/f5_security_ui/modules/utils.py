import base64
import streamlit as st
from typing import List, Dict, Any

def data_url_from_file(uploaded_file) -> str:
    """Convert uploaded file to data URL format."""
    try:
        file_content = uploaded_file.read()
        file_b64 = base64.b64encode(file_content).decode()
        mime_type = uploaded_file.type if hasattr(uploaded_file, 'type') else 'application/octet-stream'
        return f"data:{mime_type};base64,{file_b64}"
    except Exception as e:
        st.error(f"Error processing file {uploaded_file.name}: {str(e)}")
        return ""

def get_vector_db_name(vector_db) -> str:
    """Extract display name from vector database object."""
    if hasattr(vector_db, 'vector_db_name'):
        return vector_db.vector_db_name
    elif hasattr(vector_db, 'name'):
        return vector_db.name
    elif hasattr(vector_db, 'identifier'):
        return vector_db.identifier
    else:
        return str(vector_db)

def get_strategy(temperature: float, top_p: float) -> Dict[str, Any]:
    """Get sampling strategy for LLM inference."""
    return {
        "type": "top_p",
        "temperature": temperature,
        "top_p": top_p
    }


def reset_agent():
    """Reset agent state in Streamlit session."""
    if "messages" in st.session_state:
        st.session_state.messages = []
    if "debug_events" in st.session_state:
        st.session_state.debug_events = []
    if "agent" in st.session_state:
        st.session_state.agent = None
    if "session_id" in st.session_state:
        st.session_state.session_id = None
    if "selected_question" in st.session_state:
        st.session_state.selected_question = None
