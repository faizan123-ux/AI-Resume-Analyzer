# AI Resume Analyzer & ATS Optimizer 📄🤖

A Full-Stack AI application that parses PDF resumes, calculates an ATS match score, provides deep structural feedback, and generates a flawless, print-ready ATS-optimized resume with a live visual dashboard preview.

## 🚀 Features
- **PDF Text Parsing:** Extracts unstructured text layout from raw binary PDF streams.
- **AI Analysis Core:** Evaluates resume quality and returns structured JSON metrics using `gemini-2.5-flash`.
- **ATS Optimization Engine:** Reconstructs weak resume points into a high-impact, single-column executive structure.
- **Live Preview Window:** Interactive visual interface using an isolated sandboxed iframe.
- **On-the-Fly PDF Stream Rendering:** Instantly compiles and downloads structured PDF documents via `xhtml2pdf`.

## 🛠️ Tech Stack
- **Backend:** FastAPI, Python, Uvicorn, PyPDF, Google GenAI SDK, xhtml2pdf
- **Frontend:** Semantic HTML5, CSS3 Grid/Flexbox, JavaScript (Vanilla Async/Fetch API)

## 🔧 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/AI-Resume-Analyzer.git](https://github.com/YOUR_USERNAME/AI-Resume-Analyzer.git)
   cd AI-Resume-Analyzer