from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def dashboard_root():
    return {"message": "Dashboard routes placeholder"}
EOF < /dev/null
