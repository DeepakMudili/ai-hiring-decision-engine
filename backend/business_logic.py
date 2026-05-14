import fitz
import hashlib
import re
import json
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
    max_tokens=800
)


resume_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a strict AI hiring evaluator. Always return valid JSON only."
    ),
    (
        "human",
        """
Compare this resume with the job description.

Return ONLY valid JSON in this exact format:

{{
  "score": 0,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "feedback": "short recruiter-facing explanation",
  "candidate_summary": "short candidate summary"
}}

Rules:
- score must be from 0 to 50
- matched_skills must be skills clearly found in resume
- missing_skills must be important job skills missing from resume
- never include same skill in both matched_skills and missing_skills
- feedback must be short and professional
- no markdown
- no extra text

Job Description:
{job_description}

Resume:
{resume_text}
"""
    )
])


resume_chain = resume_prompt | llm


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed_password):
    return hashlib.sha256(password.encode()).hexdigest() == hashed_password


def extract_pdf_text(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    text = ""

    for page in doc:
        text += page.get_text()

    return text


def extract_json_from_text(text):
    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return None


def clean_skill_list(skills):
    if not isinstance(skills, list):
        return []

    cleaned = []

    for skill in skills:
        if not isinstance(skill, str):
            continue

        skill = skill.strip()

        if skill and skill.lower() not in [s.lower() for s in cleaned]:
            cleaned.append(skill)

    return cleaned


def remove_duplicate_missing_skills(matched_skills, missing_skills):
    matched_lower = [skill.lower() for skill in matched_skills]

    return [
        skill for skill in missing_skills
        if skill.lower() not in matched_lower
    ]


def calculate_resume_ai_analysis(resume_text, job_description):

    try:
        response = resume_chain.invoke({
            "job_description": job_description,
            "resume_text": resume_text[:6000]
        })

        data = extract_json_from_text(response.content)

        if not data:
            raise ValueError("Invalid AI response")

        score = int(data.get("score", 25))
        score = max(0, min(score, 50))

        matched_skills = clean_skill_list(data.get("matched_skills", []))
        missing_skills = clean_skill_list(data.get("missing_skills", []))

        missing_skills = remove_duplicate_missing_skills(
            matched_skills,
            missing_skills
        )

        feedback = data.get("feedback", "AI feedback not available.")
        candidate_summary = data.get(
            "candidate_summary",
            "Candidate summary not available."
        )

        return {
            "score": score,
            "matched_skills": ", ".join(matched_skills),
            "missing_skills": ", ".join(missing_skills),
            "feedback": feedback,
            "candidate_summary": candidate_summary
        }

    except Exception:
        return fallback_resume_analysis(resume_text, job_description)


def fallback_resume_analysis(resume_text, job_description):
    resume_text_lower = resume_text.lower()
    job_description_lower = job_description.lower()

    keywords = re.findall(r'\b[a-zA-Z]{3,}\b', job_description_lower)
    keywords = list(set(keywords))

    matched = [
        word for word in keywords
        if word in resume_text_lower
    ]

    missing = [
        word for word in keywords
        if word not in resume_text_lower
    ]

    score = int((len(matched) / len(keywords)) * 50) if keywords else 0
    score = max(0, min(score, 50))

    return {
        "score": score,
        "matched_skills": ", ".join(matched[:15]),
        "missing_skills": ", ".join(missing[:15]),
        "feedback": "Fallback keyword-based analysis used.",
        "candidate_summary": "Candidate summary unavailable in fallback mode."
    }


def generate_interview_questions(resume_text, job_description):
    prompt = f"""
Generate interview questions based on the resume and job description.

Return:
1. 5 technical questions
2. 3 project-based questions
3. 3 missing-skill questions
4. 2 behavioral questions

Keep it clean and recruiter-friendly.

Job Description:
{job_description}

Resume:
{resume_text[:5000]}
"""

    try:
        response = llm.invoke(prompt)
        return response.content

    except Exception:
        return "Unable to generate interview questions right now."


def calculate_final_score(resume_score, interview_score):
    try:
        resume_score = int(resume_score)
        interview_score = int(interview_score)

    except:
        return None, "Invalid Score"

    if resume_score < 0 or resume_score > 50:
        return None, "Invalid Score"

    if interview_score < 0 or interview_score > 50:
        return None, "Invalid Score"

    final_score = resume_score + interview_score

    if final_score >= 80:
        status = "Selected"

    elif final_score >= 65:
        status = "On Hold"

    else:
        status = "Rejected"

    return final_score, status

def recruiter_copilot_answer(question, context):
    prompt = f"""
You are an AI Recruiter Copilot.

Answer the recruiter's question using only the provided hiring data.

Be clear, short, and professional.

Recruiter Question:
{question}

Hiring Data:
{context}
"""

    try:
        response = llm.invoke(prompt)
        return response.content

    except Exception:
        return "AI Recruiter Copilot is unavailable right now."