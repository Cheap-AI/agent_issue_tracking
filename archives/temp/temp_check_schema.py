import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"), override=True)

from sqlalchemy import create_engine, text, inspect

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:Tkfkdgo121231!!!!@db.euhafvxclmmzkmexbcyf.supabase.co:5432/postgres")
engine = create_engine(db_url)

inspector = inspect(engine)

print("=== Database Schema Check ===")
print(f"Database URL: {db_url.split('@')[1] if '@' in db_url else db_url}")

# Check alembic version
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    alembic_version = result.fetchone()[0]
    print(f"\nAlembic version: {alembic_version}")

# Check tables
tables = inspector.get_table_names(schema="public")
print(f"\nTables in public schema: {tables}")

# Check issues table
print("\n=== Issues Table ===")
if "issues" in tables:
    columns = inspector.get_columns("issues", schema="public")
    for col in columns:
        print(f"  {col['name']}: {col['type']} (nullable={col['nullable']}, default={col.get('default', None)})")
    
    # Check constraints
    constraints = inspector.get_unique_constraints("issues", schema="public")
    for const in constraints:
        print(f"  Unique constraint: {const['name']} on {const['column_names']}")
    
    # Check indexes
    indexes = inspector.get_indexes("issues", schema="public")
    for idx in indexes:
        print(f"  Index: {idx['name']} on {idx['column_names']} (unique={idx['unique']})")

# Check components table
print("\n=== Components Table ===")
if "components" in tables:
    columns = inspector.get_columns("components", schema="public")
    for col in columns:
        print(f"  {col['name']}: {col['type']} (nullable={col['nullable']}, default={col.get('default', None)})")
    
    # Check foreign keys
    fks = inspector.get_foreign_keys("components", schema="public")
    for fk in fks:
        print(f"  Foreign key: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
    
    # Check constraints
    constraints = inspector.get_unique_constraints("components", schema="public")
    for const in constraints:
        print(f"  Unique constraint: {const['name']} on {const['column_names']}")
    
    # Check check constraints
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'components'::regclass AND contype = 'c'
        """))
        for row in result.fetchall():
            print(f"  Check constraint: {row[0]} - {row[1]}")

# Check global_docs table
print("\n=== Global Docs Table ===")
if "global_docs" in tables:
    columns = inspector.get_columns("global_docs", schema="public")
    for col in columns:
        print(f"  {col['name']}: {col['type']} (nullable={col['nullable']}, default={col.get('default', None)})")

# Compare with ORM models
print("\n=== ORM Model Comparison ===")
print("Issues table should have columns:")
print("  id: String (primary_key)")
print("  title: Text (nullable=False)")
print("  summary: Text (nullable=False, default='')")
print("  is_active: Boolean (nullable=False, default=True)")
print("  created_at: DateTime(timezone=True) (nullable=False, server_default=func.now())")

print("\nComponents table should have columns:")
print("  id: BigInteger (primary_key, autoincrement=True)")
print("  issue_id: String (ForeignKey('issues.id', ondelete='CASCADE'), nullable=False)")
print("  component_type: Text (nullable=False)")
print("  version: Integer (nullable=False)")
print("  content: Text (nullable=False)")
print("  created_at: DateTime(timezone=True) (nullable=False, server_default=func.now())")
print("  UniqueConstraint('issue_id', 'component_type', 'version')")
print("  CheckConstraint(\"component_type IN ('research', 'summary', 'timeline', 'sources', 'questions')\")")

print("\nGlobalDocs table should have columns:")
print("  name: String (primary_key)")
print("  content: Text (nullable=False, default='')")
print("  updated_at: DateTime(timezone=True) (nullable=False, server_default=func.now(), onupdate=func.now())")

# Test create_issue function
print("\n=== Testing create_issue function ===")
try:
    from backend.core.issue import create_issue
    print("create_issue function exists and can be imported")
    
    # Check if function matches schema
    import inspect as py_inspect
    sig = py_inspect.signature(create_issue)
    print(f"create_issue signature: {sig}")
    print(f"Parameters: {list(sig.parameters.keys())}")
    
except Exception as e:
    print(f"Error importing create_issue: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Schema Validation ===")
# Validate that the ORM models match the actual schema
with engine.connect() as conn:
    # Check if sequence exists
    result = conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'issue_id_seq')"))
    seq_exists = result.fetchone()[0]
    print(f"Sequence 'issue_id_seq' exists: {seq_exists}")
    
    # Check current value of sequence
    if seq_exists:
        result = conn.execute(text("SELECT last_value FROM issue_id_seq"))
        last_val = result.fetchone()[0]
        print(f"Sequence last_value: {last_val}")