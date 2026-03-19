from flask import Blueprint
from .helpers import get_meta, get_airtable

AT = get_airtable()

META = get_meta()

wedding = Blueprint(
    "wedding", 
    __name__
)
auth = Blueprint('auth', __name__)

from . import routes