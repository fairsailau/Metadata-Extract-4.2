import streamlit as st
import logging
import json
import re
from datetime import datetime
from boxsdk import Client

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_value_field_type(metadata_values):
    """
    Fix the value field type by converting string values to numbers.
    
    This function specifically targets the 'value' field in metadata and ensures
    it's converted to a number before being sent to the Box API.
    
    Args:
        metadata_values (dict): The metadata values to process
        
    Returns:
        dict: The processed metadata with value field converted to number if needed
    """
    # Make a copy to avoid modifying the original
    fixed_metadata = metadata_values.copy()
    
    # Check if 'value' field exists
    if 'value' in fixed_metadata:
        value = fixed_metadata['value']
        original_value = value
        
        # If value is a string that represents a number, convert it
        if isinstance(value, str):
            try:
                # Try to convert to int first if it's a whole number
                if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                    fixed_metadata['value'] = int(value)
                    logger.info(f"Converted string value '{value}' to integer: {fixed_metadata['value']}")
                # Otherwise try to convert to float
                else:
                    # Remove any non-numeric characters except decimal point and minus sign
                    numeric_str = re.sub(r'[^\d.-]', '', value)
                    if numeric_str:
                        fixed_metadata['value'] = float(numeric_str)
                        logger.info(f"Converted string value '{value}' to float: {fixed_metadata['value']}")
                    else:
                        logger.warning(f"Value '{value}' doesn't contain numeric characters, keeping as is")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not convert value '{value}' to a number: {str(e)}")
        
        # Log the conversion result
        if original_value != fixed_metadata['value']:
            logger.info(f"Value field converted from {type(original_value).__name__} '{original_value}' to {type(fixed_metadata['value']).__name__} {fixed_metadata['value']}")
    
    return fixed_metadata

def validate_metadata_fields(metadata_values, template_info=None):
    """
    Validate and fix metadata fields based on template requirements.
    
    This function performs basic validation and type conversion for common field types.
    
    Args:
        metadata_values (dict): The metadata values to validate
        template_info (dict, optional): Template information with field types
        
    Returns:
        dict: The validated metadata with proper field types
    """
    # Make a copy to avoid modifying the original
    validated_metadata = metadata_values.copy()
    
    # Always fix the value field
    validated_metadata = fix_value_field_type(validated_metadata)
    
    # If template info is provided, perform additional validations
    if template_info and 'fields' in template_info:
        field_types = {field['key']: field['type'] for field in template_info['fields'] if 'key' in field and 'type' in field}
        
        for key, value in list(validated_metadata.items()):
            if key in field_types:
                field_type = field_types[key]
                
                # Convert based on field type
                if field_type == 'float' and not isinstance(value, (int, float)):
                    try:
                        if isinstance(value, str):
                            # Try to convert string to number
                            numeric_str = re.sub(r'[^\d.-]', '', value)
                            if numeric_str:
                                if numeric_str.isdigit() or (numeric_str.startswith('-') and numeric_str[1:].isdigit()):
                                    validated_metadata[key] = int(numeric_str)
                                else:
                                    validated_metadata[key] = float(numeric_str)
                                logger.info(f"Converted field '{key}' from {type(value).__name__} '{value}' to {type(validated_metadata[key]).__name__} {validated_metadata[key]}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert field '{key}' to float: {str(e)}")
                
                elif field_type == 'date' and isinstance(value, str):
                    # Ensure date is in ISO format
                    if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
                        try:
                            # Try common date formats
                            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
                                try:
                                    dt = datetime.strptime(value, fmt)
                                    validated_metadata[key] = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                                    logger.info(f"Converted date field '{key}' to ISO format: {validated_metadata[key]}")
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            logger.warning(f"Could not convert date field '{key}': {str(e)}")
    
    return validated_metadata

