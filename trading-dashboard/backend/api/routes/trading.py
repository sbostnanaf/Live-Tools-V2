from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def trading_root():
    return {"message": "Trading routes placeholder"}
EOF < /dev/null
