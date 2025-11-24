import streamlit as st
import json
import os
from datetime import datetime
from openai import OpenAI
from modules.api import llama_stack_api
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

# Custom CSS to set sidebar default width while preserving drag-resize functionality
st.markdown("""
<style>
    /* Set default width but allow resizing */
    .css-1d391kg {
        width: 500px;  /* Default width (no !important to allow resizing) */
        min-width: 400px !important;  /* Minimum width */
        max-width: 800px !important;  /* Maximum width */
    }
    
    /* Alternative selectors for different Streamlit versions */
    section[data-testid="stSidebar"] {
        width: 500px;  /* Default width (no !important) */
        min-width: 400px !important;  /* Minimum width */
        max-width: 800px !important;  /* Maximum width */
    }
    
    section[data-testid="stSidebar"] > div {
        min-width: 400px !important;  /* Minimum width */
        max-width: 800px !important;  /* Maximum width */
    }
    
    /* Ensure text inputs in sidebar use full width */
    .css-1d391kg .stTextInput > div > div > input {
        width: 100% !important;
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        width: 100% !important;
    }
    
    /* Ensure the main content area adjusts dynamically (remove fixed margin) */
    .css-18e3th9 {
        margin-left: auto !important;
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

# Sidebar configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # XC URL Configuration (moved to first position)
    st.markdown("#### 🔗 XC URL")
    
    # Initialize session state for chat endpoint (from environment or default)
    if 'chat_endpoint' not in st.session_state:
        default_endpoint = os.getenv(
            'DEFAULT_CHAT_ENDPOINT', 
            'http://vllm-quantized.volt.thebizdevops.net/v1/openai/v1'
        )
        st.session_state.chat_endpoint = default_endpoint
    
    # Always get the current endpoint from session state
    current_endpoint = st.session_state.chat_endpoint
    
    # Show current endpoint
    st.info(f"**Current**: `{current_endpoint}`")
    
    # API endpoint input
    # Use session state to control the text input value directly
    # Always sync with the current endpoint initially
    if "text_input_value" not in st.session_state:
        st.session_state.text_input_value = current_endpoint
    
    # Use a dynamic key if we're forcing a refresh
    widget_key = "api_endpoint_input"
    if st.session_state.get("force_widget_refresh", False):
        widget_key = f"api_endpoint_input_{hash(st.session_state.text_input_value)}"
        # Clear the refresh flag after using it
        del st.session_state["force_widget_refresh"]
    
    new_endpoint = st.text_input(
        "XC URL",
        value=st.session_state.text_input_value,
        help="Enter the XC (F5 Distributed Cloud) endpoint URL (OpenAI-compatible):\n• https://redhataillama-31-8b-instruct-quickstart-llms.apps.ai-dev02.kni.syseng.devcluster.openshift.com/v1 (Direct RHOAI LLM - no API key needed)\n• https://your-f5-xc.com/v1 (F5 XC Proxy)\n• https://api.openai.com/v1 (OpenAI - requires API key in YAML config)\n• http://localhost:8080/v1 (Local F5 proxy)\n\nNote: API key is configured in chatEndpoint.apiKey in values.yaml",
        key=widget_key
    )
    
    # Update the session state when user types
    if new_endpoint != st.session_state.text_input_value:
        st.session_state.text_input_value = new_endpoint
        # Clear any reset flag when user starts typing again
        if "reset_text_input" in st.session_state:
            del st.session_state["reset_text_input"]
    
    # Get current model for XC URL update logic (defined later in the file)
    default_model = os.getenv('DEFAULT_MODEL', 'remote-llm/RedHatAI/Llama-3.2-1B-Instruct-quantized.w8a8')
    # For XC URL update, we need to use the current model - get it from session state or default
    # This is a temporary definition; the actual model input is defined later
    model = default_model  # Will be overridden later with actual input
    
    # Endpoint control buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Test", help="Test chat endpoint and update if test passes", type="primary", key="xc_url_update"):
            if new_endpoint:
                # Get the current Model ID from the widget state (if it exists)
                current_model_id = st.session_state.get("model_input", default_model)
                if not current_model_id.strip():
                    current_model_id = default_model
                
                with st.spinner("Testing endpoint and model compatibility..."):
                    try:
                        # Always use OpenAI API for comprehensive testing
                        api_key = os.getenv('DEFAULT_API_KEY', 'dummy-key')
                        test_client = OpenAI(base_url=new_endpoint, api_key=api_key)
                        
                        # Step 1: Test models endpoint
                        models_response = test_client.models.list()
                        
                        if hasattr(models_response, 'data'):
                            available_models = []
                            for api_model in models_response.data:
                                # Handle both OpenAI format (id) and vLLM format (identifier)
                                model_id = None
                                if hasattr(api_model, 'id') and api_model.id is not None:
                                    model_id = api_model.id
                                elif hasattr(api_model, 'identifier') and api_model.identifier is not None:
                                    model_id = api_model.identifier
                                
                                if model_id:
                                    available_models.append(model_id)
                        else:
                            available_models = []
                        
                        models_count = len(available_models)
                        
                        # Step 2: Check if current model is available on new endpoint
                        model_available_on_new_endpoint = current_model_id in available_models
                        
                        # Step 3: Test actual chat completion with current model
                        if model_available_on_new_endpoint:
                            chat_response = test_client.chat.completions.create(
                                model=current_model_id,
                                messages=[{"role": "user", "content": "Hello"}],
                                max_tokens=10,
                                temperature=0.1
                            )
                            test_response = chat_response.choices[0].message.content if chat_response.choices else "No response"
                            chat_success = True
                        else:
                            test_response = None
                            chat_success = False
                        
                        if model_available_on_new_endpoint and chat_success:
                            # SUCCESS - Both endpoint and model work together
                            st.session_state.chat_endpoint = new_endpoint
                            st.session_state.text_input_value = new_endpoint
                            
                            # Create success dialog
                            @st.dialog("🎉 Endpoint Updated Successfully!")
                            def show_success_dialog():
                                st.success("✅ **Endpoint and model compatibility verified!**")
                                
                                st.markdown("### 📊 Combined Test Summary:")
                                st.markdown(f"- **New Endpoint**: `{new_endpoint}`")
                                st.markdown(f"- **Current Model**: `{current_model_id}`")
                                st.markdown(f"- **Models Available**: {models_count}")
                                st.markdown(f"- **Model Compatible**: ✅ Yes")
                                st.markdown(f"- **Chat Completion**: ✅ Success")
                                st.markdown(f"- **Status**: ✅ **Updated and Ready!**")
                                
                                st.markdown("### 🤖 Sample Response:")
                                st.code(test_response, language="text")
                                
                                st.markdown("---")
                                st.info("💡 **Perfect match!** Your endpoint and model work together seamlessly.")
                                
                                if st.button("Close", type="primary"):
                                    st.rerun()
                            
                            show_success_dialog()
                        else:
                            # FAILURE - Model not compatible with new endpoint
                            error_title = "❌ Endpoint Update Failed - Model Incompatibility"
                            if not model_available_on_new_endpoint:
                                error_details = f"Your current model `{current_model_id}` is not available on the new endpoint."
                                
                                # Smart suggestions for compatible models
                                similar_models = []
                                model_lower = current_model_id.lower() if current_model_id and isinstance(current_model_id, str) else ""
                                for avail_model in available_models:
                                    avail_model_lower = avail_model.lower()
                                    if (model_lower in avail_model_lower or 
                                        avail_model_lower in model_lower or
                                        any(word in avail_model_lower for word in model_lower.split('-')) or
                                        any(word in avail_model_lower for word in model_lower.split('_'))):
                                        similar_models.append(avail_model)
                                
                                if similar_models:
                                    error_suggestion = f"🎯 **Compatible models found**: {', '.join(similar_models[:3])}"
                                else:
                                    error_suggestion = f"💡 **Available models**: {', '.join(available_models[:5])}{'...' if len(available_models) > 5 else ''}"
                            else:
                                error_details = f"Model `{current_model_id}` exists but chat completion failed."
                                error_suggestion = "The model might have compatibility issues with this endpoint."
                            
                            # Create error dialog - NO UPDATE HAPPENS
                            @st.dialog(error_title)
                            def show_compatibility_error_dialog():
                                st.error("**Update cancelled - model incompatibility detected!**")
                                
                                st.markdown("### 📊 Compatibility Test Summary:")
                                st.markdown(f"- **Attempted Endpoint**: `{new_endpoint}`")
                                st.markdown(f"- **Current Model**: `{current_model_id}`")
                                st.markdown(f"- **Models Available**: {models_count}")
                                st.markdown(f"- **Model Compatible**: {'✅' if model_available_on_new_endpoint else '❌'}")
                                st.markdown(f"- **Chat Completion**: ❌ Failed")
                                st.markdown(f"- **Status**: ❌ **Not Updated**")
                                
                                st.markdown("### 🔍 Incompatibility Details:")
                                st.code(error_details, language="text")
                                
                                if available_models:
                                    st.markdown("### 📋 Compatible Models on New Endpoint:")
                                    for i, avail_model in enumerate(available_models[:10]):
                                        st.markdown(f"- `{avail_model}`")
                                    if len(available_models) > 10:
                                        st.markdown(f"... and {len(available_models) - 10} more")
                                
                                st.markdown("### 💡 Resolution Options:")
                                st.info(error_suggestion)
                                st.info("🔧 **Option 1**: Update your Model ID first to a compatible model, then update the endpoint.")
                                st.info("🔧 **Option 2**: Choose a different endpoint that supports your current model.")
                                
                                st.markdown("---")
                                st.warning("⚠️ **Endpoint not updated.** Resolve model compatibility first.")
                                
                                if st.button("Close", type="primary"):
                                    st.rerun()
                            
                            show_compatibility_error_dialog()
                        
                    except Exception as e:
                        # Handle the specific NoneType attribute error
                        if isinstance(e, AttributeError) and "'NoneType' object has no attribute 'lower'" in str(e):
                            error_title = "❌ Update Failed - Server Response Format Issue"
                            error_details = "The server returned data in an unexpected format that the OpenAI client cannot process."
                            error_suggestion = "This vLLM server may not be fully OpenAI-compatible. Try a different endpoint or check the server configuration."
                        else:
                            # Handle other errors with robust error message handling
                            error_msg = "Unknown error"
                            try:
                                if e is not None:
                                    error_msg = str(e)
                                else:
                                    error_msg = "Exception was None"
                            except Exception:
                                error_msg = f"Error occurred but could not be converted to string: {type(e).__name__}"
                            
                            # Determine error type and message
                            if "404" in error_msg or "Not Found" in error_msg:
                                error_title = "❌ Update Failed - Chat Endpoint Not Found"
                                error_details = "The `/v1/chat/completions` endpoint is not available on this server."
                                error_suggestion = "This might be a LlamaStack server that only supports native API, not OpenAI-compatible endpoints."
                            elif "405" in error_msg or "Method Not Allowed" in error_msg:
                                error_title = "❌ Update Failed - Method Not Allowed"
                                error_details = "The chat endpoint doesn't support POST requests."
                                error_suggestion = "Check if this is the correct endpoint URL and supports OpenAI API format."
                            elif "Model" in error_msg and "not found" in error_msg:
                                error_title = "❌ Update Failed - Model Not Available"
                                error_details = f"The model `{current_model_id}` is not available on this endpoint."
                                error_suggestion = "Try checking available models or use a different model ID."
                            else:
                                error_title = "❌ Update Failed - Connection Error"
                                error_details = f"Unexpected error: {error_msg}"
                                error_suggestion = "Check the endpoint URL, network connectivity, and API compatibility."
                        
                        # Create error dialog - NO UPDATE HAPPENS
                        @st.dialog(error_title)
                        def show_error_dialog():
                            st.error("**Update cancelled - endpoint test failed!**")
                            
                            st.markdown("### 📊 Test Summary:")
                            st.markdown(f"- **Attempted Endpoint**: `{new_endpoint}`")
                            st.markdown(f"- **Model**: `{current_model_id}`")
                            st.markdown(f"- **Connection**: ❌ Failed")
                            st.markdown(f"- **Status**: ❌ **Not Updated**")
                            
                            st.markdown("### 🔍 Error Details:")
                            st.code(error_details, language="text")
                            
                            st.markdown("### 💡 Suggestion:")
                            st.info(error_suggestion)
                            
                            st.markdown("---")
                            st.warning("⚠️ **Endpoint not updated.** Fix the issues above and try again.")
                            
                            if st.button("Close", type="primary"):
                                st.rerun()
                        
                        show_error_dialog()
            else:
                st.warning("⚠️ Please enter a valid XC URL")
    
    with col2:
        if st.button("🔄 Reset", help="Reset XC URL to current endpoint", key="xc_url_reset"):
            # Reset the text input to match the current working endpoint
            # This handles cases where user typed a bad URL but update failed
            st.session_state.text_input_value = current_endpoint
            
            # More aggressive widget state clearing
            widget_keys_to_clear = ["api_endpoint_input"]
            for key in widget_keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Set a flag to indicate we just reset and force widget recreation
            st.session_state.reset_text_input = True
            st.session_state.force_widget_refresh = True
            
            st.success(f"✅ Reset XC URL to current endpoint: `{current_endpoint}`")
            st.rerun()
    
    st.markdown("---")
    
    # Model selection with consistent UX pattern
    st.markdown("#### 🤖 Model ID")
    
    default_model = os.getenv('DEFAULT_MODEL', 'redhataillama-31-8b-instruct')
    
    
    new_model = st.text_input(
        "Model ID",
        value=default_model,
        help="Model ID to use for chat completions",
        key="model_input"
    )
    
    # API Key field
    default_api_key = os.getenv('DEFAULT_API_KEY', '')
    
    new_api_key = st.text_input(
        "API Key",
        value=default_api_key,
        help="API key for endpoints that require authentication (leave empty for public endpoints like RHOAI)",
        type="password",
        key="api_key_input"
    )
    
    # Use the field values directly for API calls (override the temporary definition from earlier)
    model = new_model if new_model.strip() else default_model
    
    # Update the session state when user types
    if new_endpoint != st.session_state.text_input_value:
        st.session_state.text_input_value = new_endpoint
        # Clear any reset flag when user starts typing again
        if "reset_text_input" in st.session_state:
            del st.session_state["reset_text_input"]
    
    
    # Debug toggle (must be defined before vector DB logic)
    debug_mode = st.toggle("🐛 Debug Mode", value=False, help="Show detailed processing information")
    
    # Auto-select all available vector databases for RAG (hidden from UI)
    try:
        vector_dbs = llama_stack_api.get_llamastack_client().vector_dbs.list() or []
        if vector_dbs:
            vector_db_names = [get_vector_db_name(vector_db) for vector_db in vector_dbs]
            selected_vector_dbs = vector_db_names  # Auto-select all available
        else:
            selected_vector_dbs = []
        
        # Debug: Log vector database listing in sidebar
        if debug_mode:
            st.sidebar.markdown("#### 🔍 Vector Database Debug")
            st.sidebar.json({
                "vector_dbs_found": len(vector_dbs),
                "vector_db_names": [get_vector_db_name(vdb) for vdb in vector_dbs] if vector_dbs else [],
                "selected_vector_dbs": selected_vector_dbs
            })
            
    except Exception as e:
        selected_vector_dbs = []
        # Debug: Log vector database listing error
        if debug_mode:
            st.sidebar.markdown("#### ❌ Vector Database Error")
            st.sidebar.error(f"Error listing vector databases: {str(e)}")

# System prompt for Demo Application
system_prompt = """You are a helpful AI assistant for this demo application. You can help users with:

🤖 **Application Features:**
- Chat interface and conversation management
- Document upload and RAG (Retrieval-Augmented Generation)
- LLM endpoint configuration and testing
- General questions about AI and machine learning

🔒 **Security Context:**
- This application is protected by F5 Distributed Cloud
- F5 XC provides API security, rate limiting, and threat protection
- The security layer is transparent to the application functionality

📋 **How to Help:**
- Answer questions about the uploaded documents (if any)
- Explain application features and functionality
- Provide general information on topics you're knowledgeable about
- Help users understand how to use this demo application

Be helpful, accurate, and conversational. If you don't know something, say so clearly."""

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
        vector_dbs = llama_stack_api.get_llamastack_client().vector_dbs.list() or []
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
                test_response = llama_stack_api.get_llamastack_client().tool_runtime.rag_tool.query(
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
                    rag_response = llama_stack_api.get_llamastack_client().tool_runtime.rag_tool.query(
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
        f5_enhanced_prompt = f"""As an F5 API Security expert, please answer the following query using the provided F5 documentation context.

CONTEXT FROM F5 DOCUMENTATION:
{prompt_context}

QUERY:
{prompt}

📋 INSTRUCTIONS:
- Use the provided F5 documentation context to inform your response
- Focus on API security best practices from F5 products
- Provide actionable F5 security recommendations based on the documentation
- Include specific F5 product capabilities mentioned in the context
- Reference threat mitigation strategies from the documentation
- Emphasize enterprise-grade F5 security solutions"""
    else:
        f5_enhanced_prompt = f"""As an F5 API Security expert, please provide comprehensive guidance on:

{prompt}

📋 INSTRUCTIONS:
- Focus on API security best practices
- Consider OWASP API Security Top 10
- Provide actionable F5 security recommendations
- Include threat mitigation strategies
- Reference F5 products and capabilities when relevant
- Emphasize enterprise-grade security solutions"""

    # Debug: Log the constructed enhanced prompt
    debug_events_list.append({
        "type": "enhanced_prompt_construction",
        "timestamp": datetime.now().isoformat(),
        "has_rag_context": bool(prompt_context),
        "prompt_length": len(f5_enhanced_prompt),
        "enhanced_prompt": f5_enhanced_prompt[:500] + "..." if len(f5_enhanced_prompt) > 500 else f5_enhanced_prompt
    })

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            f5_messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f5_enhanced_prompt}
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

                # Always use OpenAI API for chat completions (simplified approach)
                # Use API key field value directly, fallback to environment, then dummy
                api_key_for_chat = new_api_key if new_api_key.strip() else os.getenv('DEFAULT_API_KEY', 'dummy-key')
                
                openai_chat_client = OpenAI(
                    base_url=active_endpoint,
                    api_key=api_key_for_chat
                )
                
                response = openai_chat_client.chat.completions.create(
                    model=model,
                    messages=f5_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    stream=False  # Disabled streaming for compatibility
                )
            
                # Handle OpenAI API response format
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    full_response = response.choices[0].message.content
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
