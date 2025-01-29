# Startup Validator using Reddit Data 

This is a RAG application that is designed to validate user startup idea or even solve queries with respect to startup based on the reddit user expierence .

## Project Structure

```
legacy
├── 
├── app.py          # Main entry point of the Streamlit application
├── rag.py          # Logic for loading documents and retrieval chain
└── types
│   └── index.py    # Custom types and interfaces
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vish0290/Startup-validator.git
   cd legacy
   ```

2. **Install dependencies:**
   Make sure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   Execute the following command to start the Streamlit application:
   ```bash
   streamlit run app.py
   ```

## Usage

- Open your web browser and navigate to `http://localhost:8501` to access the application.
- Enter your question in the input field and submit to receive an answer based on the provided context.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes. 

## License

This project is licensed under the MIT License.