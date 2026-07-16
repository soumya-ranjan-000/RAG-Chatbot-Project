import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(".env")
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
# Alter table requires SQL which supabase python client RPC can't do directly without a function.
# But wait, we can just use the python supabase client to insert a record, but we can't alter tables.
