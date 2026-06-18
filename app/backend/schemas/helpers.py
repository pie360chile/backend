from pydantic import BaseModel, Field, EmailStr, validator, field_validator, ConfigDict, AliasChoices
from typing import Union, List, Dict, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
import json


def _empty_str_to_none(v: Any) -> Any:
    """Convierte cadena vacía a None para campos opcionales."""
    if v == "" or (isinstance(v, str) and not v.strip()):
        return None
    return v


# Authentication schemas
