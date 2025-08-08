from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def admin_root():
    return {"message": "Admin routes placeholder"}
EOF < /dev/null
