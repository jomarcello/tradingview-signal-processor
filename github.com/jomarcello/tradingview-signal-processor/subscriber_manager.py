from supabase import create_client
import os

def find_subscribers(signal):
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    return supabase.table('subscribers').select('*').execute() 