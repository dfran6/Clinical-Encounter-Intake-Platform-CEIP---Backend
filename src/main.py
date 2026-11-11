from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.core.startup import ensure_superadmin
from src.modules.Analytics.routes import analytics_router
from src.modules.Audit.routes import audit_router
from src.modules.Auth.routes import auth_router
from src.modules.Tenants.routes import tenant_router 
from src.modules.Users.routes import user_router
from src.modules.Patients.routes import patient_router
from src.modules.Encounters.routes import encounter_router
from src.modules.ClinicalNotes.routes import encounter_note_router
from src.core.middleware import register_middleware

version = "v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_superadmin()
    yield


app = FastAPI(
    title= "Clinical Encounter Intake Platform Service(CEIPS)",
    description=" Capturing structured clinical data from messy inputs, with strict multi-tenent/RBAC boundaries",
    summary="A backend system that ingests patient encounter data (synthetic, for privacy), extracts structured clinical fields from semi-structured notes, and serves it through a secure, multi-tenant, role-based API",
    version= version,
    lifespan=lifespan,
)

register_middleware(app)

@app.get("/",tags=["Welcome"])
async def welcome():
    return {
        "detail":"Welcome to Clinical Encounter Intake Platform Service (CEIPs)",
        "summary":" A backend system that ingests patient encounter data (synthetic, for privacy), extracts structured clinical fields from semi-structured notes, and serves it through a secure, multi-tenant, role-based API",
        "Developed_by":"Awulor Chukwudi Francis"
        }



app.include_router(auth_router,prefix=f"/api/{version}/auth", tags=["Auth"])
app.include_router(user_router,prefix=f"/api/{version}/users", tags=["Users"])
app.include_router(audit_router,prefix=f"/api/{version}/audit-logs", tags=["Audit Logs"])
app.include_router(tenant_router,prefix=f"/api/{version}/tenants", tags=["Tenants"])
app.include_router(patient_router,prefix=f"/api/{version}/patients", tags=["Patients"])
app.include_router(encounter_router,prefix=f"/api/{version}", tags=["Encounters"])
app.include_router(encounter_note_router,prefix=f"/api/{version}", tags=["Clinical Notes"])
app.include_router(analytics_router,prefix=f"/api/{version}/analytics", tags=["Analytics"])
    
