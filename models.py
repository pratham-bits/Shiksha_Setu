import os
from datetime import datetime, timedelta
import hashlib
import secrets

# Database configuration - automatically switches between SQLite and PostgreSQL
USE_POSTGRESQL = os.environ.get('DATABASE_URL') is not None

# Handle PostgreSQL imports gracefully
if USE_POSTGRESQL:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        print("🔗 Using PostgreSQL for authentication")
    except ImportError:
        print("⚠️  PostgreSQL not available, falling back to SQLite")
        USE_POSTGRESQL = False
        import sqlite3
else:
    import sqlite3
    print("🔗 Using SQLite for authentication")

# ADD THIS FUNCTION - it was missing
def init_auth_db():
    """Initialize authentication database with better error handling"""
    try:
        if USE_POSTGRESQL:
            return _init_auth_db_postgresql()
        else:
            return _init_auth_db_sqlite()
    except Exception as e:
        print(f"❌ Error initializing authentication database: {e}")
        raise

def _init_auth_db_sqlite():
    """Initialize SQLite authentication database"""
    db_path = os.path.join(os.path.dirname(__file__), 'users.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT,
                  email_verified BOOLEAN DEFAULT FALSE,
                  verification_token TEXT,
                  token_expiry DATETIME,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create indexes for better performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)')
    
    conn.commit()
    conn.close()
    print("✅ SQLite authentication database initialized successfully")

def _init_auth_db_postgresql():
    """Initialize PostgreSQL authentication database"""
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            email_verified BOOLEAN DEFAULT FALSE,
            verification_token TEXT,
            token_expiry TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)')
    
    conn.commit()
    conn.close()
    print("✅ PostgreSQL authentication database initialized successfully")

def get_auth_db_connection():
    """Get connection to authentication database"""
    if USE_POSTGRESQL:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        conn.autocommit = False
        return conn
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'users.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

# ALL YOUR EXISTING FUNCTIONS REMAIN EXACTLY THE SAME - JUST UPDATE THE QUERIES

def create_user(username, email, verification_token=None):
    """Create a new user with verification token"""
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        token_expiry = datetime.now() + timedelta(hours=24) if verification_token else None
        
        if USE_POSTGRESQL:
            cursor.execute(
                'INSERT INTO users (username, email, verification_token, token_expiry) VALUES (%s, %s, %s, %s) RETURNING id',
                (username, email, verification_token, token_expiry)
            )
            user_id = cursor.fetchone()[0]
        else:
            cursor.execute(
                'INSERT INTO users (username, email, verification_token, token_expiry) VALUES (?, ?, ?, ?)',
                (username, email, verification_token, token_expiry)
            )
            user_id = cursor.lastrowid
            
        conn.commit()
        conn.close()
        
        return user_id
    except Exception as e:
        if 'unique' in str(e).lower():
            raise ValueError("Username or email already exists")
        print(f"❌ Error creating user: {e}")
        raise

def get_user_by_username_or_email(identifier):
    """Get user by username or email"""
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute(
                'SELECT * FROM users WHERE username = %s OR email = %s', 
                (identifier, identifier)
            )
        else:
            cursor.execute(
                'SELECT * FROM users WHERE username = ? OR email = ?', 
                (identifier, identifier)
            )
            
        if USE_POSTGRESQL:
            user = cursor.fetchone()
            if user:
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user))
                conn.close()
                return user_dict
        else:
            user = cursor.fetchone()
            conn.close()
            return user
            
        conn.close()
        return None
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None

def verify_user_email(user_id):
    """Mark user's email as verified"""
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute(
                'UPDATE users SET email_verified = TRUE, verification_token = NULL, token_expiry = NULL WHERE id = %s',
                (user_id,)
            )
        else:
            cursor.execute(
                'UPDATE users SET email_verified = TRUE, verification_token = NULL, token_expiry = NULL WHERE id = ?',
                (user_id,)
            )
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error verifying user email: {e}")
        return False

def set_user_password(user_id, password_hash):
    """Set user password hash"""
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute(
                'UPDATE users SET password_hash = %s WHERE id = %s',
                (password_hash, user_id)
            )
        else:
            cursor.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (password_hash, user_id)
            )
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error setting user password: {e}")
        return False

def get_user_by_verification_token(token):
    """Get user by verification token if not expired"""
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute(
                'SELECT * FROM users WHERE verification_token = %s AND token_expiry > %s',
                (token, datetime.now())
            )
            user = cursor.fetchone()
            if user:
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user))
                conn.close()
                return user_dict
        else:
            cursor.execute(
                'SELECT * FROM users WHERE verification_token = ? AND token_expiry > ?',
                (token, datetime.now())
            )
            user = cursor.fetchone()
            conn.close()
            return user
            
        conn.close()
        return None
    except Exception as e:
        print(f"❌ Error getting user by token: {e}")
        return None

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

# Test function
def test_auth_db():
    """Test authentication database functionality"""
    print("🧪 Testing authentication database...")
    
    # Reinitialize database
    init_auth_db()
    
    # Test user creation
    try:
        test_code = generate_verification_code()
        user_id = create_user("testuser", "test@example.com", test_code)
        print(f"✅ User created successfully with ID: {user_id}")
        
        # Test retrieving user
        user = get_user_by_username_or_email("testuser")
        if user:
            print(f"✅ User retrieved successfully: {user['username']}")
        else:
            print("❌ Failed to retrieve user")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == '__main__':
    test_auth_db()