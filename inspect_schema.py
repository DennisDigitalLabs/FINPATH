#!/usr/bin/env python
"""Inspect FINPATH database schema."""

# Import models to register them with SQLAlchemy
from backend.models import User, Assessment, Prediction, Recommendation
from backend.database import Base, engine
from sqlalchemy import inspect, text

# Create all tables if they don't exist
Base.metadata.create_all(engine)

# Get inspector
inspector = inspect(engine)

# Get table names
tables = inspector.get_table_names()
print("=" * 70)
print("FINPATH DATABASE SCHEMA")
print("=" * 70)
print(f"\nTables ({len(tables)}): {', '.join(sorted(tables))}\n")

# For each table, show columns and constraints
for table_name in sorted(tables):
    print(f"\n{'─' * 70}")
    print(f"TABLE: {table_name}")
    print(f"{'─' * 70}")
    
    # Columns
    columns = inspector.get_columns(table_name)
    print("\nColumns:")
    for col in columns:
        col_type = str(col['type'])
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  • {col['name']:<20} {col_type:<15} {nullable}")
    
    # Primary Key
    pk = inspector.get_pk_constraint(table_name)
    if pk['constrained_columns']:
        print(f"\nPrimary Key: {', '.join(pk['constrained_columns'])}")
    
    # Foreign Keys
    fks = inspector.get_foreign_keys(table_name)
    if fks:
        print("\nForeign Keys:")
        for fk in fks:
            cols = ', '.join(fk['constrained_columns'])
            ref = f"{fk['referred_table']}.{', '.join(fk['referred_columns'])}"
            print(f"  • {cols} → {ref}")
    
    # Indexes
    indexes = inspector.get_indexes(table_name)
    if indexes:
        print("\nIndexes:")
        for idx in indexes:
            cols = ', '.join(idx['column_names'])
            unique = " (UNIQUE)" if idx['unique'] else ""
            print(f"  • {idx['name']}: {cols}{unique}")

print(f"\n{'=' * 70}\n")

# Print ER Diagram info
print("ENTITY RELATIONSHIPS (ER Diagram):")
print("=" * 70)
print("""
users
  │
  ├─ id (PK) → assessments.user_id
  ├─ email (UNIQUE, INDEX)
  └─ created_at, updated_at
      │
      └─ assessments (1:many)
          │
          ├─ id (PK) → predictions.assessment_id
          ├─ user_id (FK → users.id) 
          ├─ assessment_data (JSON)
          └─ assessment_status (INDEX)
              │
              └─ predictions (1:many)
                  │
                  ├─ id (PK) → recommendations.prediction_id
                  ├─ assessment_id (FK → assessments.id)
                  ├─ risk_level (INDEX)
                  ├─ probability, confidence
                  └─ model_version
                      │
                      └─ recommendations (1:many)
                          │
                          ├─ id (PK)
                          ├─ prediction_id (FK → predictions.id)
                          ├─ category, priority (INDEX)
                          └─ recommendation_text

CASCADE Behavior:
  • Delete user → DELETE assessments, predictions, recommendations
  • Delete assessment → DELETE predictions, recommendations
  • Delete prediction → DELETE recommendations
""")
print("=" * 70)
