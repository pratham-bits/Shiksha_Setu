import sqlite3
import pandas as pd
from datetime import datetime
import os


class DatabaseManager:
    def __init__(self, db_path=None):
        # Use absolute path for deployment compatibility
        if db_path is None:
            self.db_path = os.path.join(os.path.dirname(__file__), 'shiksha_setu.db')
        else:
            self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize database with comprehensive higher education documents"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we need to migrate from old schema
            cursor.execute("PRAGMA table_info(documents)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            # Enhanced documents table with additional fields for better search
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
            
            # Migrate old schema to new schema if needed
            if 'status' not in existing_columns:
                print("🔄 Migrating database schema to new version...")
                self._migrate_database(cursor, existing_columns)
            
            # Create dedicated keywords table for efficient searching
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
            
            # Create search index table for full-text search
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    search_text TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON document_keywords(keyword)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department)')
            
            # Only create status index if column exists
            if 'status' in existing_columns or 'status' in [col[1] for col in cursor.execute("PRAGMA table_info(documents)").fetchall()]:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)')
            
            # Only create priority index if column exists
            if 'search_priority' in existing_columns or 'search_priority' in [col[1] for col in cursor.execute("PRAGMA table_info(documents)").fetchall()]:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_priority ON documents(search_priority)')
            
            # Check if we have data
            cursor.execute("SELECT COUNT(*) FROM documents")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("📥 Inserting comprehensive higher education documents...")
                self._insert_comprehensive_documents(cursor)
            else:
                print(f"📊 Database contains {count} documents")
            
            conn.commit()
            conn.close()
            print("✅ Database initialized successfully with comprehensive documents")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
    
    def _migrate_database(self, cursor, existing_columns):
        """Migrate from old database schema to new one"""
        try:
            # Add missing columns to existing table
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
        """Insert 40 comprehensive higher education documents"""
        comprehensive_documents = [
            # Policy Documents (5)
            {
                'title': 'National Education Policy 2020 - Complete Document',
                'content': 'The National Education Policy 2020 is a comprehensive framework for elementary to higher education in India. It focuses on multidisciplinary education, flexibility in learning, internationalization of education, and promoting Indian languages and culture.',
                'document_type': 'Policy Document',
                'category': 'National Policy',
                'sub_category': 'Higher Education Reform',
                'department': 'Ministry of Education',
                'created_date': '2020-07-29',
                'last_updated': '2020-07-29',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'NEP 2020,education policy,India,higher education,school education,multidisciplinary,internationalization,academic bank of credits,multiple entry exit,regulation framework,curriculum reform,assessment reform',
                'document_url': 'https://www.education.gov.in/sites/upload_files/mhrd/files/NEP_Final_English_0.pdf',
                'search_priority': 5,
                'full_text_content': 'National Education Policy 2020 NEP comprehensive framework elementary to higher education India multidisciplinary education flexibility learning internationalization promoting Indian languages culture academic bank of credits multiple entry exit regulatory framework higher education commission'
            },
            {
                'title': 'National Policy on Skill Development and Entrepreneurship 2015',
                'content': 'Policy framework to rapidly scale up skill development efforts in India and link them to employment opportunities.',
                'document_type': 'Policy Document',
                'category': 'Skill Development',
                'sub_category': 'Entrepreneurship',
                'department': 'Ministry of Skill Development',
                'created_date': '2015-07-15',
                'last_updated': '2015-07-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'skill development,entrepreneurship,vocational training,employment,NSDC,skill India',
                'document_url': 'https://www.skilldevelopment.gov.in/national-policy.html',
                'search_priority': 4,
                'full_text_content': 'National Policy Skill Development Entrepreneurship framework scale up skill development India link employment opportunities vocational training NSDC Skill India'
            },
            {
                'title': 'Digital India Policy Framework for Education',
                'content': 'Comprehensive policy for integrating digital technologies in education sector across India.',
                'document_type': 'Policy Document',
                'category': 'Digital Education',
                'sub_category': 'Technology Integration',
                'department': 'Ministry of Education',
                'created_date': '2022-03-01',
                'last_updated': '2022-03-01',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'digital India,education technology,digital infrastructure,e-learning,online education,digital classrooms',
                'document_url': 'https://www.education.gov.in/digital-education-policy',
                'search_priority': 4,
                'full_text_content': 'Digital India Policy Framework education integrating digital technologies education sector India digital infrastructure e-learning online education digital classrooms'
            },
            {
                'title': 'National Policy for Overseas Employment 2022',
                'content': 'Policy framework for promoting overseas employment opportunities for Indian students and professionals.',
                'document_type': 'Policy Document',
                'category': 'International Education',
                'sub_category': 'Overseas Employment',
                'department': 'Ministry of External Affairs',
                'created_date': '2022-09-15',
                'last_updated': '2022-09-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'overseas employment,international jobs,global opportunities,employment abroad,skill export',
                'document_url': 'https://www.mea.gov.in/overseas-employment-policy.htm',
                'search_priority': 3,
                'full_text_content': 'National Policy Overseas Employment framework promoting overseas employment opportunities Indian students professionals international jobs global opportunities'
            },
            {
                'title': 'Startup India Policy Framework for Educational Institutions',
                'content': 'Policy to promote startup culture and innovation in higher education institutions.',
                'document_type': 'Policy Document',
                'category': 'Innovation & Entrepreneurship',
                'sub_category': 'Startup Ecosystem',
                'department': 'Ministry of Education',
                'created_date': '2023-01-10',
                'last_updated': '2023-01-10',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'startup India,innovation,entrepreneurship,incubation centers,higher education institutions',
                'document_url': 'https://www.education.gov.in/startup-policy',
                'search_priority': 3,
                'full_text_content': 'Startup India Policy Framework promote startup culture innovation higher education institutions incubation centers entrepreneurship development'
            },

            # Regulations (8)
            {
                'title': 'University Grants Commission Regulations 2023',
                'content': 'Latest UGC regulations governing higher education institutions, including accreditation standards, faculty qualifications, and institutional governance.',
                'document_type': 'Regulation',
                'category': 'Higher Education',
                'sub_category': 'Accreditation Standards',
                'department': 'University Grants Commission',
                'created_date': '2023-01-15',
                'last_updated': '2023-01-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'UGC,regulations,accreditation,quality standards,faculty qualifications,governance,higher education institutions,universities,colleges,compliance,approval process',
                'document_url': 'https://www.ugc.gov.in/regulations/',
                'search_priority': 5,
                'full_text_content': 'University Grants Commission UGC regulations governing higher education institutions accreditation standards faculty qualifications institutional governance quality assurance compliance requirements universities colleges approval process'
            },
            {
                'title': 'AICTE Approval Process Handbook 2023-24',
                'content': 'Comprehensive handbook detailing the approval process for technical institutions and programs in India.',
                'document_type': 'Regulation',
                'category': 'Technical Education',
                'sub_category': 'Approval Process',
                'department': 'AICTE',
                'created_date': '2023-03-01',
                'last_updated': '2023-03-01',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'AICTE,technical education,engineering,management,pharmacy,architecture,approval process,quality standards,inspection,norms,program approval',
                'document_url': 'https://www.aicte-india.org/approval-process',
                'search_priority': 5,
                'full_text_content': 'AICTE Approval Process Handbook technical institutions programs India engineering management pharmacy architecture quality standards inspection norms program approval'
            },
            {
                'title': 'Medical Council of India Regulations 2023',
                'content': 'Regulations governing medical education institutions and programs in India.',
                'document_type': 'Regulation',
                'category': 'Medical Education',
                'sub_category': 'Medical Standards',
                'department': 'National Medical Commission',
                'created_date': '2023-02-20',
                'last_updated': '2023-02-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'MCI,medical education,MBBS,medical colleges,hospital standards,medical curriculum',
                'document_url': 'https://www.nmc.org.in/regulations',
                'search_priority': 4,
                'full_text_content': 'Medical Council India Regulations governing medical education institutions programs MBBS medical colleges hospital standards medical curriculum'
            },
            {
                'title': 'Bar Council of India Legal Education Rules',
                'content': 'Rules and regulations for legal education and law colleges in India.',
                'document_type': 'Regulation',
                'category': 'Legal Education',
                'sub_category': 'Law Colleges',
                'department': 'Bar Council of India',
                'created_date': '2023-01-30',
                'last_updated': '2023-01-30',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'BCI,legal education,law colleges,LLB,advocate,legal practice',
                'document_url': 'https://www.barcouncilofindia.org/legal-education-rules',
                'search_priority': 4,
                'full_text_content': 'Bar Council India Legal Education Rules regulations legal education law colleges LLB advocate legal practice standards'
            },
            {
                'title': 'National Council for Teacher Education Regulations',
                'content': 'Regulations governing teacher education programs and institutions in India.',
                'document_type': 'Regulation',
                'category': 'Teacher Education',
                'sub_category': 'Teacher Training',
                'department': 'NCTE',
                'created_date': '2023-03-15',
                'last_updated': '2023-03-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'NCTE,teacher education,B.Ed,D.El.Ed,teacher training,education colleges',
                'document_url': 'https://www.ncte.gov.in/regulations',
                'search_priority': 4,
                'full_text_content': 'National Council Teacher Education Regulations governing teacher education programs institutions BEd DElEd teacher training education colleges'
            },
            {
                'title': 'Distance Education Bureau Regulations 2023',
                'content': 'Regulations for open and distance learning programs in higher education.',
                'document_type': 'Regulation',
                'category': 'Distance Education',
                'sub_category': 'ODL Programs',
                'department': 'UGC',
                'created_date': '2023-02-10',
                'last_updated': '2023-02-10',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'DEB,distance education,online learning,ODL,correspondence courses,open learning',
                'document_url': 'https://www.ugc.gov.in/deb-regulations',
                'search_priority': 3,
                'full_text_content': 'Distance Education Bureau Regulations open distance learning programs higher education ODL correspondence courses open learning standards'
            },
            {
                'title': 'Foreign Educational Institutions Regulations',
                'content': 'Regulations governing the operation of foreign educational institutions in India and collaboration with Indian institutions.',
                'document_type': 'Regulation',
                'category': 'International Collaboration',
                'sub_category': 'Foreign Institutions',
                'department': 'University Grants Commission',
                'created_date': '2023-01-20',
                'last_updated': '2023-01-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'foreign universities,international collaboration,twinning programs,joint degrees,cross-border education,quality assurance,regulatory compliance,offshore campuses',
                'document_url': 'https://www.ugc.gov.in/foreigninstitutions/',
                'search_priority': 4,
                'full_text_content': 'Foreign educational institutions regulations operation India collaboration Indian institutions twinning programs joint degrees cross-border education quality assurance regulatory framework offshore campuses'
            },
            {
                'title': 'Pharmacy Education Regulations 2023',
                'content': 'Regulations for pharmacy education programs and institutions in India.',
                'document_type': 'Regulation',
                'category': 'Pharmacy Education',
                'sub_category': 'Pharmacy Standards',
                'department': 'Pharmacy Council of India',
                'created_date': '2023-03-20',
                'last_updated': '2023-03-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'PCI,pharmacy education,B.Pharm,D.Pharm,pharmacy colleges,drug regulations',
                'document_url': 'https://www.pci.nic.in/regulations',
                'search_priority': 3,
                'full_text_content': 'Pharmacy Education Regulations pharmacy education programs institutions BPharm DPharm pharmacy colleges drug regulations standards'
            },

            # Guidelines (7)
            {
                'title': 'Online Education Guidelines and Standards 2023',
                'content': 'Comprehensive guidelines for online and distance learning programs in higher education institutions.',
                'document_type': 'Guidelines',
                'category': 'Digital Education',
                'sub_category': 'Online Learning',
                'department': 'University Grants Commission',
                'created_date': '2023-02-15',
                'last_updated': '2023-02-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'online education,distance learning,digital education,MOOCs,SWAYAM,learning management system,quality standards,virtual learning,blended learning',
                'document_url': 'https://www.ugc.gov.in/online-guidelines',
                'search_priority': 4,
                'full_text_content': 'Online education guidelines standards distance learning programs higher education institutions MOOCs SWAYAM learning management system quality assurance digital infrastructure virtual learning blended learning'
            },
            {
                'title': 'Research Methodology Guidelines for PhD Programs',
                'content': 'Standard guidelines for research methodology and thesis preparation in PhD programs.',
                'document_type': 'Guidelines',
                'category': 'Research Education',
                'sub_category': 'PhD Programs',
                'department': 'UGC',
                'created_date': '2023-01-25',
                'last_updated': '2023-01-25',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'research methodology,PhD guidelines,thesis preparation,research ethics,plagiarism check',
                'document_url': 'https://www.ugc.gov.in/phd-guidelines',
                'search_priority': 4,
                'full_text_content': 'Research Methodology Guidelines PhD programs research methodology thesis preparation research ethics plagiarism check standards'
            },
            {
                'title': 'Anti-Ragging Guidelines for Higher Education Institutions',
                'content': 'Comprehensive guidelines to prevent and address ragging in educational institutions.',
                'document_type': 'Guidelines',
                'category': 'Student Welfare',
                'sub_category': 'Anti-Ragging',
                'department': 'UGC',
                'created_date': '2023-02-28',
                'last_updated': '2023-02-28',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'anti-ragging,student safety,campus security,ragging prevention,student welfare',
                'document_url': 'https://www.ugc.gov.in/anti-ragging',
                'search_priority': 4,
                'full_text_content': 'Anti Ragging Guidelines higher education institutions prevent address ragging student safety campus security ragging prevention student welfare'
            },
            {
                'title': 'Gender Sensitization Guidelines for Campuses',
                'content': 'Guidelines for creating gender-sensitive environments in higher education institutions.',
                'document_type': 'Guidelines',
                'category': 'Student Welfare',
                'sub_category': 'Gender Equality',
                'department': 'UGC',
                'created_date': '2023-03-10',
                'last_updated': '2023-03-10',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'gender sensitization,gender equality,campus safety,women safety,sexual harassment',
                'document_url': 'https://www.ugc.gov.in/gender-guidelines',
                'search_priority': 3,
                'full_text_content': 'Gender Sensitization Guidelines creating gender-sensitive environments higher education institutions campus safety women safety sexual harassment prevention'
            },
            {
                'title': 'Green Campus Guidelines for Educational Institutions',
                'content': 'Guidelines for developing environmentally sustainable and green campuses.',
                'document_type': 'Guidelines',
                'category': 'Infrastructure',
                'sub_category': 'Sustainable Campus',
                'department': 'UGC',
                'created_date': '2023-02-20',
                'last_updated': '2023-02-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'green campus,sustainability,environment friendly,energy efficiency,waste management',
                'document_url': 'https://www.ugc.gov.in/green-campus',
                'search_priority': 3,
                'full_text_content': 'Green Campus Guidelines developing environmentally sustainable green campuses sustainability environment friendly energy efficiency waste management'
            },
            {
                'title': 'International Student Admission Guidelines',
                'content': 'Guidelines for admission and welfare of international students in Indian institutions.',
                'document_type': 'Guidelines',
                'category': 'International Education',
                'sub_category': 'Foreign Students',
                'department': 'Ministry of Education',
                'created_date': '2023-03-05',
                'last_updated': '2023-03-05',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'international students,foreign students,admission process,student visa,welfare guidelines',
                'document_url': 'https://www.education.gov.in/international-students',
                'search_priority': 3,
                'full_text_content': 'International Student Admission Guidelines admission welfare international students Indian institutions foreign students admission process student visa welfare guidelines'
            },
            {
                'title': 'Disability Inclusion Guidelines for Higher Education',
                'content': 'Guidelines for making higher education institutions accessible for persons with disabilities.',
                'document_type': 'Guidelines',
                'category': 'Inclusive Education',
                'sub_category': 'Disability Access',
                'department': 'UGC',
                'created_date': '2023-02-25',
                'last_updated': '2023-02-25',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'disability inclusion,accessible education,specially abled,infrastructure access,learning support',
                'document_url': 'https://www.ugc.gov.in/disability-guidelines',
                'search_priority': 3,
                'full_text_content': 'Disability Inclusion Guidelines making higher education institutions accessible persons with disabilities accessible education specially abled infrastructure access learning support'
            },

            # Schemes & Programs (8)
            {
                'title': 'Scholarship Schemes for Higher Education 2023-24',
                'content': 'Comprehensive guide to various scholarship schemes available for students in higher education including merit-based and means-based scholarships.',
                'document_type': 'Scheme',
                'category': 'Student Financial Aid',
                'sub_category': 'Scholarships',
                'department': 'Ministry of Education',
                'created_date': '2023-04-01',
                'last_updated': '2023-04-01',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'scholarship,financial aid,merit-based,means-based,SC ST OBC,minority scholarships,post-matric,National Scholarship Portal,student aid,fee reimbursement',
                'document_url': 'https://scholarships.gov.in/',
                'search_priority': 5,
                'full_text_content': 'Scholarship schemes higher education students merit-based means-based SC ST OBC minority post-matric National Scholarship Portal financial aid support eligibility criteria application process fee reimbursement'
            },
            {
                'title': 'Study in India Program Guidelines',
                'content': 'Comprehensive program to attract international students to Indian higher education institutions.',
                'document_type': 'Scheme',
                'category': 'International Education',
                'sub_category': 'Student Recruitment',
                'department': 'Ministry of Education',
                'created_date': '2023-03-15',
                'last_updated': '2023-03-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'study in India,international students,global education,India brand,student recruitment',
                'document_url': 'https://www.studyinindia.gov.in/program-guidelines',
                'search_priority': 4,
                'full_text_content': 'Study India Program attract international students Indian higher education institutions global education India brand student recruitment'
            },
            {
                'title': 'Prime Ministers Research Fellowship Scheme',
                'content': 'Scheme to support PhD students in pursuing research in cutting-edge science and technology domains.',
                'document_type': 'Scheme',
                'category': 'Research Education',
                'sub_category': 'PhD Fellowships',
                'department': 'Ministry of Education',
                'created_date': '2023-02-28',
                'last_updated': '2023-02-28',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'PMRF,research fellowship,PhD scholarship,science technology,research funding',
                'document_url': 'https://www.education.gov.in/pmrf-scheme',
                'search_priority': 4,
                'full_text_content': 'Prime Minister Research Fellowship Scheme support PhD students research cutting-edge science technology domains research funding scholarship'
            },
            {
                'title': 'National Apprenticeship Promotion Scheme',
                'content': 'Scheme to promote apprenticeship training in higher education institutions.',
                'document_type': 'Scheme',
                'category': 'Skill Development',
                'sub_category': 'Apprenticeship',
                'department': 'Ministry of Skill Development',
                'created_date': '2023-03-20',
                'last_updated': '2023-03-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'apprenticeship,skill training,industry exposure,on-job training,skill development',
                'document_url': 'https://www.apprenticeship.gov.in/naps-guidelines',
                'search_priority': 3,
                'full_text_content': 'National Apprenticeship Promotion Scheme promote apprenticeship training higher education institutions skill training industry exposure on-job training skill development'
            },
            {
                'title': 'Institutions of Eminence Scheme Guidelines',
                'content': 'Scheme to identify and support higher education institutions to become world-class teaching and research institutions.',
                'document_type': 'Scheme',
                'category': 'Institutional Development',
                'sub_category': 'World-Class Institutions',
                'department': 'Ministry of Education',
                'created_date': '2023-02-15',
                'last_updated': '2023-02-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'institutions of eminence,world-class universities,research institutions,higher education excellence',
                'document_url': 'https://www.education.gov.in/ioe-scheme',
                'search_priority': 4,
                'full_text_content': 'Institutions Eminence Scheme identify support higher education institutions become world-class teaching research institutions higher education excellence'
            },
            {
                'title': 'Global Initiative for Academic Networks Program',
                'content': 'Program to facilitate the participation of international faculty in Indian higher education institutions.',
                'document_type': 'Scheme',
                'category': 'International Collaboration',
                'sub_category': 'Faculty Exchange',
                'department': 'Ministry of Education',
                'created_date': '2023-03-10',
                'last_updated': '2023-03-10',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'GIAN,international faculty,academic networks,guest faculty,global teachers',
                'document_url': 'https://www.gian.iitkgp.ac.in/program-guidelines',
                'search_priority': 3,
                'full_text_content': 'Global Initiative Academic Networks Program facilitate participation international faculty Indian higher education institutions academic networks guest faculty global teachers'
            },
            {
                'title': 'Impacting Research Innovation and Technology Scheme',
                'content': 'Scheme to promote research and innovation in higher education institutions.',
                'document_type': 'Scheme',
                'category': 'Research Education',
                'sub_category': 'Innovation Funding',
                'department': 'Ministry of Education',
                'created_date': '2023-02-25',
                'last_updated': '2023-02-25',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'IMPRINT,research innovation,technology development,research funding,academic research',
                'document_url': 'https://www.education.gov.in/imprint-scheme',
                'search_priority': 3,
                'full_text_content': 'Impacting Research Innovation Technology Scheme promote research innovation higher education institutions technology development research funding academic research'
            },
            {
                'title': 'Unnat Bharat Abhiyan 2.0 Guidelines',
                'content': 'Program to connect higher education institutions with rural development initiatives.',
                'document_type': 'Scheme',
                'category': 'Community Engagement',
                'sub_category': 'Rural Development',
                'department': 'Ministry of Education',
                'created_date': '2023-03-30',
                'last_updated': '2023-03-30',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'Unnat Bharat Abhiyan,rural development,community engagement,social responsibility,village adoption',
                'document_url': 'https://www.unnatbharatabhiyan.gov.in/guidelines',
                'search_priority': 3,
                'full_text_content': 'Unnat Bharat Abhiyan connect higher education institutions rural development initiatives community engagement social responsibility village adoption'
            },

            # Frameworks & Standards (6)
            {
                'title': 'National Institutional Ranking Framework Methodology 2023',
                'content': 'Detailed methodology for NIRF ranking of higher education institutions including parameters for teaching, research, and graduation outcomes.',
                'document_type': 'Framework',
                'category': 'Institutional Ranking',
                'sub_category': 'Ranking Methodology',
                'department': 'Ministry of Education',
                'created_date': '2023-02-10',
                'last_updated': '2023-02-10',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'NIRF,ranking,higher education institutions,methodology,parameters,teaching quality,research,graduation outcomes,academic reputation,institutional ranking',
                'document_url': 'https://www.nirfindia.org/methodology',
                'search_priority': 4,
                'full_text_content': 'National Institutional Ranking Framework NIRF methodology ranking higher education institutions parameters teaching learning resources research professional practice graduation outcomes outreach inclusivity perception'
            },
            {
                'title': 'National Credit Framework for Higher Education',
                'content': 'Comprehensive framework for academic credit system in higher education as per NEP 2020.',
                'document_type': 'Framework',
                'category': 'Academic Standards',
                'sub_category': 'Credit System',
                'department': 'UGC',
                'created_date': '2023-03-01',
                'last_updated': '2023-03-01',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'credit framework,academic credits,credit transfer,academic bank of credits,student mobility',
                'document_url': 'https://www.ugc.gov.in/credit-framework',
                'search_priority': 4,
                'full_text_content': 'National Credit Framework higher education academic credit system NEP 2020 credit transfer academic bank credits student mobility'
            },
            {
                'title': 'Quality Assurance Framework for Higher Education',
                'content': 'Comprehensive framework for quality assurance and accreditation in higher education institutions.',
                'document_type': 'Framework',
                'category': 'Quality Assurance',
                'sub_category': 'Accreditation',
                'department': 'NAAC',
                'created_date': '2023-02-20',
                'last_updated': '2023-02-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'quality assurance,accreditation,NAAC,institutional quality,assessment framework',
                'document_url': 'https://www.naac.gov.in/quality-framework',
                'search_priority': 4,
                'full_text_content': 'Quality Assurance Framework higher education quality assurance accreditation institutions NAAC institutional quality assessment framework'
            },
            {
                'title': 'Learning Outcome-Based Curriculum Framework',
                'content': 'Framework for developing outcome-based curriculum in higher education programs.',
                'document_type': 'Framework',
                'category': 'Academic Standards',
                'sub_category': 'Curriculum Development',
                'department': 'UGC',
                'created_date': '2023-03-15',
                'last_updated': '2023-03-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'learning outcomes,curriculum framework,OBE,outcome-based education,curriculum design',
                'document_url': 'https://www.ugc.gov.in/locf',
                'search_priority': 3,
                'full_text_content': 'Learning Outcome Based Curriculum Framework developing outcome-based curriculum higher education programs OBE outcome-based education curriculum design'
            },
            {
                'title': 'Digital University Framework under NEP 2020',
                'content': 'Framework for establishing and operating digital universities in India.',
                'document_type': 'Framework',
                'category': 'Digital Education',
                'sub_category': 'Digital Universities',
                'department': 'Ministry of Education',
                'created_date': '2023-02-28',
                'last_updated': '2023-02-28',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'digital university,online education,virtual university,digital infrastructure,e-learning platform',
                'document_url': 'https://www.education.gov.in/digital-university-framework',
                'search_priority': 3,
                'full_text_content': 'Digital University Framework establishing operating digital universities India online education virtual university digital infrastructure e-learning platform'
            },
            {
                'title': 'Multidisciplinary Education and Research Universities Framework',
                'content': 'Framework for establishing multidisciplinary education and research universities as per NEP 2020.',
                'document_type': 'Framework',
                'category': 'Institutional Development',
                'sub_category': 'MER Universities',
                'department': 'UGC',
                'created_date': '2023-03-25',
                'last_updated': '2023-03-25',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'multidisciplinary education,research universities,MERU,holistic education,integrated learning',
                'document_url': 'https://www.ugc.gov.in/meru-framework',
                'search_priority': 3,
                'full_text_content': 'Multidisciplinary Education Research Universities Framework establishing multidisciplinary education research universities NEP 2020 holistic education integrated learning'
            },

            # Reports & Statistics (6)
            {
                'title': 'All India Survey on Higher Education 2021-22',
                'content': 'Comprehensive survey providing key performance indicators on higher education in India including enrollment, institutions, and teachers.',
                'document_type': 'Survey Report',
                'category': 'Education Statistics',
                'sub_category': 'Higher Education Data',
                'department': 'Ministry of Education',
                'created_date': '2023-01-10',
                'last_updated': '2023-01-10',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'AISHE,higher education,enrollment,universities,colleges,education statistics,performance indicators,institutional data',
                'document_url': 'https://www.education.gov.in/sites/upload_files/mhrd/files/statistics-new/aishe_2021-22.pdf',
                'search_priority': 4,
                'full_text_content': 'All India Survey Higher Education AISHE key performance indicators enrollment institutions teachers universities colleges education statistics institutional data'
            },
            {
                'title': 'National Employability Report for Engineers 2023',
                'content': 'Comprehensive report on employability of engineering graduates in India.',
                'document_type': 'Research Report',
                'category': 'Employment',
                'sub_category': 'Engineering Graduates',
                'department': 'AICTE',
                'created_date': '2023-04-01',
                'last_updated': '2023-04-01',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'employability,engineering graduates,job readiness,skill gap,industry requirements',
                'document_url': 'https://www.aicte-india.org/employability-report',
                'search_priority': 4,
                'full_text_content': 'National Employability Report Engineers employability engineering graduates India job readiness skill gap industry requirements'
            },
            {
                'title': 'Indian Higher Education Internationalization Report 2023',
                'content': 'Report on internationalization of Indian higher education and global partnerships.',
                'document_type': 'Research Report',
                'category': 'International Education',
                'sub_category': 'Global Partnerships',
                'department': 'Ministry of Education',
                'created_date': '2023-03-20',
                'last_updated': '2023-03-20',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'internationalization,global partnerships,foreign collaborations,study abroad,global education',
                'document_url': 'https://www.education.gov.in/internationalization-report',
                'search_priority': 3,
                'full_text_content': 'Indian Higher Education Internationalization Report internationalization Indian higher education global partnerships foreign collaborations study abroad global education'
            },
            {
                'title': 'Digital Education in India Report 2023',
                'content': 'Comprehensive report on the status of digital education in India, challenges, opportunities, and future roadmap.',
                'document_type': 'Research Report',
                'category': 'Digital Education',
                'sub_category': 'Digital Transformation',
                'department': 'Ministry of Education',
                'created_date': '2023-02-15',
                'last_updated': '2023-02-15',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'digital education,online learning,EdTech,India,education technology,digital infrastructure,e-learning,digital platforms',
                'document_url': 'https://www.education.gov.in/digital-education-report',
                'search_priority': 3,
                'full_text_content': 'Digital education India report status challenges opportunities future roadmap online learning EdTech education technology digital infrastructure e-learning platforms'
            },
            {
                'title': 'Research and Development Statistics in Higher Education 2023',
                'content': 'Comprehensive statistics on research output and development activities in Indian higher education institutions.',
                'document_type': 'Statistical Report',
                'category': 'Research Education',
                'sub_category': 'R&D Statistics',
                'department': 'UGC',
                'created_date': '2023-03-30',
                'last_updated': '2023-03-30',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'research statistics,R&D output,publications,patents,research funding',
                'document_url': 'https://www.ugc.gov.in/research-statistics',
                'search_priority': 3,
                'full_text_content': 'Research Development Statistics higher education research output development activities Indian higher education institutions publications patents research funding'
            },
            {
                'title': 'Gender Parity in Higher Education Report 2023',
                'content': 'Report on gender parity and women participation in higher education in India.',
                'document_type': 'Research Report',
                'category': 'Gender Studies',
                'sub_category': 'Women Education',
                'department': 'Ministry of Education',
                'created_date': '2023-03-25',
                'last_updated': '2023-03-25',
                'status': 'Active',
                'jurisdiction': 'National',
                'keywords': 'gender parity,women education,female enrollment,gender equality,higher education access',
                'document_url': 'https://www.education.gov.in/gender-parity-report',
                'search_priority': 3,
                'full_text_content': 'Gender Parity Higher Education Report gender parity women participation higher education India female enrollment gender equality higher education access'
            }
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
            
            # Insert individual keywords for better search
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

    # [Keep all the other methods from the previous version - search_documents, get_all_documents, etc.]
    # ... (All the search and utility methods remain the same)

    def search_documents(self, query=None, doc_type=None, category=None, department=None, use_advanced=True):
        """Enhanced search documents with multiple criteria and better ranking"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check if search_priority column exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(documents)")
            columns = [column[1] for column in cursor.fetchall()]
            has_search_priority = 'search_priority' in columns
            
            if use_advanced and query and has_search_priority:
                # Use advanced search with ranking
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
                params = [f'%{query}%'] * 7  # 7 placeholders
            else:
                # Basic search (backward compatible)
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
            
            results = df.to_dict('records')
            return results
            
        except Exception as e:
            print(f"Database search error: {e}")
            return []

    def get_all_documents(self):
        """Get all documents for display - safely handle missing columns"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check if search_priority column exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(documents)")
            columns = [column[1] for column in cursor.fetchall()]
            has_search_priority = 'search_priority' in columns
            
            if has_search_priority:
                query = "SELECT * FROM documents ORDER BY COALESCE(search_priority, 1) DESC, id DESC"
            else:
                query = "SELECT * FROM documents ORDER BY id DESC"
                
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.to_dict('records')
        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []

    def get_document_by_id(self, document_id):
        """Get a specific document by ID - safely handle missing columns"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            document_data = cursor.fetchone()
            conn.close()
            
            if document_data:
                # Get actual column names
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(documents)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Create dictionary with available columns
                document = {}
                for i, col in enumerate(columns):
                    if i < len(document_data):
                        document[col] = document_data[i]
                return document
            else:
                return None
        except Exception as e:
            print(f"Error getting document by ID: {e}")
            return None

    def keyword_search(self, keywords):
        """Precise keyword-based search using dedicated keywords table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Split multiple keywords
            keyword_list = [k.strip() for k in keywords.split(',')]
            
            query = '''
                SELECT d.*, COUNT(dk.keyword) as keyword_matches
                FROM documents d
                JOIN document_keywords dk ON d.id = dk.document_id
                WHERE dk.keyword IN ({})
                GROUP BY d.id
                ORDER BY keyword_matches DESC, COALESCE(d.search_priority, 1) DESC
            '''.format(','.join(['?'] * len(keyword_list)))
            
            cursor.execute(query, keyword_list)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []

    def get_categories(self):
        """Get all unique categories"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL ORDER BY category")
            categories = [row[0] for row in cursor.fetchall()]
            conn.close()
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

    def get_document_types(self):
        """Get all unique document types"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT document_type FROM documents WHERE document_type IS NOT NULL ORDER BY document_type")
            doc_types = [row[0] for row in cursor.fetchall()]
            conn.close()
            return doc_types
        except Exception as e:
            print(f"Error getting document types: {e}")
            return []

    def get_departments(self):
        """Get all unique departments"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT department FROM documents WHERE department IS NOT NULL ORDER BY department")
            departments = [row[0] for row in cursor.fetchall()]
            conn.close()
            return departments
        except Exception as e:
            print(f"Error getting departments: {e}")
            return []

    def get_sub_categories(self):
        """Get all unique sub-categories"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT sub_category FROM documents WHERE sub_category IS NOT NULL ORDER BY sub_category")
            sub_categories = [row[0] for row in cursor.fetchall()]
            conn.close()
            return sub_categories
        except Exception as e:
            print(f"Error getting sub-categories: {e}")
            return []