def verify_metadata_application(result):
    """
    Verify the result of metadata application and provide detailed diagnostics.
    
    Args:
        result (dict): The result of metadata application
        
    Returns:
        dict: Verification result with diagnostics
    """
    verification = {
        "success": result.get("success", False),
        "file_id": result.get("file_id", ""),
        "file_name": result.get("file_name", ""),
        "diagnostics": []
    }
    
    if result.get("success"):
        verification["diagnostics"].append("✅ Metadata application successful")
        
        # Check if metadata was returned
        if "metadata" in result:
            metadata = result["metadata"]
            verification["diagnostics"].append(f"✅ Metadata response received with {len(metadata)} fields")
            
            # Check if value field was properly converted
            if "value" in metadata:
                value = metadata["value"]
                if isinstance(value, (int, float)):
                    verification["diagnostics"].append(f"✅ Value field is correctly stored as a number: {value}")
                else:
                    verification["diagnostics"].append(f"⚠️ Value field is not stored as a number: {value} ({type(value).__name__})")
        else:
            verification["diagnostics"].append("⚠️ No metadata response in result")
    else:
        verification["diagnostics"].append("❌ Metadata application failed")
        
        # Check error message
        if "error" in result:
            error = result["error"]
            verification["diagnostics"].append(f"❌ Error: {error}")
            
            # Check for common error patterns
            if "invalid value" in error.lower() and "value" in error.lower():
                verification["diagnostics"].append("❌ Error indicates value field type mismatch")
                verification["diagnostics"].append("💡 Suggestion: Ensure value field is converted to a number")
            elif "already exists" in error.lower():
                verification["diagnostics"].append("❌ Error indicates metadata already exists")
                verification["diagnostics"].append("💡 Suggestion: Use update operations instead of create")
    
    return verification

def get_file_specific_config(file_id):
    """
    Get the specific metadata configuration for a file.
    
    Args:
        file_id: The ID of the file to get configuration for
        
    Returns:
        Dict containing the file's metadata configuration
    """
    if "file_metadata_config" not in st.session_state:
        return {
            "extraction_method": "structured",
            "template_id": "",
            "custom_prompt": ""
        }
    
    return st.session_state.file_metadata_config.get(file_id, {
        "extraction_method": "structured",
        "template_id": "",
        "custom_prompt": ""
    })
