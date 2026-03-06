"""SQL database client with connection pooling and async support for MySQL."""

import asyncio
import logging
import re
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple, Union

import mysql.connector
from mysql.connector import pooling
from mysql.connector import Error as MySQLError
import aiomysql
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from client.sql_exceptions import (
    ConnectionError,
    DataError,
    PoolExhaustedError,
    QueryError,
    QueryTimeoutError,
    QueryValidationError,
    SchemaError,
    TransactionError,
)

logger = logging.getLogger(__name__)


# SQL injection prevention - block dangerous patterns
DANGEROUS_PATTERNS = [
    r";\s*$",  # Multiple statements not allowed
    r"UNION\s+ALL\s+SELECT",  # Union-based injection
    r"INTO\s+OUTFILE",  # File writes
    r"INTO\s+DUMPFILE",  # File dumps
    r"LOAD_FILE\(",  # File reads
    r"INFORMATION_SCHEMA\.",  # Schema access (allow in read-only mode with flag)
]

# Write operations that should be blocked in safe mode
WRITE_OPERATIONS = [
    r"^\s*INSERT",
    r"^\s*UPDATE",
    r"^\s*DELETE",
    r"^\s*DROP",
    r"^\s*TRUNCATE",
    r"^\s*ALTER",
    r"^\s*CREATE",
    r"^\s*REPLACE",
]


class DatabaseNotConfiguredError(Exception):
    """Raised when database operations are attempted but database is not configured."""
    
    def __init__(self, message: str = "Database not configured. Please check DB_* environment variables."):
        self.message = message
        super().__init__(message)


