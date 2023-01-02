from flask_login import UserMixin
from typing import Dict, Optional
from pyairtable.formulas import match
from app import AT

users: Dict[str, "User"] = {}

class User(UserMixin):
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    @staticmethod
    def get(user_id: str) -> Optional["User"]:
        return users.get(user_id)

    def __str__(self) -> str:
        return f"<Name: {self.name}>"

    def __repr__(self) -> str:
        return self.__str__()

for user in AT["people"].all(fields=["Name"]):
    if "Name" in user['fields']:
        name = user['fields']['Name']
    else:
        name = None
    users[user['id']] = User(
        id = user['id'],
        name = name
    )
