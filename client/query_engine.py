"""Query engine for processing and executing SQL queries with output parsing."""

import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from client.sql_client import SQLClient, AsyncSQLClient
from client.sql_exceptions import QueryError, QueryValidationError
from client.query_parser import OutputFormat, QueryOutputParser

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Query engine for processing and executing SQL queries with output parsing.
    
    Features:
    - SQL query validation and execution
    - Multiple output formats (JSON, CSV, Table, Raw)
    - Query templating with parameters
    - Result pagination
    - Query timeout management
    """
    
    def __init__(self, client: Optional[SQLClient] = None):
        """
        Initialize the query engine.
        
        Args:
            client: Optional SQLClient instance (creates one if not provided)
        """
        self.client = client or SQLClient()
        self.parser = QueryOutputParser()
    
    def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        output_format: Union[str, OutputFormat] = OutputFormat.TABLE,
        allow_write: bool = False,
        max_rows: Optional[int] = None,
    ) -> Tuple[Union[str, List[Dict], Dict], Optional[int]]:
        """
        Execute a query and return formatted output.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            output_format: Desired output format
            allow_write: Allow write operations
            max_rows: Maximum number of rows to return
            
        Returns:
            Tuple of (formatted_output, row_count)
        """
        # Apply row limit if specified
        if max_rows:
            query = self._apply_row_limit(query, max_rows)
        
        # Execute query
        results = self.client.execute(query, params, allow_write)
        
        # Handle write operations (no results)
        if results is None:
            return "Query executed successfully (no results returned)", 0
        
        # Format output
        formatted = self.parser.format(results, output_format)
        
        return formatted, len(results)
    
    def execute_many(
        self,
        query: str,
        params_list: List[Dict[str, Any]],
        output_format: Union[str, OutputFormat] = OutputFormat.JSON,
        allow_write: bool = True,
    ) -> str:
        """
        Execute a batch query.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter dictionaries
            output_format: Desired output format
            allow_write: Allow write operations
            
        Returns:
            Formatted execution summary
        """
        affected_rows = self.client.execute_many(query, params_list, allow_write)
        
        result = {
            "status": "success",
            "query": query,
            "batch_size": len(params_list),
            "affected_rows": affected_rows,
        }
        
        return self.parser.format(result, output_format)
    
    def query_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        output_format: Union[str, OutputFormat] = OutputFormat.TABLE,
    ) -> Tuple[Union[str, List[Dict], Dict], Optional[int]]:
        """
        Build and execute a SELECT query from a table.
        
        Args:
            table_name: Name of the table to query
            columns: List of columns to select (None for *)
            where: WHERE clause (without the WHERE keyword)
            params: Query parameters
            order_by: ORDER BY clause
            limit: Maximum number of rows
            offset: Offset for pagination
            
        Returns:
            Tuple of (formatted_output, row_count)
        """
        # Build SELECT clause
        select_clause = ", ".join(columns) if columns else "*"
        
        # Build query
        query = f"SELECT {select_clause} FROM {table_name}"
        
        if where:
            query += f" WHERE {where}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        if offset:
            query += f" OFFSET {offset}"
        
        return self.execute(query, params, output_format, allow_write=False)
    
    def insert(
        self,
        table_name: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        output_format: Union[str, OutputFormat] = OutputFormat.JSON,
    ) -> str:
        """
        Insert data into a table.
        
        Args:
            table_name: Name of the table
            data: Single record (dict) or multiple records (list of dicts)
            output_format: Desired output format
            
        Returns:
            Formatted insertion result
        """
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return self.parser.format(
                {"status": "warning", "message": "No data to insert"},
                output_format
            )
        
        # Get columns from first record
        columns = list(data[0].keys())
        
        # Build INSERT query
        placeholders = ", ".join([f"%({col})s" for col in columns])
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({placeholders})
            RETURNING *
        """
        
        try:
            # For single insert, use regular execute
            if len(data) == 1:
                results = self.client.execute(query, data[0], allow_write=True)
                result_data = {
                    "status": "success",
                    "table": table_name,
                    "inserted": 1,
                    "data": results[0] if results else None,
                }
            else:
                # For batch insert, use execute_many without RETURNING
                batch_query = f"""
                    INSERT INTO {table_name} ({', '.join(columns)})
                    VALUES ({placeholders})
                """
                affected_rows = self.client.execute_many(batch_query, data, allow_write=True)
                result_data = {
                    "status": "success",
                    "table": table_name,
                    "inserted": affected_rows,
                }
            
            return self.parser.format(result_data, output_format)
            
        except Exception as e:
            error_data = {
                "status": "error",
                "table": table_name,
                "error": str(e),
            }
            return self.parser.format(error_data, output_format)
    
    def update(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: str,
        params: Optional[Dict[str, Any]] = None,
        output_format: Union[str, OutputFormat] = OutputFormat.JSON,
    ) -> str:
        """
        Update records in a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column -> new value
            where: WHERE clause (without the WHERE keyword)
            params: Additional query parameters
            output_format: Desired output format
            
        Returns:
            Formatted update result
        """
        if not data:
            return self.parser.format(
                {"status": "warning", "message": "No data to update"},
                output_format
            )
        
        # Build SET clause
        set_clause = ", ".join([f"{col} = %({col})s" for col in data.keys()])
        
        # Combine data and params for the query
        query_params = {**data}
        if params:
            query_params.update(params)
        
        # Build UPDATE query with RETURNING
        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {where}
            RETURNING *
        """
        
        try:
            results = self.client.execute(query, query_params, allow_write=True)
            
            result_data = {
                "status": "success",
                "table": table_name,
                "updated": len(results) if results else 0,
                "data": results,
            }
            
            return self.parser.format(result_data, output_format)
            
        except Exception as e:
            error_data = {
                "status": "error",
                "table": table_name,
                "error": str(e),
            }
            return self.parser.format(error_data, output_format)
    
    def delete(
        self,
        table_name: str,
        where: str,
        params: Optional[Dict[str, Any]] = None,
        output_format: Union[str, OutputFormat] = OutputFormat.JSON,
    ) -> str:
        """
        Delete records from a table.
        
        Args:
            table_name: Name of the table
            where: WHERE clause (without the WHERE keyword)
            params: Query parameters
            output_format: Desired output format
            
        Returns:
            Formatted deletion result
        """
        # Build DELETE query with RETURNING
        query = f"""
            DELETE FROM {table_name}
            WHERE {where}
            RETURNING *
        """
        
        try:
            results = self.client.execute(query, params, allow_write=True)
            
            result_data = {
                "status": "success",
                "table": table_name,
                "deleted": len(results) if results else 0,
                "data": results,
            }
            
            return self.parser.format(result_data, output_format)
            
        except Exception as e:
            error_data = {
                "status": "error",
                "table": table_name,
                "error": str(e),
            }
            return self.parser.format(error_data, output_format)
    
    def get_table_info(self, table_name: str) -> str:
        """Get schema information for a table."""
        try:
            schema = self.client.get_table_schema(table_name)
            return self.parser.format(schema, OutputFormat.TABLE)
        except Exception as e:
            return f"Error getting table info: {e}"
    
    def _apply_row_limit(self, query: str, max_rows: int) -> str:
        """
        Apply a row limit to a SELECT query if not already present.
        
        Args:
            query: Original SQL query
            max_rows: Maximum number of rows
            
        Returns:
            Query with LIMIT clause if it was a SELECT without LIMIT
        """
        query_upper = query.strip().upper()
        
        # Only add LIMIT to SELECT queries that don't already have one
        if query_upper.startswith("SELECT") and "LIMIT" not in query_upper:
            # Remove trailing semicolon if present
            query = query.rstrip(';')
            return f"{query} LIMIT {max_rows}"
        
        return query
    
    def close(self) -> None:
        """Close the database client."""
        self.client.close()


class AsyncQueryEngine:
    """Async version of the Query Engine."""
    
    def __init__(self, client: Optional[AsyncSQLClient] = None):
        """
        Initialize the async query engine.
        
        Args:
            client: Optional AsyncSQLClient instance (creates one if not provided)
        """
        self.client = client or AsyncSQLClient()
        self.parser = QueryOutputParser()
    
    async def initialize(self) -> None:
        """Initialize the async client."""
        await self.client.initialize()
    
    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        output_format: Union[str, OutputFormat] = OutputFormat.TABLE,
        allow_write: bool = False,
        max_rows: Optional[int] = None,
    ) -> Tuple[Union[str, List[Dict], Dict], Optional[int]]:
        """Async version of execute."""
        if max_rows:
            query = self._apply_row_limit(query, max_rows)
        
        results = await self.client.execute(query, params, allow_write)
        
        if results is None:
            return "Query executed successfully (no results returned)", 0
        
        formatted = self.parser.format(results, output_format)
        return formatted, len(results)
    
    async def execute_many(
        self,
        query: str,
        params_list: List[Dict[str, Any]],
        output_format: Union[str, OutputFormat] = OutputFormat.JSON,
        allow_write: bool = True,
    ) -> str:
        """Async version of execute_many."""
        result = await self.client.execute_many(query, params_list, allow_write)
        
        result_data = {
            "status": "success",
            "query": query,
            "batch_size": len(params_list),
            "result": result,
        }
        
        return self.parser.format(result_data, output_format)
    
    async def query_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        output_format: Union[str, OutputFormat] = OutputFormat.TABLE,
    ) -> Tuple[Union[str, List[Dict], Dict], Optional[int]]:
        """Async version of query_table."""
        select_clause = ", ".join(columns) if columns else "*"
        
        query = f"SELECT {select_clause} FROM {table_name}"
        
        if where:
            query += f" WHERE {where}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        if offset:
            query += f" OFFSET {offset}"
        
        return await self.execute(query, params, output_format, allow_write=False)
    
    async def insert(
        self,
        table_name: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        output_format: Union[str, OutputFormat] = OutputFormat.JSON,
    ) -> str:
        """Async version of insert."""
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return self.parser.format(
                {"status": "warning", "message": "No data to insert"},
                output_format
            )
        
        columns = list(data[0].keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({placeholders})
            RETURNING *
        """
        
        try:
            if len(data) == 1:
                results = await self.client.execute(
                    query, 
                    dict(zip(columns, data[0].values())),
                    allow_write=True
                )
                result_data = {
                    "status": "success",
                    "table": table_name,
                    "inserted": 1,
                    "data": results[0] if results else None,
                }
            else:
                # For async, we need to execute sequentially in a transaction
                inserted = 0
                results = []
                
                async with self.client.transaction():
                    for row in data:
                        result = await self.client.execute(query, row, allow_write=True)
                        if result:
                            results.append(result[0])
                            inserted += 1
                
                result_data = {
                    "status": "success",
                    "table": table_name,
                    "inserted": inserted,
                    "data": results if results else None,
                }
            
            return self.parser.format(result_data, output_format)
            
        except Exception as e:
            error_data = {
                "status": "error",
                "table": table_name,
                "error": str(e),
            }
            return self.parser.format(error_data, output_format)
    
    async def close(self) -> None:
        """Close the async database client."""
        await self.client.close()
    
    def _apply_row_limit(self, query: str, max_rows: int) -> str:
        """Same as sync version."""
        query_upper = query.strip().upper()
        
        if query_upper.startswith("SELECT") and "LIMIT" not in query_upper:
            query = query.rstrip(';')
            return f"{query} LIMIT {max_rows}"
        
        return query