def flatten_metadata_for_template(metadata_values):
    """
    Flatten nested metadata structure for template-based metadata application.
    
    This function extracts fields from the 'answer' object and places them directly
    at the top level, removing non-template fields like 'ai_agent_info', 'created_at',
    and 'completion_reason'.
    
    Args:
        metadata_values (dict): The metadata values to flatten
        
    Returns:
        dict: Flattened metadata with fields at the top level
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Make a copy to avoid modifying the original
    flattened_metadata = {}
    
    # Log the original metadata
    logger.info(f"Original metadata before flattening: {metadata_values}")
    
    # Check if 'answer' field exists and is a dictionary
    if 'answer' in metadata_values and isinstance(metadata_values['answer'], dict):
        # Extract fields from 'answer' and place them at the top level
        for key, value in metadata_values['answer'].items():
            flattened_metadata[key] = value
        logger.info(f"Extracted fields from 'answer' object: {list(flattened_metadata.keys())}")
    else:
        # If no 'answer' field or not a dictionary, use the original metadata
        flattened_metadata = metadata_values.copy()
        logger.info("No 'answer' field found or not a dictionary, using original metadata")
    
    # Remove non-template fields that should not be sent to Box API
    fields_to_remove = ['ai_agent_info', 'created_at', 'completion_reason']
    for field in fields_to_remove:
        if field in flattened_metadata:
            del flattened_metadata[field]
            logger.info(f"Removed non-template field: {field}")
    
    # Log the flattened metadata
    logger.info(f"Flattened metadata: {flattened_metadata}")
    
    return flattened_metadata

def apply_metadata_to_file_enhanced(client, file_id, metadata_values, template_info=None):
    """
    Enhanced function to apply metadata to a file with robust error handling and debugging.
    
    Args:
        client: Box client object
        file_id: File ID to apply metadata to
        metadata_values: Dictionary of metadata values to apply
        template_info: Optional template information with field types
        
    Returns:
        dict: Result of metadata application
    """
    file_name = f"File {file_id}"
    try:
        # Get file object
        file_obj = client.file(file_id=file_id)
        file_name = file_obj.get().name
        
        # Log original metadata values
        logger.info(f"Original metadata values for file {file_name} ({file_id}): {json.dumps(metadata_values, default=str)}")
        
        # Validate and fix metadata fields
        validated_metadata = validate_metadata_fields(metadata_values, template_info)
        
        # Log validated metadata
        logger.info(f"Validated metadata for file {file_name} ({file_id}): {json.dumps(validated_metadata, default=str)}")
        
        # Check if we're using a template
        if template_info:
            scope = template_info.get('scope', 'enterprise')
            enterprise_id = template_info.get('enterprise_id', '')
            template_key = template_info.get('template_key', '')
            
            # Format the scope with enterprise ID
            scope_with_id = f"{scope}_{enterprise_id}" if enterprise_id else scope
            
            logger.info(f"Using template-based metadata application with scope: {scope_with_id}, template: {template_key}")
            
            try:
                # Apply metadata using the template
                metadata = file_obj.metadata(scope_with_id, template_key).create(validated_metadata)
                logger.info(f"Successfully applied template metadata to file {file_name} ({file_id})")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "success": True,
                    "metadata": metadata
                }
            except Exception as e:
                if "already exists" in str(e).lower():
                    # If metadata already exists, update it
                    try:
                        # Create update operations
                        operations = []
                        for key, value in validated_metadata.items():
                            operations.append({
                                "op": "replace",
                                "path": f"/{key}",
                                "value": value
                            })
                        
                        # Update metadata
                        logger.info(f"Template metadata already exists, updating with operations")
                        metadata = file_obj.metadata(scope_with_id, template_key).update(operations)
                        
                        logger.info(f"Successfully updated template metadata for file {file_name} ({file_id})")
                        return {
                            "file_id": file_id,
                            "file_name": file_name,
                            "success": True,
                            "metadata": metadata
                        }
                    except Exception as update_error:
                        logger.error(f"Error updating template metadata for file {file_name} ({file_id}): {str(update_error)}")
                        return {
                            "file_id": file_id,
                            "file_name": file_name,
                            "success": False,
                            "error": f"Error updating template metadata: {str(update_error)}"
                        }
                else:
                    logger.error(f"Error creating template metadata for file {file_name} ({file_id}): {str(e)}")
                    return {
                        "file_id": file_id,
                        "file_name": file_name,
                        "success": False,
                        "error": f"Error creating template metadata: {str(e)}"
                    }
        else:
            # Apply freeform metadata
            try:
                # Apply metadata
                metadata = file_obj.metadata().create(validated_metadata)
                logger.info(f"Successfully applied freeform metadata to file {file_name} ({file_id})")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "success": True,
                    "metadata": metadata
                }
            except Exception as e:
                if "already exists" in str(e).lower():
                    # If metadata already exists, update it
                    try:
                        # Create update operations
                        operations = []
                        for key, value in validated_metadata.items():
                            operations.append({
                                "op": "replace",
                                "path": f"/{key}",
                                "value": value
                            })
                        
                        # Update metadata
                        logger.info(f"Metadata already exists, updating with operations")
                        metadata = file_obj.metadata("global", "properties").update(operations)
                        
                        logger.info(f"Successfully updated metadata for file {file_name} ({file_id})")
                        return {
                            "file_id": file_id,
                            "file_name": file_name,
                            "success": True,
                            "metadata": metadata
                        }
                    except Exception as update_error:
                        logger.error(f"Error updating metadata for file {file_name} ({file_id}): {str(update_error)}")
                        return {
                            "file_id": file_id,
                            "file_name": file_name,
                            "success": False,
                            "error": f"Error updating metadata: {str(update_error)}"
                        }
                else:
                    logger.error(f"Error creating metadata for file {file_name} ({file_id}): {str(e)}")
                    return {
                        "file_id": file_id,
                        "file_name": file_name,
                        "success": False,
                        "error": f"Error creating metadata: {str(e)}"
                    }
    except Exception as e:
        logger.exception(f"Unexpected error applying metadata to file {file_id}: {str(e)}")
        return {
            "file_id": file_id,
            "file_name": file_name,
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

def apply_metadata_direct():
    """
    Direct approach to apply metadata to Box files with comprehensive fixes
    for session state alignment and metadata extraction
    """
    st.title("Apply Metadata")
    
    # Debug checkbox
    debug_mode = st.sidebar.checkbox("Debug Session State", key="debug_checkbox")
    if debug_mode:
        st.sidebar.write("### Session State Debug")
        st.sidebar.write("**Session State Keys:**")
        st.sidebar.write(list(st.session_state.keys()))
        
        if "client" in st.session_state:
            st.sidebar.write("**Client:** Available")
            try:
                user = st.session_state.client.user().get()
                st.sidebar.write(f"**Authenticated as:** {user.name}")
            except Exception as e:
                st.sidebar.write(f"**Client Error:** {str(e)}")
        else:
            st.sidebar.write("**Client:** Not available")
            
        if "processing_state" in st.session_state:
            st.sidebar.write("**Processing State Keys:**")
            st.sidebar.write(list(st.session_state.processing_state.keys()))
            
            # Dump the first processing result for debugging
            if st.session_state.processing_state:
                first_key = next(iter(st.session_state.processing_state))
                st.sidebar.write(f"**First Processing Result ({first_key}):**")
                st.sidebar.json(st.session_state.processing_state[first_key])
    
    # Check if client exists directly
    if 'client' not in st.session_state:
        st.error("Box client not found. Please authenticate first.")
        if st.button("Go to Authentication", key="go_to_auth_btn"):
            st.session_state.current_page = "Home"  # Assuming Home page has authentication
            st.rerun()
        return
    
    # Get client directly
    client = st.session_state.client
    
    # Verify client is working
    try:
        user = client.user().get()
        logger.info(f"Verified client authentication as {user.name}")
        st.success(f"Authenticated as {user.name}")
    except Exception as e:
        logger.error(f"Error verifying client: {str(e)}")
        st.error(f"Authentication error: {str(e)}. Please re-authenticate.")
        if st.button("Go to Authentication", key="go_to_auth_error_btn"):
            st.session_state.current_page = "Home"
            st.rerun()
        return
    
    # Check if processing state exists
    if "processing_state" not in st.session_state or not st.session_state.processing_state:
        st.warning("No processing results available. Please process files first.")
        if st.button("Go to Process Files", key="go_to_process_files_btn"):
            st.session_state.current_page = "Process Files"
            st.rerun()
        return
    
    # Debug the structure of processing_state
    processing_state = st.session_state.processing_state
    logger.info(f"Processing state keys: {list(processing_state.keys())}")
    
    # Add debug dump to sidebar
    st.sidebar.write("🔍 RAW processing_state")
    st.sidebar.json(processing_state)
    
    # Extract file IDs and metadata from processing_state
    available_file_ids = []
    
    # Check if we have any selected files in session state
    if "selected_files" in st.session_state and st.session_state.selected_files:
        selected_files = st.session_state.selected_files
        logger.info(f"Found {len(selected_files)} selected files in session state")
        for file_info in selected_files:
            if isinstance(file_info, dict) and "id" in file_info and file_info["id"]:
                # CRITICAL FIX: Ensure file ID is a string
                file_id = str(file_info["id"])
                file_name = file_info.get("name", "Unknown")
                available_file_ids.append(file_id)
                logger.info(f"Added file ID {file_id} from selected_files")
    
    # Pull out the real per‐file results dict
    results_map = processing_state.get("results", {})
    logger.info(f"Results map keys: {list(results_map.keys())}")
    
    file_id_to_metadata = {}
    file_id_to_file_name = {}
    
    # Initialize file_id_to_file_name from selected_files
    if "selected_files" in st.session_state and st.session_state.selected_files:
        for i, file_info in enumerate(st.session_state.selected_files):
            if isinstance(file_info, dict) and "id" in file_info and file_info["id"]:
                file_id = str(file_info["id"])
                file_id_to_file_name[file_id] = file_info.get("name", f"File {file_id}")
    
    for raw_id, payload in results_map.items():
        file_id = str(raw_id)
        available_file_ids.append(file_id)
        
        # Most APIs put your AI fields under payload["results"]
        metadata = payload.get("results", payload)
        
        # If metadata is a string that looks like JSON, try to parse it
        if isinstance(metadata, str):
            try:
                parsed_metadata = json.loads(metadata)
                if isinstance(parsed_metadata, dict):
                    metadata = parsed_metadata
            except json.JSONDecodeError:
                # Not valid JSON, keep as is
                pass
        
        # If payload has an "answer" field that's a JSON string, parse it
        if isinstance(payload, dict) and "answer" in payload and isinstance(payload["answer"], str):
            try:
                parsed_answer = json.loads(payload["answer"])
                if isinstance(parsed_answer, dict):
                    metadata = parsed_answer
            except json.JSONDecodeError:
                # Not valid JSON, keep as is
                pass
        
        file_id_to_metadata[file_id] = metadata
        logger.info(f"Extracted metadata for {file_id}: {metadata!r}")
    
    # Remove duplicates while preserving order
    available_file_ids = list(dict.fromkeys(available_file_ids))
    
    # Debug logging
    logger.info(f"Available file IDs: {available_file_ids}")
    logger.info(f"File ID to file name mapping: {file_id_to_file_name}")
    logger.info(f"File ID to metadata mapping: {list(file_id_to_metadata.keys())}")
    
    st.write("Apply extracted metadata to your Box files.")
    
    # Display selected files
    st.subheader("Selected Files")
    
    if not available_file_ids:
        st.error("No file IDs available for metadata application. Please process files first.")
        if st.button("Go to Process Files", key="go_to_process_files_error_btn"):
            st.session_state.current_page = "Process Files"
            st.rerun()
        return
    
    st.write(f"You have selected {len(available_file_ids)} files for metadata application.")
    
    with st.expander("View Selected Files"):
        for file_id in available_file_ids:
            file_name = file_id_to_file_name.get(file_id, "Unknown")
            st.write(f"- {file_name} ({file_id})")
    
    # Metadata application options
    st.subheader("Application Options")
    
    # For freeform extraction
    st.write("Freeform extraction results will be applied as properties metadata.")
    
    # Option to normalize keys
    normalize_keys = st.checkbox(
        "Normalize keys",
        value=True,
        help="If checked, keys will be normalized (lowercase, spaces replaced with underscores).",
        key="normalize_keys_checkbox"
    )
    
    # Option to filter placeholder values
    filter_placeholders = st.checkbox(
        "Filter placeholder values",
        value=True,
        help="If checked, placeholder values like 'insert date' will be filtered out.",
        key="filter_placeholders_checkbox"
    )
    
    # Batch size (simplified to just 1)
    st.subheader("Batch Processing Options")
    st.write("Using single file processing for reliability.")
    
    # Operation timeout
    timeout_seconds = st.slider(
        "Operation Timeout (seconds)",
        min_value=10,
        max_value=300,
        value=60,
        help="Maximum time to wait for each operation to complete.",
        key="timeout_slider"
    )
    
    # Apply metadata button
    col1, col2 = st.columns(2)
    
    with col1:
        apply_button = st.button(
            "Apply Metadata",
            use_container_width=True,
            key="apply_metadata_btn"
        )
    
    with col2:
        cancel_button = st.button(
            "Cancel",
            use_container_width=True,
            key="cancel_btn"
        )
    
    # Progress tracking
    progress_container = st.container()
    
    # Function to check if a value is a placeholder
    def is_placeholder(value):
        """Check if a value appears to be a placeholder"""
        if not isinstance(value, str):
            return False
            
        placeholder_indicators = [
            "insert", "placeholder", "<", ">", "[", "]", 
            "enter", "fill in", "your", "example"
        ]
        
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in placeholder_indicators)
    
    # Handle apply button click - DIRECT APPROACH WITHOUT THREADING
    if apply_button:
        # Check if client exists directly again
        if 'client' not in st.session_state:
            st.error("Box client not found. Please authenticate first.")
            return
        
        # Get client directly
        client = st.session_state.client
        
        # Process files one by one
        results = []
        errors = []
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process each file
        for i, file_id in enumerate(available_file_ids):
            file_name = file_id_to_file_name.get(file_id, "Unknown")
            status_text.text(f"Processing {file_name}...")
            
            # Get metadata for this file
            metadata_values = file_id_to_metadata.get(file_id, {})
            
            # CRITICAL FIX: Log the metadata values before application
            logger.info(f"Metadata values for file {file_name} ({file_id}) before application: {json.dumps(metadata_values, default=str)}")
            
            # Get file-specific configuration
            file_config = get_file_specific_config(file_id)
            extraction_method = file_config.get("extraction_method", "structured")
            
            # Apply metadata based on extraction method and configuration
            if extraction_method == "structured" and "metadata_config" in st.session_state:
                # Get template information
                template_id = file_config.get("template_id", "")
                if not template_id and st.session_state.metadata_config.get("use_template"):
                    template_id = st.session_state.metadata_config.get("template_id", "")
                
                if template_id:
                    # Parse the template ID
                    parts = template_id.split('_')
                    scope = parts[0]  # e.g., "enterprise"
                    enterprise_id = parts[1] if len(parts) > 1 else ""
                    template_key = parts[-1] if len(parts) > 2 else template_id
                    
                    # Create template info
                    template_info = {
                        "scope": scope,
                        "enterprise_id": enterprise_id,
                        "template_key": template_key
                    }
                    
                    # Apply metadata with enhanced function
                    result = apply_metadata_to_file_enhanced(client, file_id, metadata_values, template_info)
                else:
                    # No template specified, use freeform
                    result = apply_metadata_to_file_enhanced(client, file_id, metadata_values)
            else:
                # Freeform metadata
                result = apply_metadata_to_file_enhanced(client, file_id, metadata_values)
            
            # Verify the result
            verification = verify_metadata_application(result)
            logger.info(f"Verification result: {json.dumps(verification, default=str)}")
            
            if result["success"]:
                results.append(result)
            else:
                errors.append(result)
            
            # Update progress
            progress = (i + 1) / len(available_file_ids)
            progress_bar.progress(progress)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Show results
        st.subheader("Metadata Application Results")
        st.write(f"Successfully applied metadata to {len(results)} of {len(available_file_ids)} files.")
        
        if errors:
            with st.expander("View Errors"):
                for error in errors:
                    st.write(f"**{error['file_name']}:** {error['error']}")
                    
                    # Add diagnostics for better troubleshooting
                    verification = verify_metadata_application(error)
                    st.write("**Diagnostics:**")
                    for diagnostic in verification["diagnostics"]:
                        st.write(f"- {diagnostic}")
        
        if results:
            with st.expander("View Successful Applications"):
                for result in results:
                    st.write(f"**{result['file_name']}:** Metadata applied successfully")
    
    # Handle cancel button click
    if cancel_button:
        st.warning("Operation cancelled.")
        st.rerun()
