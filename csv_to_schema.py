#!/usr/bin/env python3
"""
Convert a CSV file describing your database schema to schema.json format.

CSV Format:
table_name,column_name,data_type,nullable,description
users,id,INTEGER,REQUIRED,Primary key
users,email,STRING,REQUIRED,User email address
users,created_at,TIMESTAMP,REQUIRED,Account creation timestamp
orders,id,INTEGER,REQUIRED,Primary key
orders,user_id,INTEGER,REQUIRED,Foreign key to users
...

Usage:
    python csv_to_schema.py schema.csv --project your-project --dataset your-dataset
"""

import csv
import json
import argparse
from collections import defaultdict

def csv_to_schema(csv_file, project_id, dataset_id, output_file="schema.json"):
    """Convert CSV schema to schema.json format"""

    # Group columns by table
    tables_dict = defaultdict(list)

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            table_name = row['table_name']
            column = {
                "name": row['column_name'],
                "type": row['data_type'],
                "mode": row.get('nullable', 'NULLABLE'),
                "description": row.get('description', '')
            }
            tables_dict[table_name].append(column)

    # Build schema structure
    schema = {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "tables": []
    }

    for table_name, columns in tables_dict.items():
        table = {
            "table_name": table_name,
            "description": f"Table: {table_name}",
            "num_rows": 0,  # You can update this manually or leave as 0
            "columns": columns
        }
        schema["tables"].append(table)

    # Write to file
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)

    print(f"✅ Schema created: {output_file}")
    print(f"   📊 {len(schema['tables'])} tables")
    print(f"   📋 {sum(len(t['columns']) for t in schema['tables'])} columns")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Convert CSV schema to schema.json format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example CSV format:
    table_name,column_name,data_type,nullable,description
    users,id,INTEGER,REQUIRED,Primary key
    users,email,STRING,REQUIRED,User email address
    users,created_at,TIMESTAMP,REQUIRED,Account creation timestamp
    orders,id,INTEGER,REQUIRED,Primary key
    orders,user_id,INTEGER,REQUIRED,Foreign key to users table
    orders,total_amount,FLOAT,REQUIRED,Order total in USD
        """
    )

    parser.add_argument('csv_file', help='Path to CSV file with schema')
    parser.add_argument('--project', required=True, help='Project ID')
    parser.add_argument('--dataset', required=True, help='Dataset ID')
    parser.add_argument('--output', default='schema.json', help='Output file (default: schema.json)')

    args = parser.parse_args()

    csv_to_schema(args.csv_file, args.project, args.dataset, args.output)


if __name__ == "__main__":
    main()
