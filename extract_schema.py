"""
Extract BigQuery schema with detailed information for the curiosity agent.
"""

from google.cloud import bigquery
import json

def extract_schema(project_id, dataset_id):
    """Extract comprehensive schema information from BigQuery dataset"""
    
    client = bigquery.Client(project=project_id)
    dataset_ref = client.dataset(dataset_id)
    
    schema_info = {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "tables": []
    }
    
    # Get all tables in the dataset
    tables = client.list_tables(dataset_ref)
    
    for table_item in tables:
        table_ref = dataset_ref.table(table_item.table_id)
        table = client.get_table(table_ref)
        
        table_info = {
            "table_name": table.table_id,
            "description": table.description or "",
            "num_rows": table.num_rows,
            "columns": []
        }
        
        # Get column information
        for field in table.schema:
            column_info = {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "description": field.description or ""
            }
            table_info["columns"].append(column_info)
        
        schema_info["tables"].append(table_info)
    
    return schema_info


def main():
    # Configuration
    PROJECT_ID = "thelook-459020"  # From your screenshot
    DATASET_ID = "thelook"
    
    print(f"Extracting schema from {PROJECT_ID}.{DATASET_ID}...")
    
    schema = extract_schema(PROJECT_ID, DATASET_ID)
    
    # Save to JSON
    with open("schema.json", "w") as f:
        json.dump(schema, f, indent=2)
    
    print(f"✅ Schema extracted successfully!")
    print(f"   Tables found: {len(schema['tables'])}")
    for table in schema['tables']:
        print(f"   - {table['table_name']}: {len(table['columns'])} columns, {table['num_rows']} rows")
    
    print("\n📁 Saved to: schema.json")


if __name__ == "__main__":
    main()
