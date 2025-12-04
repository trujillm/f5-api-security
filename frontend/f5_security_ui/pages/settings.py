import streamlit as st
import os
from datetime import datetime
from modules.api import f5_security_api
from modules.utils import get_vector_db_name

# Page config is now handled by app.py

# CSS is now handled centrally by app.py

# Page header
st.markdown("### ⚙️ Settings")
st.markdown("Configure your chat endpoint, model, and other application settings.")

# Initialize session state variables
if 'chat_endpoint' not in st.session_state:
    default_endpoint = os.getenv(
        'DEFAULT_CHAT_ENDPOINT', 
        'http://vllm-quantized.volt.thebizdevops.net'
    )
    st.session_state.chat_endpoint = default_endpoint

if "text_input_value" not in st.session_state:
    st.session_state.text_input_value = st.session_state.chat_endpoint

if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

if 'available_models' not in st.session_state:
    st.session_state.available_models = []

if 'models_loading' not in st.session_state:
    st.session_state.models_loading = False

if 'model_fetch_error' not in st.session_state:
    st.session_state.model_fetch_error = None

def fetch_models_from_endpoint(endpoint: str):
    """Fetch models from LlamaStack endpoint and update session state."""
    if not endpoint or not endpoint.strip():
        return
    
    st.session_state.models_loading = True
    st.session_state.model_fetch_error = None
    
    try:
        with st.spinner(f"🔄 Fetching models from {endpoint}..."):
            result = f5_security_api.test_llamastack_endpoint(endpoint)
            
            if result["success"]:
                # Extract model IDs from the models list
                model_ids = []
                for model in result["models"]:
                    if hasattr(model, 'identifier'):
                        model_ids.append(model.identifier)
                    elif hasattr(model, 'id'):
                        model_ids.append(model.id)
                    elif isinstance(model, dict):
                        model_ids.append(model.get('identifier') or model.get('id', 'unknown'))
                    else:
                        model_ids.append(str(model))
                
                st.session_state.available_models = model_ids
                st.session_state.model_fetch_error = None
            else:
                st.session_state.available_models = []
                st.session_state.model_fetch_error = result["error"]
                st.error(f"❌ Failed to connect to {endpoint}: {result['error']}")
                
    except Exception as e:
        st.session_state.available_models = []
        st.session_state.model_fetch_error = str(e)
        st.error(f"❌ Error fetching models: {str(e)}")
    finally:
        st.session_state.models_loading = False

def on_xc_url_change():
    """Callback function when XC URL changes."""
    new_endpoint = st.session_state.get("xc_url_input", "")
    if new_endpoint and new_endpoint != st.session_state.chat_endpoint:
        # Clear current model selection when XC URL changes
        st.session_state.selected_model = ""
        # Clear available models to force fresh fetch
        st.session_state.available_models = []
        # Fetch models from new endpoint
        fetch_models_from_endpoint(new_endpoint)
        st.session_state.chat_endpoint = new_endpoint

# XC URL Configuration
st.markdown("## 🔗 XC URL Configuration")

# Always get the current endpoint from session state
current_endpoint = st.session_state.chat_endpoint

# Initialize text input value if not set
if "text_input_value" not in st.session_state:
    st.session_state.text_input_value = current_endpoint

new_endpoint = st.text_input(
    "XC URL",
    value=st.session_state.text_input_value,
    help="Enter the LlamaStack endpoint URL:\n• http://vllm-quantized.volt.thebizdevops.net (External LlamaStack)\n• http://llamastack:8321 (Local LlamaStack)\n• https://your-f5-xc.com:8321 (F5 XC Proxy to LlamaStack)\n\nModels will be automatically fetched when you change the URL.",
    key="xc_url_input",
    on_change=on_xc_url_change
)

# Update the session state when user types
if new_endpoint != st.session_state.text_input_value:
    st.session_state.text_input_value = new_endpoint

# Auto-fetch models on page load if we haven't fetched them yet
if not st.session_state.available_models and not st.session_state.models_loading:
    # Auto-fetch models from XC URL endpoint
    if current_endpoint:
        fetch_models_from_endpoint(current_endpoint)

# Test button for XC URL
if st.button("🔄 Test", help="Test XC URL with selected model", type="primary", key="xc_url_test"):
    if new_endpoint and st.session_state.get("selected_model"):
        test_model = st.session_state.selected_model
        with st.spinner(f"Testing {new_endpoint} with model {test_model}..."):
            try:
                # Test the LlamaStack endpoint with the selected model
                llamastack_client = f5_security_api.get_llamastack_client(new_endpoint)
                
                # Test a simple chat completion
                response = llamastack_client.inference.chat_completion(
                    model_id=test_model,
                    messages=[{"role": "user", "content": "Hello"}],
                    sampling_params={
                        "temperature": 0.1,
                        "max_tokens": 10
                    }
                )
                
                # Extract response content
                if hasattr(response, 'completion_message') and hasattr(response.completion_message, 'content'):
                    test_response = response.completion_message.content
                elif hasattr(response, 'content'):
                    test_response = response.content
                else:
                    test_response = str(response)
                
                # Store test results in session state and trigger dialog
                st.session_state.test_success = True
                st.session_state.test_endpoint = new_endpoint
                st.session_state.test_model = test_model
                st.session_state.test_response = test_response
                st.rerun()
                
            except Exception as e:
                # Store test error in session state and trigger dialog
                st.session_state.test_success = False
                st.session_state.test_error = str(e)
                st.rerun()
    else:
        if not new_endpoint:
            st.warning("⚠️ Please enter an XC URL to test")
        if not st.session_state.get("selected_model"):
            st.warning("⚠️ Please select a model from the dropdown to test")

