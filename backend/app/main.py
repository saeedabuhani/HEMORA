from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api import router
from .config import settings
from .limiting import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

app=FastAPI(title="HEMORA API",version="1.0.0",description="Explainable, deterministic blood-test tracking API")
app.state.limiter=limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["GET","POST","PATCH","PUT","DELETE"],allow_headers=["Authorization","Content-Type"])
@app.middleware("http")
async def security_headers(request:Request,call_next):
    response=await call_next(request); response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Permissions-Policy":"camera=(), microphone=(), geolocation=()"}); return response
@app.exception_handler(Exception)
async def unexpected_error(request,exc): return JSONResponse(status_code=500,content={"code":"INTERNAL_ERROR","message":"אירעה שגיאה בלתי צפויה. נסו שוב.","details":{}})
@app.get("/health")
def health(): return {"status":"ok","service":"HEMORA","algorithm":"HEMORA-CLINICAL-1.0.0"}
app.include_router(router)
from .management import router as management_router
app.include_router(management_router)
