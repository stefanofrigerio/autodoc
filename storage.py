import os
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField,
    StringType,
    ListType,
    StructType,
    TimestampType
)
import pyarrow as pa
from datetime import datetime
import models
from models import CVData
import uuid
import typing

# Configuration
CATALOG_NAME = "default"
WAREHOUSE_PATH = os.path.abspath("warehouse")
DB_PATH = f"sqlite:///{WAREHOUSE_PATH}/catalog.db"
NAMESPACE = "autodoc"
TABLE_NAME = "cv_analysis"

def get_catalog():
    """
    Initializes and returns the PyIceberg catalog.
    Uses SQLite for metadata and local filesystem for data.
    """
    if not os.path.exists(WAREHOUSE_PATH):
        os.makedirs(WAREHOUSE_PATH)

    catalog = load_catalog(
        CATALOG_NAME,
        **{
            "uri": DB_PATH,
            "warehouse": WAREHOUSE_PATH,
        }
    )
    return catalog

def get_cv_schema():
    """
    Defines the Iceberg schema for CV data.
    """
    return Schema(
        NestedField(1, "id", StringType(), required=True),
        NestedField(2, "filename", StringType(), required=True),
        NestedField(3, "ingestion_timestamp", TimestampType(), required=True),
        NestedField(4, "first_name", StringType(), required=True),
        NestedField(5, "last_name", StringType(), required=True),
        NestedField(6, "email", StringType(), required=False),
        NestedField(7, "phone", StringType(), required=False),
        NestedField(8, "summary", StringType(), required=False),
        NestedField(9, "skills", ListType(
            element_id=10, element=StringType(), element_required=False
        ), required=False),
        NestedField(11, "work_experience", ListType(
            element_id=12,
            element=StructType(
                NestedField(13, "company", StringType(), required=False),
                NestedField(14, "dates", StringType(), required=False),
                NestedField(15, "role", StringType(), required=False),
                NestedField(16, "description", StringType(), required=False),
            ),
            element_required=False
        ), required=False),
        NestedField(17, "education", ListType(
            element_id=18,
            element=StructType(
                NestedField(19, "school", StringType(), required=False),
                NestedField(20, "dates", StringType(), required=False),
                NestedField(21, "degree", StringType(), required=False),
            ),
            element_required=False
        ), required=False),
    )

def ensure_table_exists():
    """
    Checks if the table exists, creates it if not.
    """
    catalog = get_catalog()
    
    try:
        catalog.create_namespace(NAMESPACE)
    except Exception:
        pass # Namespace might already exist

    identifier = f"{NAMESPACE}.{TABLE_NAME}"
    
    try:
        catalog.load_table(identifier)
        print(f"Table {identifier} already exists.")
    except Exception:
        print(f"Creating table {identifier}...")
        catalog.create_table(
            identifier=identifier,
            schema=get_cv_schema(),
        )
        print(f"Table {identifier} created successfully.")

def save_cv_data(cv_data: CVData, filename: str):
    """
    Saves extracted CV data to the Iceberg table.
    """
    catalog = get_catalog()
    table = catalog.load_table(f"{NAMESPACE}.{TABLE_NAME}")
    
    # Transform Pydantic model to Dictionary compatible with Schema
    record = {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "ingestion_timestamp": datetime.now(),
        "first_name": cv_data.first_name,
        "last_name": cv_data.last_name,
        "email": cv_data.email,
        "phone": cv_data.phone,
        "summary": cv_data.summary,
        "skills": cv_data.skills,
        "work_experience": [
            {
                "company": we.company,
                "dates": we.dates,
                "role": we.role,
                "description": we.description
            } for we in cv_data.work_experience
        ],
        "education": [
            {
                "school": edu.school,
                "dates": edu.dates,
                "degree": edu.degree
            } for edu in cv_data.education
        ]
    }
    
    # Define PyArrow schema explicitly to match Iceberg schema
    # Iceberg: 
    #   1: id: required string
    #   2: filename: required string
    #   3: ingestion_timestamp: required timestamp
    #   4: first_name: required string
    #   5: last_name: required string
    #   ...
    
    arrow_schema = pa.schema([
        pa.field("id", pa.string(), nullable=False),
        pa.field("filename", pa.string(), nullable=False),
        pa.field("ingestion_timestamp", pa.timestamp("us"), nullable=False),
        pa.field("first_name", pa.string(), nullable=False),
        pa.field("last_name", pa.string(), nullable=False),
        pa.field("email", pa.string(), nullable=True),
        pa.field("phone", pa.string(), nullable=True),
        pa.field("summary", pa.string(), nullable=True),
        pa.field("skills", pa.list_(pa.string()), nullable=True),
        pa.field("work_experience", pa.list_(
            pa.struct([
                pa.field("company", pa.string(), nullable=True),
                pa.field("dates", pa.string(), nullable=True),
                pa.field("role", pa.string(), nullable=True),
                pa.field("description", pa.string(), nullable=True),
            ])
        ), nullable=True),
        pa.field("education", pa.list_(
            pa.struct([
                pa.field("school", pa.string(), nullable=True),
                pa.field("dates", pa.string(), nullable=True),
                pa.field("degree", pa.string(), nullable=True),
            ])
        ), nullable=True),
    ])

    arrow_table = pa.Table.from_pylist([record], schema=arrow_schema)
    
    # Append
    table.append(arrow_table)
    print(f"Standard {filename} data saved to Iceberg table.")

