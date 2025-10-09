import sqlite3
import os
from datetime import datetime, timedelta
import hashlib
import secrets

def init_db():
    """Initialize authentication database with better error handling"""
    try:
        # Use absolute path for deployment compatibility
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
        print("✅ Authentication database initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing authentication database: {e}")
        raise

def get_db_connection():
    """Get connection to authentication database with error handling"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'users.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys and better performance
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # Better performance
        
        return conn
    except Exception as e:
        print(f"❌ Error connecting to authentication database: {e}")
        raise

# Utility functions for user management
def create_user(username, email, verification_token=None):
    """Create a new user with verification token"""
    try:
        conn = get_db_connection()
        token_expiry = datetime.now() + timedelta(hours=24) if verification_token else None
        
        conn.execute(
            'INSERT INTO users (username, email, verification_token, token_expiry) VALUES (?, ?, ?, ?)',
            (username, email, verification_token, token_expiry)
        )
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
        conn.close()
        
        return user_id
    except sqlite3.IntegrityError:
        raise ValueError("Username or email already exists")
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        raise

def get_user_by_username_or_email(identifier):
    """Get user by username or email"""
    try:
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (identifier, identifier)
        ).fetchone()
        conn.close()
        return user
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None

def verify_user_email(user_id):
    """Mark user's email as verified"""
    try:
        conn = get_db_connection()
        conn.execute(
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
        conn = get_db_connection()
        conn.execute(
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
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE verification_token = ? AND token_expiry > ?',
            (token, datetime.now())
        ).fetchone()
        conn.close()
        return user
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
    init_db()
    
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