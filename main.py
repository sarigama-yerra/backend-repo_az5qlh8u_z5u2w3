import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from database import create_document, db
from schemas import Lead

app = FastAPI(title="Elegance Glazing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static folder for uploads
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def read_root():
    return {"message": "Elegance Glazing backend ready"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": os.getenv("DATABASE_NAME") or "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


class LeadCreateResponse(BaseModel):
    id: str
    status: str = "received"


def send_confirmation_email(email: Optional[str], name: Optional[str]):
    if not email:
        return
    # Best-effort email via SMTP if env provided; otherwise simulate
    import smtplib
    from email.mime.text import MIMEText

    subject = "Thanks for your enquiry – Elegance Glazing"
    body = (
        f"Hi {name or ''}\n\n"
        "Thanks for getting in touch with Elegance Glazing. A specialist will review your details "
        "and contact you shortly. If you need anything urgent, reply to this email or call us.\n\n"
        "Kind regards,\nElegance Glazing"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_FROM", "no-reply@eleganceglazing.local")
    msg["To"] = email

    host = os.getenv("EMAIL_HOST")
    port = int(os.getenv("EMAIL_PORT", "0") or 0)
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    use_tls = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

    if not host or not port:
        # Simulate send in logs
        print(f"[Email] Simulated send to {email}: {subject}")
        return

    try:
        server = smtplib.SMTP(host, port, timeout=10)
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(msg["From"], [email], msg.as_string())
        server.quit()
        print(f"[Email] Sent confirmation to {email}")
    except Exception as e:
        print(f"[Email] Failed to send: {e}")


@app.post("/leads", response_model=LeadCreateResponse)
async def create_lead(
    background_tasks: BackgroundTasks,
    name: str = Form(None),
    email: Optional[EmailStr] = Form(None),
    phone: Optional[str] = Form(None),
    postcode: Optional[str] = Form(None),
    project_type: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    source: Optional[str] = Form("website"),
    files: Optional[List[UploadFile]] = File(None),
):
    file_infos: List[dict] = []
    if files:
        for f in files:
            safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{f.filename}"
            dest_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(dest_path, "wb") as out:
                out.write(await f.read())
            file_infos.append({
                "filename": f.filename,
                "stored_as": safe_name,
                "url": f"/uploads/{safe_name}",
                "content_type": f.content_type,
                "size": os.path.getsize(dest_path),
            })

    lead_doc = Lead(
        name=name or "",
        email=email,
        phone=phone,
        postcode=postcode,
        project_type=project_type,
        message=message,
        source=source,
        files=file_infos or None,
    )

    inserted_id = create_document("lead", lead_doc)

    # Send confirmation email in background
    background_tasks.add_task(send_confirmation_email, email, name)

    return LeadCreateResponse(id=inserted_id)


@app.get("/leads")
def list_leads(limit: int = 20):
    if db is None:
        return {"error": "Database not configured"}
    docs = db["lead"].find().sort("created_at", -1).limit(limit)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(d)
    return {"items": out}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
