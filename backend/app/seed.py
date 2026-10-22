from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.database import client, database
from app.utils.security import hash_password

email = settings.erp_seed_admin_email.strip().lower()
password = settings.erp_seed_admin_password
if len(password) < 12:
    raise SystemExit("Set ERP_SEED_ADMIN_PASSWORD to a unique password of at least 12 characters before seeding.")

try:
    database.users.insert_one(
        {
            "_id": "admin-" + email,
            "email": email,
            "name": "ERP Administrator",
            "role": "admin",
            "password_hash": hash_password(password),
            "active": True,
        }
    )
    print(f"Created administrator account for {email}")
except DuplicateKeyError:
    print(f"Administrator account already exists for {email}; no data was changed")
finally:
    client.close()
