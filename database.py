import os
import pandas as pd
from datetime import datetime
import sys

# Database configuration - automatically switches between SQLite and PostgreSQL
USE_POSTGRESQL = os.environ.get('DATABASE_URL') is not None

if USE_POSTGRESQL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("🔗 Using PostgreSQL database")
else:
    import sqlite3
    print("🔗 Using SQLite database")

class DatabaseManager:
    def __init__(self, db_path=None):
        self.use_postgresql = USE_POSTGRESQL
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), 'shiksha_setu.db')
        self.init_database()
        
    def get_connection(self):
        """Get database connection - works for both SQLite and PostgreSQL"""
        if self.use_postgresql:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            conn.autocommit = False
            return conn
        else:
            return sqlite3.connect(self.db_path)
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute query with parameters - works for both databases"""
        conn = self.get_connection()
        try:
            if self.use_postgresql:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query, params or ())
            else:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                # Convert to list of dictionaries for consistency
                if self.use_postgresql:
                    return [dict(row) for row in result]
                else:
                    return [dict(row) for row in result]
            else:
                conn.commit()
                return cursor.lastrowid if not self.use_postgresql else cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database with comprehensive higher education documents"""
        try:
            if self.use_postgresql:
                self._init_postgresql()
            else:
                self._init_sqlite()
                
            print("✅ Database initialized successfully with comprehensive documents")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we need to migrate from old schema
        cursor.execute("PRAGMA table_info(documents)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # Enhanced documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                document_type TEXT NOT NULL,
                category TEXT,
                sub_category TEXT,
                department TEXT,
                created_date DATE,
                last_updated DATE,
                status TEXT DEFAULT 'Active',
                jurisdiction TEXT,
                keywords TEXT,
                document_url TEXT,
                search_priority INTEGER DEFAULT 1,
                full_text_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create other tables and indexes (same as your original code)
        self._create_auxiliary_tables_sqlite(cursor, existing_columns)
        self._check_and_insert_data_sqlite(cursor)
        
        conn.commit()
        conn.close()
    
    def _init_postgresql(self):
        """Initialize PostgreSQL database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                document_type TEXT NOT NULL,
                category TEXT,
                sub_category TEXT,
                department TEXT,
                created_date DATE,
                last_updated DATE,
                status TEXT DEFAULT 'Active',
                jurisdiction TEXT,
                keywords TEXT,
                document_url TEXT,
                search_priority INTEGER DEFAULT 1,
                full_text_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create other tables and indexes
        self._create_auxiliary_tables_postgresql(cursor)
        self._check_and_insert_data_postgresql(cursor)
        
        conn.commit()
        conn.close()
    
    def _create_auxiliary_tables_sqlite(self, cursor, existing_columns):
        """Create auxiliary tables for SQLite"""
        # Create dedicated keywords table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                keyword TEXT NOT NULL,
                keyword_type TEXT,
                relevance_score INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        # Create search index table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                search_text TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON document_keywords(keyword)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department)')
        
        # Migration logic (same as your original)
        self._migrate_database(cursor, existing_columns)
    
    def _create_auxiliary_tables_postgresql(self, cursor):
        """Create auxiliary tables for PostgreSQL"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_keywords (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id),
                keyword TEXT NOT NULL,
                keyword_type TEXT,
                relevance_score INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_index (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id),
                search_text TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON document_keywords(keyword)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department)')
    
    def _check_and_insert_data_sqlite(self, cursor):
        """Check and insert data for SQLite"""
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("📥 Inserting comprehensive higher education documents...")
            self._insert_comprehensive_documents(cursor)
        else:
            print(f"📊 Database contains {count} documents")
    
    def _check_and_insert_data_postgresql(self, cursor):
        """Check and insert data for PostgreSQL"""
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("📥 Inserting comprehensive higher education documents...")
            self._insert_comprehensive_documents_postgresql(cursor)
        else:
            print(f"📊 Database contains {count} documents")
    
    def _migrate_database(self, cursor, existing_columns):
        """Migrate database schema - same as your original"""
        try:
            new_columns = [
                ('sub_category', 'TEXT'),
                ('last_updated', 'DATE'),
                ('status', 'TEXT DEFAULT "Active"'),
                ('jurisdiction', 'TEXT'),
                ('search_priority', 'INTEGER DEFAULT 1'),
                ('full_text_content', 'TEXT')
            ]
            
            for column_name, column_type in new_columns:
                if column_name not in existing_columns:
                    print(f"   Adding column: {column_name}")
                    cursor.execute(f'ALTER TABLE documents ADD COLUMN {column_name} {column_type}')
        except Exception as e:
            print(f"Migration error: {e}")
    
    def _insert_comprehensive_documents(self, cursor):
        """Insert documents for SQLite - same as your original"""
        comprehensive_documents = [
            # Your existing document data here (same as before)
            # ... [ALL YOUR EXISTING DOCUMENT DATA REMAINS EXACTLY THE SAME]
        ]
        
        for doc in comprehensive_documents:
            cursor.execute('''
                INSERT INTO documents (
                    title, content, document_type, category, sub_category, department,
                    created_date, last_updated, status, jurisdiction, keywords,
                    document_url, search_priority, full_text_content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc['title'], doc['content'], doc['document_type'], doc['category'],
                doc['sub_category'], doc['department'], doc['created_date'],
                doc['last_updated'], doc.get('status', 'Active'), doc.get('jurisdiction', 'National'),
                doc['keywords'], doc['document_url'], doc['search_priority'],
                doc['full_text_content']
            ))
            
            document_id = cursor.lastrowid
            
            # Insert keywords
            keywords = doc['keywords'].split(',')
            for keyword in keywords:
                clean_keyword = keyword.strip()
                if clean_keyword:
                    cursor.execute('''
                        INSERT INTO document_keywords (document_id, keyword, relevance_score)
                        VALUES (?, ?, ?)
                    ''', (document_id, clean_keyword, 1))
            
            # Insert into search index
            search_text = f"{doc['title']} {doc['content']} {doc['full_text_content']} {doc['keywords']}"
            cursor.execute('''
                INSERT INTO search_index (document_id, search_text)
                VALUES (?, ?)
            ''', (document_id, search_text))
        
        print(f"✅ Inserted {len(comprehensive_documents)} comprehensive higher education documents")
    
    def _insert_comprehensive_documents_postgresql(self, cursor):
        """Insert documents for PostgreSQL"""
        comprehensive_documents = [
            # Your existing document data here (same as before)
            # ... [ALL YOUR EXISTING DOCUMENT DATA REMAINS EXACTLY THE SAME]
        ]
        
        for doc in comprehensive_documents:
            cursor.execute('''
                INSERT INTO documents (
                    title, content, document_type, category, sub_category, department,
                    created_date, last_updated, status, jurisdiction, keywords,
                    document_url, search_priority, full_text_content
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                doc['title'], doc['content'], doc['document_type'], doc['category'],
                doc['sub_category'], doc['department'], doc['created_date'],
                doc['last_updated'], doc.get('status', 'Active'), doc.get('jurisdiction', 'National'),
                doc['keywords'], doc['document_url'], doc['search_priority'],
                doc['full_text_content']
            ))
            
            document_id = cursor.fetchone()[0]
            
            # Insert keywords
            keywords = doc['keywords'].split(',')
            for keyword in keywords:
                clean_keyword = keyword.strip()
                if clean_keyword:
                    cursor.execute('''
                        INSERT INTO document_keywords (document_id, keyword, relevance_score)
                        VALUES (%s, %s, %s)
                    ''', (document_id, clean_keyword, 1))
            
            # Insert into search index
            search_text = f"{doc['title']} {doc['content']} {doc['full_text_content']} {doc['keywords']}"
            cursor.execute('''
                INSERT INTO search_index (document_id, search_text)
                VALUES (%s, %s)
            ''', (document_id, search_text))
        
        print(f"✅ Inserted {len(comprehensive_documents)} comprehensive higher education documents")

    # ALL YOUR EXISTING METHODS REMAIN EXACTLY THE SAME - JUST UPDATE THE QUERIES SLIGHTLY
    
    def search_documents(self, query=None, doc_type=None, category=None, department=None, use_advanced=True):
        """Enhanced search documents with multiple criteria and better ranking"""
        try:
            if self.use_postgresql:
                return self._search_documents_postgresql(query, doc_type, category, department, use_advanced)
            else:
                return self._search_documents_sqlite(query, doc_type, category, department, use_advanced)
        except Exception as e:
            print(f"Database search error: {e}")
            return []

    def _search_documents_sqlite(self, query=None, doc_type=None, category=None, department=None, use_advanced=True):
        """SQLite implementation of search"""
        conn = sqlite3.connect(self.db_path)
        
        # Check if search_priority column exists
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(documents)")
        columns = [column[1] for column in cursor.fetchall()]
        has_search_priority = 'search_priority' in columns
        
        if use_advanced and query and has_search_priority:
            base_query = '''
                SELECT d.*, 
                       (CASE 
                        WHEN d.title LIKE ? THEN 5
                        WHEN d.keywords LIKE ? THEN 3
                        WHEN d.content LIKE ? THEN 2
                        ELSE 1
                       END) * COALESCE(d.search_priority, 1) as relevance
                FROM documents d
                WHERE (d.title LIKE ? OR d.content LIKE ? OR d.keywords LIKE ? OR d.full_text_content LIKE ?)
            '''
            params = [f'%{query}%'] * 7
        else:
            base_query = "SELECT * FROM documents WHERE 1=1"
            params = []
            if query:
                base_query += " AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?)"
                search_term = f"%{query}%"
                params.extend([search_term, search_term, search_term])
        
        # Add filters
        if doc_type:
            base_query += " AND document_type = ?"
            params.append(doc_type)
            
        if category:
            base_query += " AND category = ?"
            params.append(category)
            
        if department:
            base_query += " AND department = ?"
            params.append(department)
        
        # Add ordering
        if use_advanced and query and has_search_priority:
            base_query += " ORDER BY relevance DESC, COALESCE(search_priority, 1) DESC"
        else:
            base_query += " ORDER BY id DESC"
        
        df = pd.read_sql_query(base_query, conn, params=params)
        conn.close()
        
        return df.to_dict('records')

    def _search_documents_postgresql(self, query=None, doc_type=None, category=None, department=None, use_advanced=True):
        """PostgreSQL implementation of search"""
        if use_advanced and query:
            base_query = '''
                SELECT d.*, 
                       (CASE 
                        WHEN d.title ILIKE %s THEN 5
                        WHEN d.keywords ILIKE %s THEN 3
                        WHEN d.content ILIKE %s THEN 2
                        ELSE 1
                       END) * COALESCE(d.search_priority, 1) as relevance
                FROM documents d
                WHERE (d.title ILIKE %s OR d.content ILIKE %s OR d.keywords ILIKE %s OR d.full_text_content ILIKE %s)
            '''
            params = [f'%{query}%'] * 7
        else:
            base_query = "SELECT * FROM documents WHERE 1=1"
            params = []
            if query:
                base_query += " AND (title ILIKE %s OR content ILIKE %s OR keywords ILIKE %s)"
                search_term = f"%{query}%"
                params.extend([search_term, search_term, search_term])
        
        # Add filters
        if doc_type:
            base_query += " AND document_type = %s"
            params.append(doc_type)
            
        if category:
            base_query += " AND category = %s"
            params.append(category)
            
        if department:
            base_query += " AND department = %s"
            params.append(department)
        
        # Add ordering
        if use_advanced and query:
            base_query += " ORDER BY relevance DESC, COALESCE(search_priority, 1) DESC"
        else:
            base_query += " ORDER BY id DESC"
        
        results = self.execute_query(base_query, params, fetch=True)
        return results

    # Keep all your other methods exactly the same - just update the internal queries
    def get_all_documents(self):
        """Get all documents for display"""
        try:
            if self.use_postgresql:
                query = "SELECT * FROM documents ORDER BY COALESCE(search_priority, 1) DESC, id DESC"
            else:
                query = "SELECT * FROM documents ORDER BY COALESCE(search_priority, 1) DESC, id DESC"
                
            results = self.execute_query(query, fetch=True)
            return results
        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []

    def get_document_by_id(self, document_id):
        """Get a specific document by ID"""
        try:
            if self.use_postgresql:
                query = "SELECT * FROM documents WHERE id = %s"
            else:
                query = "SELECT * FROM documents WHERE id = ?"
                
            results = self.execute_query(query, (document_id,), fetch=True)
            return results[0] if results else None
        except Exception as e:
            print(f"Error getting document by ID: {e}")
            return None

    def keyword_search(self, keywords):
        """Precise keyword-based search"""
        try:
            keyword_list = [k.strip() for k in keywords.split(',')]
            
            if self.use_postgresql:
                placeholders = ','.join(['%s'] * len(keyword_list))
                query = f'''
                    SELECT d.*, COUNT(dk.keyword) as keyword_matches
                    FROM documents d
                    JOIN document_keywords dk ON d.id = dk.document_id
                    WHERE dk.keyword IN ({placeholders})
                    GROUP BY d.id
                    ORDER BY keyword_matches DESC, COALESCE(d.search_priority, 1) DESC
                '''
            else:
                placeholders = ','.join(['?'] * len(keyword_list))
                query = f'''
                    SELECT d.*, COUNT(dk.keyword) as keyword_matches
                    FROM documents d
                    JOIN document_keywords dk ON d.id = dk.document_id
                    WHERE dk.keyword IN ({placeholders})
                    GROUP BY d.id
                    ORDER BY keyword_matches DESC, COALESCE(d.search_priority, 1) DESC
                '''
            
            results = self.execute_query(query, keyword_list, fetch=True)
            return results
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []

    def get_categories(self):
        """Get all unique categories"""
        try:
            query = "SELECT DISTINCT category FROM documents WHERE category IS NOT NULL ORDER BY category"
            results = self.execute_query(query, fetch=True)
            return [row['category'] for row in results]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

    def get_document_types(self):
        """Get all unique document types"""
        try:
            query = "SELECT DISTINCT document_type FROM documents WHERE document_type IS NOT NULL ORDER BY document_type"
            results = self.execute_query(query, fetch=True)
            return [row['document_type'] for row in results]
        except Exception as e:
            print(f"Error getting document types: {e}")
            return []

    def get_departments(self):
        """Get all unique departments"""
        try:
            query = "SELECT DISTINCT department FROM documents WHERE department IS NOT NULL ORDER BY department"
            results = self.execute_query(query, fetch=True)
            return [row['department'] for row in results]
        except Exception as e:
            print(f"Error getting departments: {e}")
            return []

    def get_sub_categories(self):
        """Get all unique sub-categories"""
        try:
            query = "SELECT DISTINCT sub_category FROM documents WHERE sub_category IS NOT NULL ORDER BY sub_category"
            results = self.execute_query(query, fetch=True)
            return [row['sub_category'] for row in results]
        except Exception as e:
            print(f"Error getting sub-categories: {e}")
            return []

# Test function
def test_comprehensive_database():
    """Test the comprehensive database functionality"""
    print("🧪 Testing comprehensive database...")
    
    # Delete existing SQLite database to force recreation
    if os.path.exists('shiksha_setu.db'):
        os.remove('shiksha_setu.db')
        print("🗑️  Removed old database file")
    
    db = DatabaseManager()
    documents = db.get_all_documents()
    print(f"📄 Loaded {len(documents)} documents from database")
    
    # Test searches
    results = db.search_documents(query="education policy")
    print(f"🔍 'education policy' search found {len(results)} documents")

if __name__ == '__main__':
    test_comprehensive_database()