# Test function
def test_comprehensive_database():
    """Test the comprehensive database functionality"""
    print("🧪 Testing comprehensive database...")
    
    # Delete existing database to force recreation
    if os.path.exists('shiksha_setu.db'):
        os.remove('shiksha_setu.db')
        print("🗑️  Removed old database file")
    
    db = DatabaseManager()
    documents = db.get_all_documents()
    print(f"📄 Loaded {len(documents)} documents from database")
    
    # Test categories and types
    categories = db.get_categories()
    doc_types = db.get_document_types()
    departments = db.get_departments()
    
    print(f"📂 Categories ({len(categories)}): {categories}")
    print(f"📝 Document Types ({len(doc_types)}): {doc_types}")
    print(f"🏛️  Departments ({len(departments)}): {departments}")
    
    # Test searches
    results = db.search_documents(query="education policy")
    print(f"🔍 'education policy' search found {len(results)} documents")
    
    results = db.search_documents(query="scholarship")
    print(f"💰 'scholarship' search found {len(results)} documents")
    
    results = db.search_documents(query="regulation")
    print(f"⚖️  'regulation' search found {len(results)} documents")
    
    # Test keyword search
    results = db.keyword_search("UGC,regulation,accreditation")
    print(f"🔑 Keyword search found {len(results)} documents")

if __name__ == '__main__':
    test_comprehensive_database()