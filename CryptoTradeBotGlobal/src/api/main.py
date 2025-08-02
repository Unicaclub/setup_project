from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import usuarios, planos, assinaturas, tenants, auth, stripe_webhook

app = FastAPI(title="CryptoTradeBotGlobal SaaS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(planos.router)
app.include_router(assinaturas.router)
app.include_router(tenants.router)
app.include_router(stripe_webhook.router)

@app.get("/")
def root():
    return {"msg": "CryptoTradeBotGlobal SaaS API Fase 5 SUPREMA"}
