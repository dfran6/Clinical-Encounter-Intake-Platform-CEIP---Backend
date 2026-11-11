from sqlmodel import SQLModel
from src.models.main_model import (
    User,
    Tenant,
    Encounter,
    ClinicalNote,
    AuditLog,
    Patient,
)


metadata = SQLModel.metadata



#i used this file to reduce 
# the number of model importation on the env.py file
#so no need to import a model to the env.py itll be gotten from here
#to prvent this: from src.db.models import User
