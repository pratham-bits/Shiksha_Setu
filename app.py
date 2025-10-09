import sqlite3
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



load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Initialize components with error handling
db_manager = DatabaseManager()
nlp_processor = NLPProcessor()

# Email configuration from environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Check if email is configured
EMAIL_CONFIGURED = all([EMAIL_USER, EMAIL_PASSWORD])
if EMAIL_CONFIGURED:
    print("✅ Email service configured")
else:
    print("⚠️  Email service not configured - using console fallback")

def init_auth_db():
    """Initialize authentication database"""
    conn = sqlite3.connect('users.db')
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
    
    conn.commit()
    conn.close()

def get_auth_db_connection():
    """Get connection to authentication database"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def send_verification_email_real(email, verification_code):
    """Actually send verification email via SMTP"""
    try:
        print(f"🔧 Attempting to send email to: {email}")
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
                .code {{ font-size: 42px; font-weight: bold; color: #667eea; text-align: center; margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; letter-spacing: 5px; }}
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
                        <p>1. Go back to the ShikshaSetu verification page</p>
                        <p>2. Enter the code above</p>
                        <p>3. Complete your registration</p>
                    </div>
                    
                    <p><strong>⏰ This code will expire in 24 hours.</strong></p>
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
        1. Go back to the ShikshaSetu verification page
        2. Enter the code above
        3. Complete your registration
        
        This code will expire in 24 hours.
        
        If you didn't create an account with ShikshaSetu, please ignore this email.
        
        Best regards,
        The ShikshaSetu Team
        
        This is an automated message, please do not reply to this email.
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
        
        # Send email
        print("📧 Connecting to SMTP server...")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("📧 Logging in...")
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        print("📧 Sending email...")
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

def send_verification_email(email, verification_code):
    """Try real email first, fall back to console if failed"""
    
    # First try real email
    print("🔄 Attempting to send real email...")
    if send_verification_email_real(email, verification_code):
        return True
    
    # If real email fails, fall back to console
    print("🔄 Falling back to console display...")
    print("\n" + "="*70)
    print("🎯 VERIFICATION CODE (Email failed - check console)")
    print("="*70)
    print(f"📧 Intended for: {email}")
    print(f"🔐 Verification Code: {verification_code}")
    print("="*70)
    print("💡 Copy this code and paste it in the verification page")
    print("="*70 + "\n")
    
    # Still show a flash message
    flash('Email service temporarily unavailable. Please check the console for your verification code.', 'warning')
    return True

@app.route('/test-email')
def test_email():
    """Test email sending functionality"""
    test_email = "your-actual-email@gmail.com"  # Change to your actual email
    test_code = "987654"
    
    print("🧪 Testing email configuration...")
    print(f"📧 EMAIL_HOST: {EMAIL_HOST}")
    print(f"📧 EMAIL_PORT: {EMAIL_PORT}")
    print(f"📧 EMAIL_USER: {EMAIL_USER}")
    print(f"📧 EMAIL_PASSWORD: {'*' * len(EMAIL_PASSWORD) if EMAIL_PASSWORD else 'NOT SET'}")
    
    # Test the actual email sending
    print("🔄 Attempting to send test email...")
    result = send_verification_email_real(test_email, test_code)
    
    if result:
        return '''
        <h1>✅ Email Test SUCCESSFUL!</h1>
        <p>Check your email inbox for the test message.</p>
        <p>Test code sent: <strong>987654</strong></p>
        <a href="/register">Go to Registration</a>
        '''
    else:
        return '''
        <h1>❌ Email Test FAILED</h1>
        <p>Check the Flask console for error details.</p>
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

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
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
        conn = get_auth_db_connection()
        existing_user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (username, email)
        ).fetchone()
        
        if existing_user:
            if existing_user['username'] == username:
                flash('Username already exists', 'error')
            else:
                flash('Email already exists', 'error')
            conn.close()
            return render_template('register.html', username=username, email=email)
        
        # Generate simpler verification code (6-digit number)
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        token_expiry = datetime.now() + timedelta(hours=24)
        
        print(f"Generated verification code: {verification_code} for {email}")
        
        # Store user data (without password yet)
        try:
            conn.execute(
                'INSERT INTO users (username, email, verification_token, token_expiry) VALUES (?, ?, ?, ?)',
                (username, email, verification_code, token_expiry)
            )
            conn.commit()
            user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.close()
            
            print(f"User stored in database with ID: {user_id}")
            
        except Exception as db_error:
            print(f"Database error: {db_error}")
            flash('Error creating user account. Please try again.', 'error')
            conn.close()
            return render_template('register.html', username=username, email=email)
        
        # Send verification email (uses real email with fallback to console)
        if send_verification_email(email, verification_code):
            session['pending_user_id'] = user_id
            session['pending_email'] = email
            session['pending_username'] = username
            session['verification_code'] = verification_code
            
            flash('Verification code sent! Please check your email.', 'success')
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
        conn = get_auth_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE verification_token = ? AND token_expiry > ?',
            (token, datetime.now())
        ).fetchone()
        
        if user:
            session['verified_user'] = user['id']
            session['verified_email'] = user['email']
            conn.close()
            flash('Email verified successfully! Please create your password.', 'success')
            return redirect(url_for('create_password'))
        else:
            flash('Invalid or expired verification link', 'error')
            conn.close()
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
            conn = get_auth_db_connection()
            conn.execute(
                'UPDATE users SET email_verified = TRUE WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
            
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
        conn = get_auth_db_connection()
        try:
            conn.execute(
                'UPDATE users SET password_hash = ?, email_verified = TRUE WHERE id = ?',
                (password_hash, session['verified_user'])
            )
            conn.commit()
            
            # Get user info for session
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['verified_user'],)).fetchone()
            conn.close()
            
            if user:
                # Clear session and log user in
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                
                flash('Account created successfully! Welcome to ShikshaSetu.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Error creating account. Please try again.', 'error')
                return redirect(url_for('register'))
                
        except Exception as e:
            print(f"Password creation error: {e}")
            flash('Error creating account. Please try again.', 'error')
            conn.close()
            return redirect(url_for('register'))
    
    return render_template('create_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_auth_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE (username = ? OR email = ?) AND password_hash = ? AND email_verified = TRUE',
            (username_or_email, username_or_email, password_hash)
        ).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
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

# Existing Application Routes
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
        conn = sqlite3.connect('shiksha_setu.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        document_data = cursor.fetchone()
        conn.close()
        
        if document_data:
            # Convert to dictionary
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
        conn = sqlite3.connect('shiksha_setu.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        document_data = cursor.fetchone()
        conn.close()
        
        if document_data:
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
    print("🔧 Running in production mode")
    if EMAIL_CONFIGURED:
        print("📧 Email service: ENABLED")
    else:
        print("📧 Email service: DISABLED (using console fallback)")
    
    # Run in production mode
    app.run(host='0.0.0.0', port=port, debug=False)