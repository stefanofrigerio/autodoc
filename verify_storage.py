from storage import get_catalog, NAMESPACE, TABLE_NAME, get_cv_schema
import pyarrow as pa
from datetime import datetime
import uuid

def test_storage():
    print("Loading catalog...")
    catalog = get_catalog()
    identifier = f"{NAMESPACE}.{TABLE_NAME}"
    
    try:
        table = catalog.load_table(identifier)
        print(f"Table loaded: {table}")
    except Exception as e:
        print(f"Table not found, ensuring handling: {e}")
        return

    # Create a dummy record matching EXACTLY the structure in save_cv_data
    record = {
        "id": str(uuid.uuid4()),
        "filename": "debug_test.txt",
        "ingestion_timestamp": datetime.now(),
        "first_name": "Debug",
        "last_name": "User",
        "email": "debug@example.com",
        "phone": "123",
        "summary": "Debug summary",
        "skills": ["DebugSkill"],
        "work_experience": [],
        "education": []
    }
    
    print("Creating Arrow table...")
    arrow_table = pa.Table.from_pylist([record])
    print(f"Arrow Schema: {arrow_table.schema}")
    
    print("Appending to Iceberg...")
    try:
        table.append(arrow_table)
        print("Append successful.")
    except Exception as e:
        print(f"Append FAILED: {e}")
        # Print schema diff if possible
        print(f"Iceberg Schema: {table.schema()}")

    print("Reading back...")
    try:
        scan = table.scan()
        read_table = scan.to_arrow()
        print(f"Rows read: {len(read_table)}")
        print(read_table)
    except Exception as e:
        print(f"Read FAILED: {e}")

if __name__ == "__main__":
    test_storage()
