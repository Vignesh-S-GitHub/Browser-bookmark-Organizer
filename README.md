# 🧠 AI Browser Organizer

![Project Logo](assets/logo.png)

**Effortlessly organize your bookmarks using Google's Gemini AI.**

AI Browser Organizer is a local Python application that automatically detects your Chrome and Edge bookmarks, uses Google's Gemini AI to categorize them into intuitive folders (like "Development", "Shopping", "News"), and exports a clean HTML file you can import back into any browser.

## ✨ Features

- **🔍 Auto-Discovery**: Instantly finds bookmarks from default **Chrome**, **Edge**, **Brave**, and **Firefox** profiles on Windows.
- **🤖 Smart Categorization**: Supports any Gemini model (e.g., 2.5 Flash, 2.5 Pro) to understand context and group links logically.
- **⚡ Batch Processing**: Handles large libraries efficiently with customizable batch sizes.
- **🎨 Beautiful UI**: A modern, dark-mode aesthetic built with Streamlit and custom styling.
- **🔄 Universal Export**: Generates standard Netscape HTML format compatible with all major browsers.
- **🔒 Privacy Focused**: Your bookmarks are processed in-memory and only titles/URLs are sent to the API.

## 🚀 Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/ai-browser-organizer.git
   cd ai-browser-organizer
   ```

2. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the App**:

   ```bash
   streamlit run app.py
   ```

## 🛠️ Usage

1. **Launch**: Open the local URL provided by Streamlit (usually `http://localhost:8501`).
2. **Configure**:
   - Enter your **Gemini API Key** (Get it free from [Google AI Studio](https://aistudio.google.com/)).
   - (Optional) Adjust **Model Name** or **Batch Size** in the sidebar.
3. **Step 1: Scan**: Click the "Scan Browsers" button to load your local bookmarks.
4. **Step 2: Organize**: Click "Start AI Magic". Sit back while the AI processes your links.
5. **Step 3: Export**: Download the organized HTML file.
6. **Import**: Go to your browser's "Import Bookmarks" setting and select the downloaded file.

## 📦 Requirements

- Python 3.8+
- Windows (for automatic path detection)
- `streamlit`
- `google-generativeai`
- `beautifulsoup4`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open-source and available under the MIT License.
