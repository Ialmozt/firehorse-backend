import os
import subprocess
import sys

# Read credentials from .env
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value

# Get database credentials
db_host = env_vars.get('DATABASE_HOST', 'aws-0-eu-west-1.pooler.supabase.com')
db_port = env_vars.get('DATABASE_PORT', '5432')
db_name = env_vars.get('DATABASE_NAME', 'postgres')
db_user = env_vars.get('DATABASE_USER', 'postgres.yommcknuizxkwpmpvlmp')
db_password = env_vars.get('DATABASE_PASSWORD', 'bkOFQ9jiln6JE82v')

# Build connection string
conn_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"

print(f"Connecting to: {db_host}:{db_port}")
print(f"Database: {db_name}")
print(f"User: {db_user}")

# Read SQL file
with open('create_fh_ingress.sql', 'r') as f:
    sql = f.read()

# Try to execute via psql
try:
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    cmd = ['psql', conn_str, '-c', sql]
    print(f"Executing: psql {db_host}:{db_port}/{db_name}")
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
    
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
    
    if result.returncode == 0:
        print("✅ SQL executed successfully!")
    else:
        print("❌ SQL execution failed")
        
except subprocess.TimeoutExpired:
    print("❌ Command timed out")
except Exception as e:
    print(f"❌ Error: {e}")
