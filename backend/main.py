import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Any, Optional
from dotenv import load_dotenv
import pdfplumber 
from google import genai
from google.genai import types
from xhtml2pdf import pisa


# --- ഇംപോർട്ടുകൾ ഈ രീതിയിൽ മാത്രം നൽകുക ---
import models 
import security
from database import engine, get_db

# ബാക്കി നിങ്ങളുടെ മുഴുവൻ കോഡും (FastAPI അപ്ലിക്കേഷൻ ഫംഗ്ഷനുകൾ) താഴേക്ക് അതേപടി തുടരുക...

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI(title="AI Universal Resume Builder & Analyzer")

models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security_jwt = HTTPBearer()
client = genai.Client()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)



class CreateFromScratchInput(BaseModel):
    name: Any
    email: Any
    phone: Any
    linkedin: Optional[Any] = "None"
    github: Optional[Any] = "None"
    portfolio_link: Optional[Any] = "None"
    target_domain: Optional[Any] = "Software Engineering"
    career_objective: Optional[Any] = "None"
    institution_name: Optional[Any] = "None"
    university: Optional[Any] = "None"
    year_of_passing: Optional[Any] = "None"
    percentage_or_cgpa: Optional[Any] = "None"
    skills: Optional[Any] = "None"
    soft_skills: Optional[Any] = "None"
    experience_or_projects: Optional[Any] = "None"
    certifications: Optional[Any] = "None"
    achievements: Optional[Any] = "None"
    positions_of_responsibility: Optional[Any] = "None"
    languages: Optional[Any] = "None"

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GeminiResumeResponse(BaseModel):
    html: str
    score: int
    suggestions: list[str]


@app.get("/")
def home():
    return {"message": "AI Resume Analyzer Running"}




@app.post("/auth/signup")
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = security.hash_password(user_data.password)
    new_user = models.User(email=user_data.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}


@app.post("/auth/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid Email or Password")
    
    if not security.verify_password(user_data.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid Email or Password")
    
    access_token = security.create_access_token(data={"sub": db_user.email, "user_id": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}



@app.post("/audit")
@app.post("/audit-resume")
async def audit_resume(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security_jwt)
):
    payload = security.verify_access_token(token.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    current_user_id = payload.get("user_id")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed!")

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        extracted_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"

        if not extracted_text.strip():
            extracted_text = "Please generate a professional standard resume template for an Engineer."

        improve_prompt = f"""
        You are an expert executive resume designer. 
        Analyze the original resume text provided below. Perform the following steps:
        1. Rewrite the resume into a flawless, ATS-optimized professional layout using clean, standard HTML tags inside body.
        2. Evaluate the original resume text and calculate an ATS optimization score out of 100 based on keywords, layout structure, and typical professional gaps.
        3. Provide actionable suggestions for improvements as a list of strings.

        Original Resume Content:
        {extracted_text}
        """
        
        try:
            response_improve = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=improve_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiResumeResponse,
                ),
            )
            
            result_data = json.loads(response_improve.text.strip())
            perfect_html = result_data.get("html", "")
            final_ats_score = result_data.get("score", 70)
            ai_suggestions = result_data.get("suggestions", ["Structure optimized by AI"])
            
        except Exception as gemini_err:
            # --- 🌟 ബാക്കെൻഡിൽ കൃത്യമായ UNAVAILABLE എറർ ഹാൻഡ്‌ലിങ് നൽകുന്നു 🌟 ---
            raise HTTPException(
                status_code=503, 
                detail=f"Gemini AI temporary traffic spike: SERVICE_UNAVAILABLE. {str(gemini_err)}"
            )
        
        new_resume = models.Resume(
            user_id=current_user_id,
            domain="Uploaded & Improved Profile",
            raw_text=perfect_html, 
            structured_json={"candidate_name": "Candidate"}
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)
        
        return {
            "resume_id": new_resume.id,
            "ats_score": final_ats_score,  
            "perfect_resume_text": perfect_html,
            "parsed_data": {
                "name": "Candidate Profile",
                "career_objective": "ATS-Optimized Executive Summary",
                "skills": []
            },
            "suggestions": ai_suggestions 
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File Processing Error: {str(e)}")



@app.post("/create-from-scratch")
def create_resume_from_scratch(
    input_data: CreateFromScratchInput,
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security_jwt)
):
    payload = security.verify_access_token(token.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    current_user_id = payload.get("user_id")

    try:
        def clean_val(val):
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val else "None"

        prompt = f"""
        You are an expert executive resume designer. Generate an ATS-optimized professional resume using clean HTML elements inside body.
        Do NOT include markdown wrapping symbols like ```html or ```. Output ONLY raw HTML elements.
        
        Data:
        Name: {clean_val(input_data.name)}, Email: {clean_val(input_data.email)}, Phone: {clean_val(input_data.phone)}
        Links: LinkedIn: {clean_val(input_data.linkedin)}, GitHub: {clean_val(input_data.github)}, Portfolio: {clean_val(input_data.portfolio_link)}
        Objective: {clean_val(input_data.career_objective)}
        Education: {clean_val(input_data.institution_name)} ({clean_val(input_data.university)}), Year: {clean_val(input_data.year_of_passing)}, Score: {clean_val(input_data.percentage_or_cgpa)}
        Skills: {clean_val(input_data.skills)}, Soft Skills: {clean_val(input_data.soft_skills)}, Languages: {clean_val(input_data.languages)}
        Experience/Projects: {clean_val(input_data.experience_or_projects)}
        """
        
        try:
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            clean_html = response.text.replace("```html", "").replace("```", "").strip()
        except Exception as gemini_err:
          
            raise HTTPException(
                status_code=503, 
                detail=f"Gemini AI temporary traffic spike: SERVICE_UNAVAILABLE. {str(gemini_err)}"
            )
        
        new_resume = models.Resume(
            user_id=current_user_id,
            domain=str(input_data.target_domain or "Scratch Built"),
            raw_text=clean_html,  
            structured_json={"name": str(input_data.name)}
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)

        return {
            "message": "Fresh optimized resume profile created from scratch!",
            "resume_id": new_resume.id,
            "perfect_resume_text": clean_html
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")




@app.get("/download-pdf")
@app.post("/download-pdf")
async def download_perfect_resume(
    resume_id: Optional[int] = Query(None),
    x: Optional[int] = Query(None),  
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    target_id = resume_id if resume_id is not None else x
    if not target_id:
        raise HTTPException(status_code=422, detail="Missing resume id (resume_id or x)")

    resume = db.query(models.Resume).filter(models.Resume.id == target_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume data not found in Database")

    html_content = resume.raw_text

    styled_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: a4; margin: 20mm 15mm; }}
            body {{ font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.4; color: #111; }}
            h1 {{ text-align: center; font-size: 24pt; margin-bottom: 5px; text-transform: uppercase; font-weight: bold; }}
            h2 {{ font-size: 13pt; text-transform: uppercase; border-bottom: 1px solid #222; margin-top: 18px; margin-bottom: 8px; padding-bottom: 2px; font-weight: bold; }}
            p {{ margin-bottom: 6px; text-align: justify; }}
            ul {{ margin-top: 4px; padding-left: 20px; }}
            li {{ margin-bottom: 4px; text-align: justify; }}
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
        "Content-Disposition": f"attachment; filename=Perfect_Resume_{target_id}.pdf",
        "Access-Control-Expose-Headers": "Content-Disposition"
    })
