import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pypdf import PdfReader
from google import genai
from google.genai import types
from xhtml2pdf import pisa

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


 
client = genai.Client()

# Set up the Upload Directory safely
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def home():
    return {"message": "AI Resume Analyzer Running"}


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed!")
        
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        reader = PdfReader(file_path)
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
        
        prompt = f"""
        You are an expert ATS (Applicant Tracking System) and HR manager. 
        Analyze this resume text and evaluate it strictly.
        
        Resume Text:
        {extracted_text}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "candidate_name": {"type": "STRING"},
                        "resume_score": {"type": "INTEGER", "description": "Score out of 100"},
                        "summary": {"type": "STRING"},
                        "extracted_skills": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "improvements": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "3 concrete points to improve"}
                    },
                    "required": ["candidate_name", "resume_score", "summary", "extracted_skills", "improvements"]
                }
            )
        )
        
        analysis_data = json.loads(response.text)
        
        return {
            "status": "success",
            "filename": file.filename,
            "data": analysis_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.post("/improve")
async def improve_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed!")
        
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        reader = PdfReader(file_path)
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
        
    
        prompt = f"""
        You are an expert executive resume designer. Rewrite the following resume into a flawless, ATS-optimized layout using clean, standard HTML.
        
        Follow these styling constraints strictly for a professional executive layout:
        1. Do NOT include generic markdown wrapping symbols like ```html or ```. Output ONLY the raw HTML string.
        2. Use a standard professional font-family like 'Times New Roman' or 'Helvetica'.
        3. Structure headings using a clear hierarchy (e.g., h1 for name, h2 for section titles). Give sections an elegant bottom border: border-bottom: 1px solid #333;.
        4. Organize content into standard sections: Contact Info, Professional Summary, Technical Skills, Education, and Projects.
        5. For projects, present descriptive details using proper clean HTML <ul> and <li> tags. Use strong action verbs.
        6. Do NOT add colorful background decorations, multi-column sidebars, or floating elements. Keep it single-column, clean, and highly readable.
        
        Original Resume Text:
        {extracted_text}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
     
        clean_html = response.text.replace("```html", "").replace("```", "").strip()
        
        return {
            "status": "success",
            "perfect_resume_text": clean_html
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate perfect resume: {str(e)}")
        
        
    
@app.post("/download-pdf")
async def download_perfect_resume(data: dict):
   
    html_content = data.get("text", "")
    
    
    styled_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: a4; margin: 20mm 15mm; }}
            body {{ font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.4; color: #111; }}
            h1 {{ text-align: center; font-size: 24pt; margin-bottom: 5px; text-transform: uppercase; }}
            .contact-info {{ text-align: center; font-size: 10pt; margin-bottom: 20px; color: #444; }}
            h2 {{ font-size: 13pt; text-transform: uppercase; border-bottom: 1px solid #222; margin-top: 20px; margin-bottom: 10px; padding-bottom: 2px; }}
            p {{ margin-bottom: 8px; text-align: justify; }}
            ul {{ margin-top: 5px; padding-left: 20px; }}
            li {{ margin-bottom: 5px; text-align: justify; }}
            .project-title {{ font-weight: bold; float: left; }}
            .project-date {{ float: right; text-align: right; }}
            .clear {{ clear: both; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(styled_html.encode("utf-8")), pdf_buffer)
    pdf_buffer.seek(0)
    
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=Perfect_ATS_Resume.pdf"
    })