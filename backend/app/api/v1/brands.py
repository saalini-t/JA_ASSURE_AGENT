from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.brand.registry import list_brands, get_brand

router = APIRouter(prefix="/brands", tags=["Brands"])

@router.get("")
def get_all_brands():
    """
    Returns list of all supported JA Assure brand identities with Brand DNA.
    """
    return list_brands()

@router.get("/{brand_id}")
def get_single_brand_info(brand_id: str):
    """
    Returns single brand DNA details.
    """
    try:
        return get_brand(brand_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
