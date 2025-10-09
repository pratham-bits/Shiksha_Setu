import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class NLPProcessor:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.documents = []
        self.tfidf_matrix = None
        self.is_fitted = False  # Track if model is fitted
        
    def preprocess_text(self, text):
        """Clean and preprocess text"""
        if not text:
            return ""
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and short tokens
        tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def fit_documents(self, documents):
        """Fit TF-IDF vectorizer with documents"""
        try:
            self.documents = documents
            processed_texts = []
            
            for doc in documents:
                # Combine title, content, and keywords for better representation
                combined_text = f"{doc['title']} {doc['content']} {doc.get('keywords', '')}"
                processed_text = self.preprocess_text(combined_text)
                processed_texts.append(processed_text)
            
            if processed_texts:
                self.tfidf_matrix = self.vectorizer.fit_transform(processed_texts)
                self.is_fitted = True
                print(f"TF-IDF model fitted with {len(processed_texts)} documents")
            else:
                print("No documents to fit TF-IDF model")
                self.is_fitted = False
                
        except Exception as e:
            print(f"Error fitting documents: {e}")
            self.is_fitted = False
    
    def semantic_search(self, query, documents, top_k=5):
        """Perform semantic search using TF-IDF and cosine similarity"""
        try:
            print(f"Starting semantic search for: '{query}'")
            
            # Check if model is fitted - FIXED: Use our custom flag instead of checking the matrix directly
            if not self.is_fitted or self.tfidf_matrix is None:
                print("TF-IDF model not fitted, fitting now...")
                self.fit_documents(documents)
                if not self.is_fitted:
                    print("Failed to fit model, returning empty results")
                    return []
            
            if not query or not query.strip():
                print("Empty query, returning empty results")
                return []
            
            # Preprocess query
            processed_query = self.preprocess_text(query)
            
            if not processed_query:
                print("Query processed to empty string, returning empty results")
                return []
            
            print(f"Processed query: '{processed_query}'")
            
            # Transform query to TF-IDF vector
            query_vector = self.vectorizer.transform([processed_query])
            
            # Calculate cosine similarity
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            print(f"Similarities calculated, shape: {similarities.shape}")
            
            # Get top k most similar documents
            if len(similarities) > 0:
                # Use numpy argsort with proper array handling
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                
                results = []
                for idx in top_indices:
                    similarity_score = similarities[idx]
                    # Only include results with meaningful similarity
                    if similarity_score > 0.001:  # Small threshold to filter very low matches
                        doc = documents[idx].copy()
                        doc['similarity_score'] = float(similarity_score)
                        results.append(doc)
                        print(f"Document {idx}: '{doc['title'][:30]}...' - similarity = {similarity_score:.4f}")
                
                print(f"Semantic search found {len(results)} relevant results")
                return results
            else:
                print("No similarities calculated")
                return []
                
        except Exception as e:
            print(f"Semantic search error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []
    
    def extract_keywords(self, text, top_n=10):
        """Extract important keywords from text"""
        try:
            processed_text = self.preprocess_text(text)
            tokens = processed_text.split()
            
            # Simple frequency-based keyword extraction
            from collections import Counter
            keywords = Counter(tokens)
            
            return [keyword for keyword, count in keywords.most_common(top_n)]
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return []