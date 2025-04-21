# Box AI Metadata Extraction and Application Tool

This application allows you to extract metadata from Box files using Box AI and apply it back to the files as metadata.

## Updates in this version

### Fixed Structured Metadata Application
- Fixed an issue where structured metadata application was failing with 400 errors
- Added proper parsing of string representations of dictionaries into actual Python dictionaries
- Structured metadata is now correctly formatted before being sent to the Box API
- Freeform metadata application continues to work as before

## Features

- Authentication with Box
- File selection from Box
- Document categorization using Box AI
- Metadata extraction using Box AI
- Metadata configuration
- Direct metadata application to Box files
- Results viewer

## Requirements

- Python 3.8+
- Streamlit
- Box SDK
- Other dependencies listed in requirements.txt

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `streamlit run app.py`

## Usage

1. Authenticate with Box
2. Select files from Box
3. Configure metadata extraction
4. Process files to extract metadata
5. Review extracted metadata
6. Apply metadata back to Box files

## Implementation Details

The application uses Box AI to extract metadata from files and then applies it back to the files using Box's metadata API. It supports both freeform and structured metadata extraction and application.

## License

See the LICENSE file for details.