def list_cvs(search_query: str = None) -> typing.List[typing.Dict]:
    """
    Lists CVs from the Iceberg table, optionally filtered by search query.
    """
    try:
        catalog = get_catalog()
        table = catalog.load_table(f"{NAMESPACE}.{TABLE_NAME}")
        
        # Scan the table
        # For a real implementation with search, we would add filters to the scan.
        # PyIceberg filtering is powerful but for now we might fetch all (if small) 
        # or implement basic filtering.
        
        # Note: PyIceberg < 0.6 might have different scanning APIs. Assuming recent version.
        # We'll fetch selected columns to optimize.
        con = table.scan(
            selected_fields=("id", "first_name", "last_name", "filename", "summary")
        ).to_duckdb(table_name="cvs")
        
        query = "SELECT * FROM cvs"
        params = []
        if search_query:
            query += " WHERE first_name ILIKE ? OR last_name ILIKE ? OR filename ILIKE ?"
            wildcard = f"%{search_query}%"
            params = [wildcard, wildcard, wildcard]
            
        result = con.execute(query, params).fetchall()
        
        return cvs

    except Exception as e:
        print(f"Error listing CVs: {e}")
        return []

def get_cv(cv_id: str) -> typing.Optional[typing.Dict]:
    """
    Retrieves full details for a single CV.
    """
    try:
        catalog = get_catalog()
        table = catalog.load_table(f"{NAMESPACE}.{TABLE_NAME}")
        
        # We can use DuckDB to filter by ID easily
        con = table.scan().to_duckdb(table_name="cvs")
        result = con.execute("SELECT * FROM cvs WHERE id = ?", [cv_id]).fetchone()
        
        if result:
             columns = [desc[0] for desc in con.description]
             return dict(zip(columns, result))
        return None

    except Exception as e:
        print(f"Error getting CV {cv_id}: {e}")
        return None

def delete_cv(cv_id: str) -> bool:
    """
    Deletes a CV from the Iceberg table.
    """
    try:
        catalog = get_catalog()
        table = catalog.load_table(f"{NAMESPACE}.{TABLE_NAME}")
        
        # PyIceberg Delete: 
        # Note: Delete implementation depends on having a delete-enabled table.
        # However, for simple use cases or if strict delete isn't supported by the catalog/fileio combo,
        # we might need a workaround. 
        # But assuming PyIceberg write support is active (which we used for append).
        
        # Standard deletion if supported:
        table.delete(f"id = '{cv_id}'")
        print(f"Deleted CV {cv_id}")
        return True
        
    except Exception as e:
        print(f"Error deleting CV {cv_id}: {e}")
        return False

def list_cvs(search_query: str = None) -> typing.List[typing.Dict]:
    """
    Lists CVs from the Iceberg table, optionally filtered by search query.
    Updated to query skills and summary.
    """
    try:
        catalog = get_catalog()
        table = catalog.load_table(f"{NAMESPACE}.{TABLE_NAME}")
        
        # Fetching fewer fields for the list view to be lightweight
        con = table.scan(
            selected_fields=("id", "first_name", "last_name", "filename", "summary", "skills")
        ).to_duckdb(table_name="cvs")
        
        query = "SELECT id, first_name, last_name, filename, summary FROM cvs"
        params = []
        
        if search_query:
            # Note: duckdb list_contains or roughly converting list to string for searching
            # Skills is a list<string>. In DuckDB we can cast to text or use list functions.
            # Simplified approach: cast everything to text for ILIKE.
            
            wildcard = f"%{search_query}%"
            query += """ 
                WHERE first_name ILIKE ? 
                OR last_name ILIKE ? 
                OR filename ILIKE ?
                OR summary ILIKE ?
                OR list_contains(skills, ?)
            """
            # For list_contains, we might need exact match if using that function,
            # or we cast list to string and ILIKE it?
            # Let's try casting list to string for loose partial matching on skills
            
            query = """
                SELECT id, first_name, last_name, filename, summary 
                FROM cvs 
                WHERE first_name ILIKE ? 
                OR last_name ILIKE ? 
                OR filename ILIKE ?
                OR summary ILIKE ?
                OR CAST(skills AS VARCHAR) ILIKE ?
            """
            params = [wildcard, wildcard, wildcard, wildcard, wildcard]
            
        result = con.execute(query, params).fetchall()
        
        columns = [desc[0] for desc in con.description]
        cvs = []
        for row in result:
             cvs.append(dict(zip(columns, row)))
             
        return cvs

    except Exception as e:
        print(f"Error listing CVs: {e}")
        return []