# Show test result dialogs based on session state
if st.session_state.get("test_success") is True:
    @st.dialog("✅ Test Successful!")
    def show_test_success():
        st.success("Connection test completed successfully!")
        st.info(f"**Endpoint**: `{st.session_state.test_endpoint}`")
        st.info(f"**Model**: `{st.session_state.test_model}`")
        st.info(f"**Response**: {st.session_state.test_response}")
        if st.button("Close", type="primary"):
            # Clear test results from session state
            del st.session_state.test_success
            del st.session_state.test_endpoint
            del st.session_state.test_model
            del st.session_state.test_response
            st.rerun()
    
    show_test_success()

elif st.session_state.get("test_success") is False:
    @st.dialog("❌ Test Failed")
    def show_test_error():
        st.error(f"Connection test failed: {st.session_state.test_error}")
        st.warning("Check that the XC URL is a valid LlamaStack endpoint and the model is available.")
        if st.button("Close", type="primary"):
            # Clear test error from session state
            del st.session_state.test_success
            del st.session_state.test_error
            st.rerun()
    
    show_test_error()

st.markdown("---")

# Model Configuration
st.markdown("## 🤖 Model Configuration")

# Show loading state or model dropdown
if st.session_state.models_loading:
    st.info("🔄 Fetching models from endpoint...")
    st.empty()  # Placeholder for loading
elif st.session_state.model_fetch_error:
    st.error(f"❌ Error fetching models: {st.session_state.model_fetch_error}")
    def retry_fetch_models():
        fetch_models_from_endpoint(current_endpoint)
    
    st.button("🔄 Retry", on_click=retry_fetch_models)
elif st.session_state.available_models:
    # Model dropdown with available models
    current_model = st.session_state.get("selected_model", "")
    
    # Always auto-select first model if no valid selection or if current selection is not in available models
    if not current_model or current_model not in st.session_state.available_models:
        if st.session_state.available_models:
            current_model = st.session_state.available_models[0]
            st.session_state.selected_model = current_model
    
    selected_model = st.selectbox(
        "Model ID",
        options=st.session_state.available_models,
        index=st.session_state.available_models.index(current_model) if current_model in st.session_state.available_models else 0,
        help="Select a model from the available models on the LlamaStack endpoint",
        key="model_dropdown"
    )
    
    # Update session state
    st.session_state.selected_model = selected_model
else:
    def fetch_models_button():
        fetch_models_from_endpoint(current_endpoint)
    
    st.button("🔄 Fetch Models", on_click=fetch_models_button)

# Model fetching is always from XC URL endpoint
    
    # Direct model fetch without triggering test dialogs
    try:
        # Get LlamaStack client and fetch models directly
        client = f5_security_api.get_llamastack_client(endpoint)
        models = client.models.list()
        
        # Extract model IDs from the models list
        model_ids = []
        for model in models:
            if hasattr(model, 'identifier'):
                model_ids.append(model.identifier)
            elif hasattr(model, 'id'):
                model_ids.append(model.id)
            elif isinstance(model, dict):
                model_ids.append(model.get('identifier') or model.get('id', 'unknown'))
            else:
                model_ids.append(str(model))
        
        st.session_state.available_models = model_ids
        # Auto-select first model immediately when models are fetched
        if model_ids:
            st.session_state.selected_model = model_ids[0]
        else:
            st.session_state.selected_model = ""
        st.session_state.model_fetch_error = None
    except Exception as e:
        st.session_state.available_models = []
        st.session_state.selected_model = ""
        st.session_state.model_fetch_error = str(e)
    
    st.rerun()

st.markdown("---")

# Debug Configuration
st.markdown("## 🐛 Debug Configuration")

# Debug toggle
debug_mode = st.toggle("🐛 Debug Mode", value=st.session_state.debug_mode, help="Show detailed processing information")

# Update session state
st.session_state.debug_mode = debug_mode

# Auto-select all available vector databases for RAG (hidden from UI)
try:
    vector_dbs = f5_security_api.get_default_llamastack_client().vector_dbs.list() or []
    if vector_dbs:
        vector_db_names = [get_vector_db_name(vector_db) for vector_db in vector_dbs]
        selected_vector_dbs = vector_db_names  # Auto-select all available
    else:
        selected_vector_dbs = []
    
    # Debug: Log vector database listing
    if debug_mode:
        st.markdown("### 🔍 Vector Database Debug")
        st.json({
            "vector_dbs_found": len(vector_dbs),
            "vector_db_names": [get_vector_db_name(vdb) for vdb in vector_dbs] if vector_dbs else [],
            "selected_vector_dbs": selected_vector_dbs
        })
        
except Exception as e:
    selected_vector_dbs = []
    # Debug: Log vector database listing error
    if debug_mode:
        st.markdown("### ❌ Vector Database Error")
        st.error(f"Error listing vector databases: {str(e)}")

# Settings configuration complete