import sqlite3
import psycopg2
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
from database import DatabaseManager
from models import create_user, get_user_by_username_or_email, verify_user_email, hash_password, init_auth_db, get_auth_db_connection
from nlp_processor import NLPProcessor
import traceback
import hashlib
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from dotenv import load_dotenv
import sys
import traceback
import threading
import time
import requests

# Add better error handling
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("UNHANDLED EXCEPTION:", file=sys.stderr)
    print("Type:", exc_type, file=sys.stderr)
    print("Value:", exc_value, file=sys.stderr)
    print("Traceback:", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

sys.excepthook = handle_exception

load_dotenv()  # Load environment variables from .env file

# Debug: Check if all imports work
try:
    print("🔧 Testing imports...")
    from nlp_processor import NLPProcessor
    print("✅ NLPProcessor imported successfully")
    
    from database import DatabaseManager
    print("✅ DatabaseManager imported successfully")
    
    from models import init_auth_db
    print("✅ Auth models imported successfully")
    
    print("✅ All imports successful!")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key-for-development')

# ✅ CRITICAL FIX: Session configuration for persistence
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # 1 week session
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # For HTTPS in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize components with error handling
db_manager = DatabaseManager()
nlp_processor = NLPProcessor()

# Email configuration from environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

# Check which email service to use
IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER', False)
USE_SENDGRID = IS_PRODUCTION and SENDGRID_API_KEY
USE_SMTP = not IS_PRODUCTION and all([EMAIL_USER, EMAIL_PASSWORD])

# Email configuration status
if USE_SENDGRID:
    print("✅ Using SendGrid for email (Production)")
    print(f"📧 SendGrid API Key: {'*' * len(SENDGRID_API_KEY) if SENDGRID_API_KEY else 'NOT SET'}")
elif USE_SMTP:
    print("✅ Using SMTP for email (Local Development)")
    print(f"📧 Using: {EMAIL_HOST}:{EMAIL_PORT}")
else:
    print("⚠️  Email service not configured - using console fallback")

# ✅ CRITICAL FIX: Universal database connection function
def get_auth_db_connection():
    """Get connection to authentication database (PostgreSQL on Render, SQLite locally)"""
    database_url = os.environ.get('DATABASE_URL')
    
    # Handle Render's PostgreSQL URL
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if database_url and database_url.startswith('postgresql://'):
        try:
            # PostgreSQL connection (Render Production)
            result = urlparse(database_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            print("✅ Connected to PostgreSQL database")
            return conn
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}, falling back to SQLite")
            # Fallback to SQLite
            return get_sqlite_connection()
    else:
        # SQLite connection (Local Development)
        return get_sqlite_connection()

def get_sqlite_connection():
    """Get SQLite connection for development"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_main_db_connection():
    """Get connection for main documents database"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if database_url and database_url.startswith('postgresql://'):
        try:
            # PostgreSQL for main database
            result = urlparse(database_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            return conn
        except Exception as e:
            print(f"❌ PostgreSQL connection error: {e}")
            return sqlite3.connect('shiksha_setu.db')
    else:
        # SQLite for development
        return sqlite3.connect('shiksha_setu.db')



# ✅ CRITICAL FIX: Universal database execution helper
def execute_db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """Execute database queries that work with both SQLite and PostgreSQL"""
    conn = get_auth_db_connection()
    try:
        cursor = conn.cursor()
        
        # Convert SQLite ? placeholders to PostgreSQL %s if needed
        if hasattr(conn, 'cursor') and not isinstance(conn, sqlite3.Connection):
            # PostgreSQL - convert ? to %s
            query = query.replace('?', '%s')
        
        cursor.execute(query, params)
        
        result = None
        if fetchone:
            row = cursor.fetchone()
            if row:
                if hasattr(cursor, 'description'):
                    # PostgreSQL - convert to dict
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                else:
                    # SQLite - already a dict due to row_factory
                    result = row
        elif fetchall:
            rows = cursor.fetchall()
            if hasattr(cursor, 'description'):
                # PostgreSQL - convert to list of dicts
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]
            else:
                # SQLite - already dicts
                result = rows
        
        if commit:
            conn.commit()
            if fetchone and 'RETURNING id' in query.upper():
                # Get the inserted ID for PostgreSQL
                if hasattr(conn, 'cursor'):
                    returning_result = cursor.fetchone()
                    if returning_result:
                        result = returning_result[0] if isinstance(returning_result, (list, tuple)) else returning_result
        
        return result
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        if hasattr(conn, 'rollback'):
            conn.rollback()
        raise e
    finally:
        conn.close()

def _display_verification_code_console(email, verification_code):
    """Display verification code in console"""
    print("\n" + "="*70)
    print("🎯 VERIFICATION CODE")
    print("="*70)
    print(f"📧 For: {email}")
    print(f"🔐 Code: {verification_code}")
    print("="*70)
    print("💡 Copy this code and paste it in the verification page")
    print("="*70 + "\n")

def send_verification_email_sendgrid(email, verification_code):
    """Send email using SendGrid API (for production)"""
    try:
        print(f"🔧 Using SendGrid to send email to: {email}")
        
        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        email_data = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "subject": "ShikshaSetu - Verify Your Email Address"
                }
            ],
            "from": {
                "email": "shikshasetu70@gmail.com",
                "name": "Shiksha Setu"
            },
            "content": [
                {
                    "type": "text/html",
                    "value": f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                            .code {{ font-size: 32px; font-weight: bold; color: #667eea; text-align: center; margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; letter-spacing: 3px; }}
                            .footer {{ margin-top: 30px; padding: 20px; background-color: #f8f9fa; text-align: center; border-radius: 0 0 10px 10px; }}
                            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>🎓 ShikshaSetu</h1>
                                <p>AI-Powered Education Document Search</p>
                            </div>
                            
                            <div class="content">
                                <h2>Verify Your Email Address</h2>
                                <p>Hello,</p>
                                <p>Thank you for registering with ShikshaSetu. Please use the verification code below to complete your registration:</p>
                                
                                <div class="code">{verification_code}</div>
                                
                                <div class="info">
                                    <p><strong>📝 Instructions:</strong></p>
                                    <p>1. Return to the ShikshaSetu verification page</p>
                                    <p>2. Enter the code above</p>
                                    <p>3. Complete your registration</p>
                                </div>
                                
                                <p><strong>⏰ This code will expire in 15 minutes.</strong></p>
                                <p>If you didn't create an account with ShikshaSetu, please ignore this email.</p>
                            </div>
                            
                            <div class="footer">
                                <p>Best regards,<br><strong>The ShikshaSetu Team</strong></p>
                                <p style="font-size: 12px; color: #666;">This is an automated message, please do not reply to this email.</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                }
            ]
        }
        
        response = requests.post(url, json=email_data, headers=headers)
        
        if response.status_code == 202:
            print(f"✅ SendGrid email sent successfully to {email}")
            return True
        else:
            print(f"❌ SendGrid API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ SendGrid request failed: {str(e)}")
        return False

def send_verification_email_smtp(email, verification_code):
    """Send email using SMTP (for local development)"""
    try:
        print(f"🔧 Using SMTP to send email to: {email}")
        print(f"🔧 Using SMTP: {EMAIL_HOST}:{EMAIL_PORT}")
        print(f"🔧 From: {EMAIL_USER}")
        
        # Create message
        subject = "ShikshaSetu - Verify Your Email Address"
        
        # HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .code {{ font-size: 32px; font-weight: bold; color: #667eea; text-align: center; margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; letter-spacing: 3px; }}
                .footer {{ margin-top: 30px; padding: 20px; background-color: #f8f9fa; text-align: center; border-radius: 0 0 10px 10px; }}
                .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 ShikshaSetu</h1>
                    <p>AI-Powered Education Document Search</p>
                </div>
                
                <div class="content">
                    <h2>Verify Your Email Address</h2>
                    <p>Hello,</p>
                    <p>Thank you for registering with ShikshaSetu. Please use the verification code below to complete your registration:</p>
                    
                    <div class="code">{verification_code}</div>
                    
                    <div class="info">
                        <p><strong>📝 Instructions:</strong></p>
                        <p>1. Return to the ShikshaSetu verification page</p>
                        <p>2. Enter the code above</p>
                        <p>3. Complete your registration</p>
                    </div>
                    
                    <p><strong>⏰ This code will expire in 15 minutes.</strong></p>
                    <p>If you didn't create an account with ShikshaSetu, please ignore this email.</p>
                </div>
                
                <div class="footer">
                    <p>Best regards,<br><strong>The ShikshaSetu Team</strong></p>
                    <p style="font-size: 12px; color: #666;">This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        ShikshaSetu - Verify Your Email Address
        
        Hello,
        
        Thank you for registering with ShikshaSetu. Please use the verification code below to complete your registration:
        
        Verification Code: {verification_code}
        
        Instructions:
        1. Return to the ShikshaSetu verification page
        2. Enter the code above
        3. Complete your registration
        
        This code will expire in 15 minutes.
        
        If you didn't create an account with ShikshaSetu, please ignore this email.
        
        Best regards,
        The ShikshaSetu Team
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = email
        
        # Attach both HTML and plain text versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email with timeout
        print("📧 Connecting to SMTP server...")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10)  # 10 second timeout
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("📧 Logging in...")
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        print("📧 Sending email...")
        server.send_message(msg)
        server.quit()
        print("✅ SMTP email sent successfully!")
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP Authentication Failed - Check email credentials")
        return False
    except smtplib.SMTPConnectError:
        print("❌ SMTP Connection Failed - Check host and port")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected SMTP error: {str(e)}")
        return False

def send_verification_email_async(email, verification_code):
    """Send email in background to avoid timeouts"""
    def email_worker():
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 Email attempt {attempt + 1} for {email}")
                
                # Choose email service based on environment
                if USE_SENDGRID:
                    success = send_verification_email_sendgrid(email, verification_code)
                elif USE_SMTP:
                    success = send_verification_email_smtp(email, verification_code)
                else:
                    success = False
                
                if success:
                    print(f"✅ Email sent successfully to {email}")
                    return
                else:
                    print(f"⚠️ Email attempt {attempt + 1} failed for {email}")
                    
            except Exception as e:
                print(f"❌ Email attempt {attempt + 1} error: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
        
        # If all retries fail, use console fallback
        print(f"❌ All email attempts failed for {email}, using console fallback")
        _display_verification_code_console(email, verification_code)
    
    # Start email in background thread if email service is configured
    if USE_SENDGRID or USE_SMTP:
        email_thread = threading.Thread(target=email_worker)
        email_thread.daemon = True
        email_thread.start()
        print(f"🔄 Background email process started for {email}")
        return True
    else:
        print("🔄 Email not configured, using console fallback")
        _display_verification_code_console(email, verification_code)
        return True

@app.route('/test-email')
def test_email():
    """Test email sending functionality"""
    if not (USE_SENDGRID or USE_SMTP):
        return '''
        <h1>❌ Email Not Configured</h1>
        <p>Please set email environment variables.</p>
        <p><strong>For Local Development:</strong> EMAIL_USER and EMAIL_PASSWORD</p>
        <p><strong>For Production:</strong> SENDGRID_API_KEY</p>
        <a href="/">Go Home</a>
        '''
    
    test_email = EMAIL_USER or "test@example.com"  # Send test to yourself or test address
    test_code = "987654"
    
    print("🧪 Testing email configuration...")
    print(f"📧 Environment: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}")
    
    if USE_SENDGRID:
        print(f"📧 Using: SendGrid")
        print(f"📧 SENDGRID_API_KEY: {'*' * len(SENDGRID_API_KEY) if SENDGRID_API_KEY else 'NOT SET'}")
    elif USE_SMTP:
        print(f"📧 Using: SMTP")
        print(f"📧 EMAIL_HOST: {EMAIL_HOST}")
        print(f"📧 EMAIL_PORT: {EMAIL_PORT}")
        print(f"📧 EMAIL_USER: {EMAIL_USER}")
        print(f"📧 EMAIL_PASSWORD: {'*' * len(EMAIL_PASSWORD) if EMAIL_PASSWORD else 'NOT SET'}")
    
    # Test the actual email sending
    print("🔄 Attempting to send test email...")
    
    if USE_SENDGRID:
        result = send_verification_email_sendgrid(test_email, test_code)
    elif USE_SMTP:
        result = send_verification_email_smtp(test_email, test_code)
    else:
        result = False
    
    if result:
        return f'''
        <h1>✅ Email Test SUCCESSFUL!</h1>
        <p>Check your email inbox ({test_email}) for the test message.</p>
        <p>Test code sent: <strong>987654</strong></p>
        <p><strong>Service Used:</strong> {'SendGrid' if USE_SENDGRID else 'SMTP'}</p>
        <a href="/register">Go to Registration</a>
        '''
    else:
        return f'''
        <h1>❌ Email Test FAILED</h1>
        <p>Check the Flask console for error details.</p>
        <p><strong>Service Used:</strong> {'SendGrid' if USE_SENDGRID else 'SMTP'}</p>
        <a href="/">Go Home</a>
        '''

# Initialize authentication database
init_auth_db()

# Pre-load documents for NLP processing with error handling
try:
    documents = db_manager.get_all_documents()
    print(f"Loaded {len(documents)} documents from database")
    
    if documents and len(documents) > 0:
        nlp_processor.fit_documents(documents)
        print("NLP processor trained successfully")
    else:
        print("No documents found in database")
        documents = []
        
except Exception as e:
    print(f"Error during initialization: {e}")
    print(f"Initialization traceback: {traceback.format_exc()}")
    documents = []

# ✅ CRITICAL FIX: Updated Authentication Routes with PostgreSQL support

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page - PostgreSQL compatible"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        
        print(f"Registration attempt - Username: {username}, Email: {email}")
        
        # Enhanced validation
        if not username or not email:
            flash('Please fill in all fields', 'error')
            return render_template('register.html', username=username, email=email)
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('register.html', username=username, email=email)
        
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            flash('Please enter a valid email address', 'error')
            return render_template('register.html', username=username, email=email)
        
        # Check if user already exists
        existing_user = execute_db_query(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (username, email), 
            fetchone=True
        )
        
        if existing_user:
            if existing_user['username'] == username:
                flash('Username already exists', 'error')
            else:
                flash('Email already exists', 'error')
            return render_template('register.html', username=username, email=email)
        
        # Generate simpler verification code (6-digit number)
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        token_expiry = datetime.now() + timedelta(hours=24)
        
        print(f"Generated verification code: {verification_code} for {email}")
        
        # Store user data (without password yet)
        try:
            # Use the universal database function
            user_id = execute_db_query(
                'INSERT INTO users (username, email, verification_token, token_expiry) VALUES (?, ?, ?, ?) RETURNING id',
                (username, email, verification_code, token_expiry),
                fetchone=True,
                commit=True
            )
            
            if user_id:
                if isinstance(user_id, dict) and 'id' in user_id:
                    user_id = user_id['id']
                print(f"User stored in database with ID: {user_id}")
            else:
                # Fallback for SQLite
                conn = get_auth_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT last_insert_rowid()')
                user_id = cursor.fetchone()[0]
                conn.close()
                print(f"User stored in SQLite with ID: {user_id}")
            
        except Exception as db_error:
            print(f"Database error: {db_error}")
            flash('Error creating user account. Please try again.', 'error')
            return render_template('register.html', username=username, email=email)
        
        # Send verification email using async method
        if send_verification_email_async(email, verification_code):
            session['pending_user_id'] = user_id
            session['pending_email'] = email
            session['pending_username'] = username
            session['verification_code'] = verification_code
            
            if USE_SENDGRID or USE_SMTP:
                flash('Verification code sent! Please check your email.', 'success')
            else:
                flash('Verification code generated! Please check the console.', 'info')
            
            print(f"Redirecting to verification page for user {user_id}")
            return redirect(url_for('verify_email'))
        else:
            flash('Error sending verification email. Please try again.', 'error')
            return render_template('register.html', username=username, email=email)
    
    return render_template('register.html')

@app.route('/verify-email', methods=['GET', 'POST'])
@app.route('/verify-email/<token>', methods=['GET'])
def verify_email(token=None):
    """Email verification page"""
    # Check if we have a pending registration
    if 'pending_user_id' not in session and not token:
        flash('Session expired. Please register again.', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'GET' and token:
        # Handle direct link verification
        user = execute_db_query(
            'SELECT * FROM users WHERE verification_token = ? AND token_expiry > ?',
            (token, datetime.now()),
            fetchone=True
        )
        
        if user:
            session['verified_user'] = user['id']
            session['verified_email'] = user['email']
            flash('Email verified successfully! Please create your password.', 'success')
            return redirect(url_for('create_password'))
        else:
            flash('Invalid or expired verification link', 'error')
            return redirect(url_for('register'))
    
    if request.method == 'POST':
        verification_code = request.form.get('verification_code', '').strip()
        
        if not verification_code:
            flash('Please enter the verification code', 'error')
            return render_template('verify_email.html')
        
        # Get user data from session
        user_id = session.get('pending_user_id')
        stored_code = session.get('verification_code')
        
        print(f"Verification attempt - Entered: {verification_code}, Stored: {stored_code}")
        
        if not user_id or not stored_code:
            flash('Session expired. Please register again.', 'error')
            return redirect(url_for('register'))
        
        # Verify code (exact match)
        if verification_code == stored_code:
            print("✅ Verification SUCCESSFUL!")
            # Mark user as verified and proceed to password creation
            session['verified_user'] = user_id
            session['verified_email'] = session.get('pending_email')
            
            # Update database
            execute_db_query(
                'UPDATE users SET email_verified = TRUE WHERE id = ?',
                (user_id,),
                commit=True
            )
            
            # Clear pending session data
            session.pop('pending_user_id', None)
            session.pop('pending_email', None)
            session.pop('pending_username', None)
            session.pop('verification_code', None)
            
            flash('Email verified successfully! Please create your password.', 'success')
            return redirect(url_for('create_password'))
        else:
            print("❌ Verification FAILED!")
            flash('Invalid verification code. Please try again.', 'error')
    
    # Pre-fill email for display
    email = session.get('pending_email', '')
    return render_template('verify_email.html', email=email)

@app.route('/create-password', methods=['GET', 'POST'])
def create_password():
    """Create password after email verification"""
    if 'verified_user' not in session:
        flash('Please complete email verification first', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('create_password.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('create_password.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('create_password.html')
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Update user with password
        try:
            execute_db_query(
                'UPDATE users SET password_hash = ?, email_verified = TRUE WHERE id = ?',
                (password_hash, session['verified_user']),
                commit=True
            )
            
            # Get user info for session
            user = execute_db_query(
                'SELECT * FROM users WHERE id = ?',
                (session['verified_user'],),
                fetchone=True
            )
            
            if user:
                # ✅ CRITICAL FIX: Make session permanent and clear old session
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                session.permanent = True  # This makes the session last 7 days
                
                flash('Account created successfully! Welcome to ShikshaSetu.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Error creating account. Please try again.', 'error')
                return redirect(url_for('register'))
                
        except Exception as e:
            print(f"Password creation error: {e}")
            flash('Error creating account. Please try again.', 'error')
            return redirect(url_for('register'))
    
    return render_template('create_password.html')

# ✅ CRITICAL FIX: Updated login with session persistence
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page with persistent sessions"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = execute_db_query(
            'SELECT * FROM users WHERE (username = ? OR email = ?) AND password_hash = ? AND email_verified = TRUE',
            (username_or_email, username_or_email, password_hash),
            fetchone=True
        )
        
        if user:
            # ✅ CRITICAL FIX: Set permanent session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session.permanent = True  # This makes the session persist for 7 days
            
            flash('Login successful!', 'success')
            
            # Redirect to intended page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or email not verified', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires login"""
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    # Simple user data for the dashboard
    user_data = {
        'username': session['username'],
        'email': session['email']
    }
    
    return render_template('dashboard.html', user=user_data)

# Debug routes to check database status
@app.route('/debug/users')
def debug_users():
    """Debug route to check all users in database"""
    users = execute_db_query('SELECT id, username, email, email_verified, created_at FROM users', fetchall=True)
    return jsonify({
        'total_users': len(users) if users else 0,
        'users': users or []
    })

@app.route('/debug/database-type')
def debug_database_type():
    """Check which database is being used"""
    conn = get_auth_db_connection()
    db_type = "PostgreSQL" if hasattr(conn, 'cursor') and not isinstance(conn, sqlite3.Connection) else "SQLite"
    conn.close()
    return jsonify({'database_type': db_type})

# Existing Application Routes (keep all your existing routes below exactly as they are)
@app.route('/')
def home():
    """Home page with welcome message"""
    return render_template('index.html')

@app.route('/search')
def search_page():
    """Search interface page - requires login"""
    if 'user_id' not in session:
        flash('Please login to access search features', 'error')
        return redirect(url_for('login', next=url_for('search_page')))
    return render_template('search.html')

@app.route('/api/search', methods=['POST'])
def search_documents():
    """API endpoint for document search - requires login"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        print("=== SEARCH API CALLED ===")
        data = request.get_json()
        print("Received data:", data)
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        query = data.get('query', '')
        doc_type = data.get('document_type', '')
        category = data.get('category', '')
        
        print(f"Search parameters - query: '{query}', type: '{doc_type}', category: '{category}'")
        
        # Basic keyword search
        print("Performing basic search...")
        basic_results = db_manager.search_documents(
            query=query if query else None,
            doc_type=doc_type if doc_type else None,
            category=category if category else None
        )
        print(f"Basic search found {len(basic_results)} results")
        
        # Semantic search if query is provided
        semantic_results = []
        if query:
            print("Performing semantic search...")
            try:
                semantic_results = nlp_processor.semantic_search(query, documents)
                print(f"Semantic search found {len(semantic_results)} results")
            except Exception as nlp_error:
                print(f"Semantic search failed: {nlp_error}")
                print(f"Semantic search traceback: {traceback.format_exc()}")
                # Continue with basic results only
        
        # Combine and deduplicate results
        all_results = basic_results + semantic_results
        unique_results = {}
        
        for result in all_results:
            doc_id = result['id']
            if doc_id not in unique_results:
                unique_results[doc_id] = result
            else:
                # Keep the one with higher similarity score if available
                current_score = unique_results[doc_id].get('similarity_score', 0)
                new_score = result.get('similarity_score', 0)
                if new_score > current_score:
                    unique_results[doc_id] = result
        
        final_results = list(unique_results.values())
        
        # Sort by relevance (similarity score) or title
        final_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        print(f"Returning {len(final_results)} final results")
        
        return jsonify({
            'success': True,
            'results': final_results,
            'count': len(final_results)
        })
        
    except Exception as e:
        print(f"=== SEARCH ERROR ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': f'{type(e).__name__}: {str(e)}'
        }), 500

@app.route('/api/documents')
def get_all_documents_api():
    """API endpoint to get all documents - requires login"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        documents = db_manager.get_all_documents()
        return jsonify({
            'success': True,
            'documents': documents
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/document/<int:document_id>')
def document_detail(document_id):
    """Document detail page - requires login"""
    if 'user_id' not in session:
        flash('Please login to view document details', 'error')
        return redirect(url_for('login', next=url_for('document_detail', document_id=document_id)))
        
    try:
        # Get the specific document
        conn = get_main_db_connection()
        cursor = conn.cursor()
        
        if hasattr(conn, 'cursor') and not isinstance(conn, sqlite3.Connection):
            # PostgreSQL
            cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        else:
            # SQLite
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            
        document_data = cursor.fetchone()
        conn.close()
        
        if document_data:
            # Convert to dictionary
            if hasattr(cursor, 'description'):
                # PostgreSQL
                columns = [desc[0] for desc in cursor.description]
                document = dict(zip(columns, document_data))
            else:
                # SQLite
                columns = ['id', 'title', 'content', 'document_type', 'category', 'department', 'created_date', 'keywords', 'document_url']
                document = dict(zip(columns, document_data))
            return render_template('document_detail.html', document=document)
        else:
            return "Document not found", 404
    except Exception as e:
        print(f"Document detail error: {e}")
        return "Error loading document", 500

@app.route('/api/document/<int:document_id>')
def get_document_api(document_id):
    """API endpoint to get specific document - requires login"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        conn = get_main_db_connection()
        cursor = conn.cursor()
        
        if hasattr(conn, 'cursor') and not isinstance(conn, sqlite3.Connection):
            cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        else:
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            
        document_data = cursor.fetchone()
        conn.close()
        
        if document_data:
            if hasattr(cursor, 'description'):
                columns = [desc[0] for desc in cursor.description]
                document = dict(zip(columns, document_data))
            else:
                columns = ['id', 'title', 'content', 'document_type', 'category', 'department', 'created_date', 'keywords', 'document_url']
                document = dict(zip(columns, document_data))
            return jsonify({'success': True, 'document': document})
        else:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/about')
def about():
    """About page - publicly accessible"""
    return render_template('about.html')

# Static file routes
@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('static/css', filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Starting ShikshaSetu Application...")
    print(f"📍 Access the application at: http://localhost:{port}")
    print(f"🔧 Environment: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}")
    
    if USE_SENDGRID:
        print("📧 Email service: SendGrid (Production)")
    elif USE_SMTP:
        print("📧 Email service: SMTP (Local Development)")
    else:
        print("📧 Email service: CONSOLE FALLBACK")
    
    # Run in production mode
    app.run(host='0.0.0.0', port=port, debug=False)