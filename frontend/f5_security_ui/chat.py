import streamlit as st
import json
import os
from datetime import datetime
from modules.api import f5_security_api
from modules.utils import get_vector_db_name
from constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P, 
    DEFAULT_MAX_TOKENS,
    DEFAULT_REPETITION_PENALTY
)

st.set_page_config(
    page_title="Chat",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for consistent fixed sidebar width across all tabs
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

# Sidebar navigation

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "debug_events" not in st.session_state:
    st.session_state.debug_events = []

# Page header
st.markdown("### 💬 Chat")

# Initialize session state for configuration (moved from Settings page)
if 'chat_endpoint' not in st.session_state:
    from constants import DEFAULT_XC_URL
    default_endpoint = os.getenv(
        'DEFAULT_CHAT_ENDPOINT', 
        DEFAULT_XC_URL
    )
    st.session_state.chat_endpoint = default_endpoint

if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# Get configuration values from session state (set in Settings page)
debug_mode = st.session_state.debug_mode

# Get model from session state (selected in Settings dropdown)
model = st.session_state.get("selected_model", "")
if not model:
    # Fallback if no model selected yet
    if st.session_state.get("available_models"):
        model = st.session_state.available_models[0]
    else:
        model = "default-model"  # Fallback

# Auto-select all available vector databases for RAG (hidden from UI)
try:
    vector_dbs = f5_security_api.get_default_llamastack_client().vector_dbs.list() or []
    if vector_dbs:
        vector_db_names = [get_vector_db_name(vector_db) for vector_db in vector_dbs]
        selected_vector_dbs = vector_db_names  # Auto-select all available
    else:
        selected_vector_dbs = []
        
except Exception as e:
    selected_vector_dbs = []


# System prompt
system_prompt = "You are a helpful AI assistant."

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Debug information
if debug_mode and st.session_state.debug_events:
    with st.expander("🐛 Debug Information", expanded=False):
        for i, events in enumerate(st.session_state.debug_events):
            st.markdown(f"**Turn {i+1}:**")
            for event in events:
                st.json(event)

# Chat input
def process_chat_prompt(prompt, model, selected_vector_dbs, system_prompt):
    """Process chat prompt using Direct Mode RAG with sensible defaults."""
    
    # Sensible defaults for chat responses
    temperature = DEFAULT_TEMPERATURE      # Balanced creativity for helpful responses
    top_p = DEFAULT_TOP_P                 # Good diversity while staying focused
    max_tokens = DEFAULT_MAX_TOKENS       # Sufficient for detailed explanations
    repetition_penalty = DEFAULT_REPETITION_PENALTY  # Slight penalty to avoid repetition
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Prepare debug events for this turn
    st.session_state.debug_events.append([])
    current_turn_debug_events = st.session_state.debug_events[-1]
    
    # Direct Mode Processing with RAG
    direct_process_prompt(prompt, model, selected_vector_dbs, system_prompt, temperature, top_p, max_tokens, repetition_penalty, current_turn_debug_events)

def direct_process_prompt(prompt, model, selected_vector_dbs, system_prompt, temperature, top_p, max_tokens, repetition_penalty, debug_events_list):
    """Direct Mode processing with optional RAG."""
    
    # Step 1: RAG Query (if vector databases are available)
    prompt_context = None
    
    # Debug: Log vector database selection
    debug_events_list.append({
        "type": "vector_db_selection",
        "timestamp": datetime.now().isoformat(),
        "selected_vector_dbs": selected_vector_dbs,
        "selected_count": len(selected_vector_dbs) if selected_vector_dbs else 0
    })
    
    if selected_vector_dbs:
        vector_dbs = f5_security_api.get_default_llamastack_client().vector_dbs.list() or []
        vector_db_ids = [vector_db.identifier for vector_db in vector_dbs if get_vector_db_name(vector_db) in selected_vector_dbs]
        
        # Debug: Log available vector databases
        debug_events_list.append({
            "type": "available_vector_dbs",
            "timestamp": datetime.now().isoformat(),
            "total_vector_dbs": len(vector_dbs),
            "matching_vector_db_ids": vector_db_ids,
            "all_vector_dbs": [{"name": get_vector_db_name(vdb), "id": vdb.identifier} for vdb in vector_dbs]
        })
        
        # Debug: Try to get vector database info for troubleshooting
        try:
            for vdb_id in vector_db_ids[:1]:  # Only check first one to avoid spam
                # Note: LlamaStack doesn't have a direct way to list documents, 
                # but we can try a very broad search to see if anything is stored
                test_response = f5_security_api.get_default_llamastack_client().tool_runtime.rag_tool.query(
                    content="test query to check if database has content", 
                    vector_db_ids=[vdb_id]
                )
                debug_events_list.append({
                    "type": "vector_db_content_test",
                    "timestamp": datetime.now().isoformat(),
                    "vector_db_id": vdb_id,
                    "test_query_result_length": len(test_response.content) if test_response.content else 0,
                    "test_query_has_content": bool(test_response.content),
                    "test_response_preview": (str(test_response.content[:100]) + "..." if test_response.content else "Empty")
                })
        except Exception as test_error:
            debug_events_list.append({
                "type": "vector_db_content_test_error",
                "timestamp": datetime.now().isoformat(),
                "error": str(test_error)
            })
        
        if vector_db_ids:
            with st.spinner("🔍 Retrieving relevant F5 security documentation..."):
                try:
                    rag_response = f5_security_api.get_default_llamastack_client().tool_runtime.rag_tool.query(
                        content=prompt, 
                        vector_db_ids=list(vector_db_ids)
                    )
                    prompt_context = rag_response.content
                    
                    # Debug: Log detailed RAG response
                    debug_events_list.append({
                        "type": "f5_rag_query",
                        "timestamp": datetime.now().isoformat(),
                        "query": prompt,
                        "vector_dbs": selected_vector_dbs,
                        "vector_db_ids_used": vector_db_ids,
                        "context_length": len(prompt_context) if prompt_context else 0,
                        "context_preview": (str(prompt_context[:200]) + "..." if prompt_context else "None"),
                        "rag_response_type": type(rag_response).__name__,
                        "rag_response_content_empty": not bool(prompt_context),
                        "rag_response_raw": str(rag_response)[:500] + "..." if len(str(rag_response)) > 500 else str(rag_response),
                        "rag_response_has_content_attr": hasattr(rag_response, 'content'),
                        "rag_response_content_type": type(rag_response.content).__name__ if hasattr(rag_response, 'content') else "N/A"
                    })
                except Exception as e:
                    # Robust error message handling
                    try:
                        error_msg = str(e) if e is not None else "Unknown RAG error"
                    except:
                        error_msg = "RAG error occurred but could not be converted to string"
                    
                    st.warning(f"RAG Error: {error_msg}")
                    debug_events_list.append({
                        "type": "f5_rag_error", 
                        "timestamp": datetime.now().isoformat(),
                        "error": error_msg,
                        "vector_db_ids_attempted": vector_db_ids
                    })
        else:
            # Debug: No matching vector database IDs found
            debug_events_list.append({
                "type": "no_matching_vector_dbs",
                "timestamp": datetime.now().isoformat(),
                "selected_vector_dbs": selected_vector_dbs,
                "available_vector_dbs": len(vector_dbs),
                "message": "No vector database IDs matched the selected databases"
            })
    else:
        # Debug: No vector databases selected
        debug_events_list.append({
            "type": "no_vector_dbs_selected",
            "timestamp": datetime.now().isoformat(),
            "message": "No vector databases were selected for RAG"
        })
    
    # Step 2: Construct Enhanced Prompt with Context
    if prompt_context:
        enhanced_prompt = f"""Please answer the following query using the provided documentation context.

CONTEXT FROM DOCUMENTATION:
{prompt_context}

QUERY:
{prompt}

Please provide a comprehensive answer based on the context above."""
    else:
        enhanced_prompt = f"""{prompt}"""

    # Debug: Log the constructed enhanced prompt
    debug_events_list.append({
        "type": "enhanced_prompt_construction",
        "timestamp": datetime.now().isoformat(),
        "has_rag_context": bool(prompt_context),
        "prompt_length": len(enhanced_prompt),
        "enhanced_prompt": enhanced_prompt[:500] + "..." if len(enhanced_prompt) > 500 else enhanced_prompt
    })

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': enhanced_prompt}
            ]
            
            # Show spinner while waiting for LLM response
            with st.spinner("🤖 Assistant is thinking..."):
                # Get the current endpoint from session state to ensure it's up-to-date
                active_endpoint = st.session_state.chat_endpoint

                # Log which endpoint is being used for debugging
                debug_events_list.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": "endpoint_selection",
                    "endpoint": active_endpoint
                })

                # Use native LlamaStack client for chat completions
                # Get the current endpoint from session state to ensure it's up-to-date
                active_endpoint = st.session_state.chat_endpoint
                
                llamastack_client = f5_security_api.get_llamastack_client(active_endpoint)
                
                response = llamastack_client.inference.chat_completion(
                    model_id=model,
                    messages=messages,
                    sampling_params={
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p
                    }
                )
            
                # Handle LlamaStack response format
                if hasattr(response, 'completion_message') and hasattr(response.completion_message, 'content'):
                    full_response = response.completion_message.content
                elif hasattr(response, 'content'):
                    full_response = response.content
                else:
                    full_response = str(response)
            
            message_placeholder.markdown(full_response)
            
            # Log successful completion
            debug_events_list.append({
                "type": "f5_security_completion",
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "response_length": len(full_response),
                "status": "success"
            })
            
        except Exception as e:
            # Robust error message handling
            try:
                error_str = str(e) if e is not None else "Unknown LLM error"
            except:
                error_str = "LLM error occurred but could not be converted to string"
            
            error_msg = f"LLM Error: {error_str}"
            message_placeholder.error(error_msg)
            full_response = f"❌ {error_msg}"
            
            # Log error
            debug_events_list.append({
                "type": "f5_security_error",
                "timestamp": datetime.now().isoformat(),
                "error": error_str,
                "model": model
            })
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Sidebar info

# Chat input
if prompt := st.chat_input("Ask a question..."):
    process_chat_prompt(prompt, model, selected_vector_dbs, system_prompt)
