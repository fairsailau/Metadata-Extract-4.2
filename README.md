# Box AI Metadata - Enhanced Version

This is an enhanced version of the Box AI Metadata application with fixes for structured metadata application and support for per-file metadata configuration.

## Key Enhancements

1. **Fixed Structured Metadata Application**: Resolved issues with applying structured metadata to Box files by properly converting field types to match template requirements.

2. **Per-File Metadata Configuration**: Added support for configuring different extraction methods and templates for each file individually.

3. **Robust Error Handling**: Improved error handling and logging for better troubleshooting.

4. **Field Type Validation**: Added comprehensive field type validation to ensure metadata values match template requirements.

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   streamlit run app.py
   ```

## Usage

1. **Authentication**: Log in to your Box account to access your files.

2. **File Selection**: Browse your Box files and select individual files or entire folders for processing.

3. **Document Categorization**: Categorize your documents using Box AI to identify document types.

4. **Metadata Configuration**: Configure how metadata will be extracted from your files.
   - You can now configure different extraction methods for each file
   - Choose between structured (template-based) or freeform extraction for each file

5. **Process Files**: Extract metadata from your files using Box AI.

6. **Review Results**: Review the extracted metadata and make any necessary adjustments.

7. **Apply Metadata**: Apply the extracted metadata to your Box files.

## Troubleshooting

If you encounter issues with metadata application:

1. Check the logs for detailed error messages
2. Verify that the template fields match the expected types
3. Ensure that numeric fields are properly formatted as numbers

## Credits

Developed by the Box AI Metadata team.
