# app/database.py
from psycopg2 import pool
from contextlib import contextmanager

class Database:
    def __init__(self, database_url):
        """
        Initializes the connection pool using a database URL.
        :param database_url: A string containing the database connection information.
        """
        self.connection_pool = pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=database_url)

    @contextmanager
    def get_connection(self):
        """
        A context manager to acquire and release a connection from the pool.
        This allows the connection to be used with a 'with' statement, ensuring it is returned to the pool.
        """
        connection = self.connection_pool.getconn()
        try:
            yield connection
        finally:
            self.connection_pool.putconn(connection)

    def close_all_connections(self):
        """
        Closes all connections in the pool.
        """
        self.connection_pool.closeall()