class SQLClient:
    """Synchronous MySQL database client with connection pooling."""
    
    def __init__(self) -> None:
        # Check if database is configured
        if settings.database is None:
            logger.warning("Database not configured. SQLClient will not be functional.")
            self._connection_pool = None
            self.settings = None
            return
            
        self.settings = settings.database
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool."""
        if self.settings is None:
            return
            
        try:
            config = {
                'host': self.settings.host,
                'port': self.settings.port,
                'database': self.settings.database,
                'user': self.settings.username,
                'password': self.settings.password,
                'pool_name': 'moodle_pool',
                'pool_size': self.settings.pool_max_size,
                'pool_reset_session': True,
                'connection_timeout': self.settings.pool_timeout,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'autocommit': False,
                'buffered': True,
            }
            
            # Add SSL config if specified
            if self.settings.ssl_mode != 'prefer':
                config['ssl_mode'] = self.settings.ssl_mode
            if self.settings.ssl_ca_cert:
                config['ssl_ca'] = self.settings.ssl_ca_cert
            
            self._connection_pool = pooling.MySQLConnectionPool(**config)
            
            logger.info(
                "MySQL connection pool initialized: %s:%s/%s",
                self.settings.host,
                self.settings.port,
                self.settings.database,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to initialize connection pool: {e}", e)
    
    def _check_configured(self) -> None:
        """Check if database is configured and raise if not."""
        if settings.database is None or self._connection_pool is None:
            raise DatabaseNotConfiguredError()
    
    def _validate_query(self, query: str, allow_write: bool = False) -> None:
        """
        Validate SQL query for safety.
        
        Args:
            query: SQL query to validate
            allow_write: If True, allow write operations in safe mode
            
        Raises:
            QueryValidationError: If query is potentially dangerous
        """
        self._check_configured()
        
        # Check for dangerous patterns
        query_upper = query.upper()
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                raise QueryValidationError(
                    f"Potentially dangerous SQL pattern detected: {pattern}",
                    query=query
                )
        
        # Check for write operations in safe mode
        if self.settings.safe_mode and not allow_write:
            for pattern in WRITE_OPERATIONS:
                if re.match(pattern, query_upper, re.IGNORECASE):
                    raise QueryValidationError(
                        f"Write operations are blocked in safe mode. Use allow_write=True to override.",
                        query=query
                    )
    
    def _get_connection(self):
        """Get a connection from the pool."""
        self._check_configured()
        
        if not self._connection_pool:
            raise ConnectionError("Connection pool not initialized")
        
        try:
            conn = self._connection_pool.get_connection()
            
            # Set session variables
            cursor = conn.cursor()
            cursor.execute(f"SET SESSION MAX_EXECUTION_TIME = {self.settings.statement_timeout}")
            cursor.execute(f"SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
            cursor.close()
            
            return conn
        except Exception as e:
            raise PoolExhaustedError(f"Failed to get connection from pool: {e}")
    
    def _return_connection(self, conn) -> None:
        """Return a connection to the pool."""
        if conn and self._connection_pool:
            conn.close()  # MySQL connector pool handles this
    
    @retry(
        retry=retry_if_exception_type((MySQLError, mysql.connector.errors.OperationalError)),
        stop=stop_after_attempt(lambda: settings.database.pool_max_size if settings.database else 3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def execute(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        allow_write: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            allow_write: Allow write operations in safe mode
            
        Returns:
            List of rows as dictionaries for SELECT queries, None for write operations
        """
        self._check_configured()
        self._validate_query(query, allow_write)
        
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            
            # Use dictionary cursor for named columns
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            logger.debug("Executing query: %s", query)
            logger.debug("Parameters: %s", params)
            
            cursor.execute(query, params or {})
            
            # Check if this is a SELECT query
            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                logger.debug("Query returned %d rows", len(results))
                return results
            else:
                # For write operations, commit and return row count
                conn.commit()
                logger.debug("Query affected %d rows", cursor.rowcount)
                return None
                
        except mysql.connector.errors.DatabaseError as e:
            logger.error("Database error: %s", e)
            if e.errno == 3024:  # Query timeout
                raise QueryTimeoutError(query=query, timeout=self.settings.query_timeout)
            raise QueryError(f"Database error: {e}", query=query, params=params, original_error=e)
        except mysql.connector.Error as e:
            logger.error("MySQL error: %s", e)
            raise QueryError(f"MySQL error: {e}", query=query, params=params, original_error=e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self._return_connection(conn)
    
    def execute_many(
        self,
        query: str,
        params_list: List[Dict[str, Any]],
        allow_write: bool = True
    ) -> int:
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter dictionaries
            allow_write: Allow write operations in safe mode
            
        Returns:
            Total number of affected rows
        """
        self._check_configured()
        self._validate_query(query, allow_write)
        
        if not params_list:
            return 0
        
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            logger.debug("Executing batch query with %d parameter sets", len(params_list))
            
            # Use executemany for batch operations
            cursor.executemany(query, [tuple(params.values()) for params in params_list])
            conn.commit()
            
            total_rows = cursor.rowcount
            logger.debug("Batch query affected %d rows", total_rows)
            return total_rows
            
        except mysql.connector.Error as e:
            logger.error("Batch database error: %s", e)
            raise QueryError(f"Batch database error: {e}", query=query, original_error=e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self._return_connection(conn)
    
    @contextmanager
    def transaction(self, allow_write: bool = True) -> Generator:
        """
        Context manager for database transactions.
        
        Args:
            allow_write: Allow write operations in safe mode
            
        Yields:
            Database connection with transaction management
        """
        self._check_configured()
        
        conn = None
        try:
            conn = self._get_connection()
            conn.start_transaction()
            
            logger.debug("Starting database transaction")
            yield conn
            
            conn.commit()
            logger.debug("Transaction committed")
            
        except Exception as e:
            if conn:
                conn.rollback()
                logger.debug("Transaction rolled back due to: %s", e)
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if a table exists in the database."""
        self._check_configured()
        schema = schema or self.settings.db_schema
        query = """
            SELECT COUNT(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = %s
        """
        result = self.execute(query, (schema, table_name), allow_write=False)
        return result[0]['table_count'] > 0 if result else False
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get schema information for a table."""
        self._check_configured()
        schema = schema or self.settings.db_schema
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position
        """
        return self.execute(query, (schema, table_name), allow_write=False) or []
    
    def close(self) -> None:
        """Close all database connections."""
        # MySQL connector pool handles this automatically
        logger.info("MySQL connection pool closed")
    
    def __enter__(self) -> "SQLClient":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncSQLClient:
    """Asynchronous MySQL database client with connection pooling."""
    
    def __init__(self) -> None:
        if settings.database is None:
            logger.warning("Database not configured. AsyncSQLClient will not be functional.")
            self._pool = None
            self.settings = None
            return
            
        self.settings = settings.database
        self._pool: Optional[aiomysql.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize the async connection pool."""
        if settings.database is None:
            logger.warning("Database not configured. Skipping async pool initialization.")
            return
            
        if self._pool:
            return
        
        try:
            self._pool = await aiomysql.create_pool(
                host=self.settings.host,
                port=self.settings.port,
                db=self.settings.database,
                user=self.settings.username,
                password=self.settings.password,
                minsize=self.settings.pool_min_size,
                maxsize=self.settings.pool_max_size,
                connect_timeout=self.settings.pool_timeout,
                charset='utf8mb4',
                autocommit=False,
                pool_recycle=3600,  # Recycle connections after 1 hour
            )
            logger.info(
                "Async MySQL connection pool initialized: %s:%s/%s",
                self.settings.host,
                self.settings.port,
                self.settings.database,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to initialize async connection pool: {e}", e)
    
    def _check_configured(self) -> None:
        """Check if database is configured and raise if not."""
        if settings.database is None:
            raise DatabaseNotConfiguredError()
    
    def _validate_query(self, query: str, allow_write: bool = False) -> None:
        """Validate SQL query for safety."""
        self._check_configured()
        
        query_upper = query.upper()
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                raise QueryValidationError(
                    f"Potentially dangerous SQL pattern detected: {pattern}",
                    query=query
                )
        
        if self.settings.safe_mode and not allow_write:
            for pattern in WRITE_OPERATIONS:
                if re.match(pattern, query_upper, re.IGNORECASE):
                    raise QueryValidationError(
                        f"Write operations are blocked in safe mode. Use allow_write=True to override.",
                        query=query
                    )
    
    @retry(
        retry=retry_if_exception_type((aiomysql.OperationalError, ConnectionError)),
        stop=stop_after_attempt(lambda: settings.database.pool_max_size if settings.database else 3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def execute(
        self,
        query: str,
        params: Optional[Union[Dict, Tuple, List]] = None,
        allow_write: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query asynchronously.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            allow_write: Allow write operations in safe mode
            
        Returns:
            List of rows as dictionaries for SELECT queries, None for write operations
        """
        self._check_configured()
        self._validate_query(query, allow_write)
        
        if not self._pool:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    logger.debug("Executing async query: %s", query)
                    logger.debug("Parameters: %s", params)
                    
                    await cursor.execute(query, params or ())
                    
                    if query.strip().upper().startswith("SELECT"):
                        results = await cursor.fetchall()
                        logger.debug("Query returned %d rows", len(results))
                        return results
                    else:
                        await conn.commit()
                        logger.debug("Query affected %d rows", cursor.rowcount)
                        return None
                        
                except aiomysql.Error as e:
                    logger.error("Async MySQL error: %s", e)
                    raise QueryError(f"Database error: {e}", query=query, params=params, original_error=e)
    
    async def execute_many(
        self,
        query: str,
        params_list: List[Union[Dict, Tuple, List]],
        allow_write: bool = True
    ) -> int:
        """
        Execute a query with multiple parameter sets asynchronously.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter dictionaries or tuples
            allow_write: Allow write operations in safe mode
            
        Returns:
            Total number of affected rows
        """
        self._check_configured()
        self._validate_query(query, allow_write)
        
        if not params_list or not self._pool:
            return 0
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # Convert params to list of tuples if they're dicts
                    if isinstance(params_list[0], dict):
                        params = [tuple(p.values()) for p in params_list]
                    else:
                        params = params_list
                    
                    await cursor.executemany(query, params)
                    await conn.commit()
                    
                    logger.debug("Batch query executed with %d parameter sets", len(params_list))
                    return cursor.rowcount
                    
                except aiomysql.Error as e:
                    logger.error("Async batch database error: %s", e)
                    raise QueryError(f"Batch database error: {e}", query=query, original_error=e)
    
    @asynccontextmanager
    async def transaction(self, allow_write: bool = True) -> AsyncGenerator:
        """
        Context manager for async database transactions.
        
        Args:
            allow_write: Allow write operations in safe mode
            
        Yields:
            Database connection with transaction management
        """
        self._check_configured()
        
        if not self._pool:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await conn.begin()
                logger.debug("Starting async database transaction")
                
                try:
                    yield conn
                    await conn.commit()
                    logger.debug("Async transaction committed")
                except Exception as e:
                    await conn.rollback()
                    logger.debug("Async transaction rolled back due to: %s", e)
                    raise
    
    async def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if a table exists in the database (async)."""
        self._check_configured()
        schema = schema or self.settings.db_schema
        query = """
            SELECT COUNT(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = %s
        """
        result = await self.execute(query, (schema, table_name), allow_write=False)
        return result[0]['table_count'] > 0 if result else False
    
    async def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get schema information for a table (async)."""
        self._check_configured()
        schema = schema or self.settings.db_schema
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position
        """
        return await self.execute(query, (schema, table_name), allow_write=False) or []
    
    async def close(self) -> None:
        """Close all database connections."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("Async MySQL connection pool closed")
    
    async def __aenter__(self) -> "AsyncSQLClient":
        await self.initialize()
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        await self.close()