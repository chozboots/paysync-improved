import logging
from typing import Any, Dict, List
from psycopg2.extras import DictCursor
from flask import g

logger = logging.getLogger(__name__)

# Assuming g.db_conn is a global database connection object
class Queries:
    def __init__(self):
        pass
    
    def check_existence(self, table_name: str, fields: List[str], values: List[Any]) -> bool:
        """
        Checks if any records match the specified fields and values in the specified table of the database.

        Parameters:
        - table_name (str): The name of the table to search.
        - fields (List[str]): The fields to query against.
        - values (List[Any]): The values corresponding to each field.

        Returns:
        - bool: True if at least one record matches the criteria, False otherwise.

        Raises:
        - Exception: Propagates any exceptions caught during database operations.
        """
        if len(fields) != len(values):
            raise ValueError('Fields and values count mismatch.')

        query_parts = [f"{field} = %s" for field in fields]  # Safe field placeholder
        query = f"SELECT 1 FROM {table_name} WHERE {' OR '.join(query_parts)} LIMIT 1"
        
        try:
            with g.db_conn as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tuple(values))
                    return bool(cursor.fetchone())
        except Exception as e:
            logger.error(f"Failed to communicate with database: {e}")
            raise

    def fetch_records(self, table_name: str, fields: List[str], values: List[Any], return_fields: List[str]) -> List[Dict[str, Any]]:
        """
        Fetches records from the specified table in the database matching the specified fields and values.

        Parameters:
        - table_name (str): The name of the table to search.
        - fields (List[str]): The fields to query against.
        - values (List[Any]): The values corresponding to each field.
        - return_fields (List[str]): The fields to return for matching records.

        Returns:
        - List[Dict[str, Any]]: A list of dictionaries, each representing a matching record.

        Raises:
        - Exception: Propagates any exceptions caught during database operations.
        """
        if len(fields) != len(values):
            raise ValueError('Fields and values count mismatch.')

        query_parts = [f"{field} = %s" for field in fields]
        query = f"SELECT {', '.join(return_fields)} FROM {table_name} WHERE {' OR '.join(query_parts)}"
        
        try:
            with g.db_conn as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(query, tuple(values))
                    records = cursor.fetchall()
                    return [dict(record) for record in records] if records else []
        except Exception as e:
            logger.error(f"Failed to communicate with database: {e}")
            raise

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a record into the specified table in the database.

        Parameters:
        - table_name (str): The name of the table where the data will be inserted.
        - data (Dict[str, Any]): A dictionary where keys are column names and values are the data to insert.

        Returns:
        - Dict[str, Any]: A dictionary containing a success message and any relevant information (e.g., the ID of the inserted record).

        Raises:
        - Exception: Propagates any exceptions caught during database operations.
        """
        fields = list(data.keys())
        values = list(data.values())
        placeholders = ["%s" for _ in fields]  # Create placeholders for the values

        query = f"""
        INSERT INTO {table_name} ({', '.join(fields)})
        VALUES ({', '.join(placeholders)})
        """
        
        try:
            with g.db_conn as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tuple(values))
                    conn.commit()
                    return {'message': 'Record inserted successfully.'}
        except Exception as e:
            logger.error(f"Failed to insert record into database: {e}")
            raise
        
    def delete_record(self, table_name: str, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deletes records from the specified table in the database matching the specified conditions.

        Parameters:
        - table_name (str): The name of the table from which to delete records.
        - conditions (Dict[str, Any]): A dictionary where keys are column names and values are the conditions for deletion.

        Returns:
        - Dict[str, Any]: A dictionary containing the status of the operation and the number of rows affected.

        Raises:
        - Exception: Propagates any exceptions caught during database operations.
        """
        if not conditions:
            raise ValueError("No conditions provided for deletion.")

        condition_parts = [f"{field} = %s" for field in conditions]
        query = f"DELETE FROM {table_name} WHERE {' AND '.join(condition_parts)} RETURNING *;"
        
        try:
            with g.db_conn as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tuple(conditions.values()))
                    deleted_records = cursor.rowcount  # Number of rows affected by the delete operation
                    conn.commit()
                    return {'status': 'success', 'rows_deleted': deleted_records}
        except Exception as e:
            logger.error(f"Failed to delete records from database: {e}")
            raise
