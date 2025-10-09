// search.js - Fixed version with proper query parameter handling
console.log("=== SEARCH.JS LOADED ===");

// Function to initialize search when DOM is ready
function initializeSearch() {
    console.log("Initializing search functionality...");
    
    // Try multiple ways to find the form
    let searchForm = document.getElementById('searchForm');
    console.log("Form found by ID:", searchForm);
    
    if (!searchForm) {
        // Try other methods to find the form
        const forms = document.getElementsByTagName('form');
        console.log("All forms on page:", forms.length);
        if (forms.length > 0) {
            searchForm = forms[0];
            console.log("Using first form:", searchForm);
        }
    }
    
    const resultsSection = document.getElementById('resultsSection');
    const loadingElement = document.getElementById('loading');
    const noResultsElement = document.getElementById('noResults');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsCount = document.getElementById('resultsCount');
    const searchButton = document.getElementById('searchButton');

    console.log("Elements found:", {
        searchForm: !!searchForm,
        resultsSection: !!resultsSection,
        loadingElement: !!loadingElement,
        resultsContainer: !!resultsContainer,
        searchButton: !!searchButton
    });

    if (searchForm) {
        console.log("Adding submit event listener to form");
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log("=== FORM SUBMITTED ===");
            handleSearch();
        });
    }

    if (searchButton) {
        console.log("Adding click event listener to button");
        searchButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("=== BUTTON CLICKED ===");
            handleSearch();
        });
    }

    // If no form found, try to attach to any button with "Search" text
    if (!searchForm && !searchButton) {
        console.log("No form or button found, searching for any search button...");
        const allButtons = document.getElementsByTagName('button');
        for (let btn of allButtons) {
            if (btn.textContent.toLowerCase().includes('search')) {
                console.log("Found search button by text:", btn);
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log("=== FALLBACK SEARCH BUTTON CLICKED ===");
                    handleSearch();
                });
                break;
            }
        }
    }

    function handleSearch() {
        console.log("Handling search request...");
        
        // FIXED: Properly get input values with multiple fallback options
        const query = getInputValue('query') || getInputValue('search') || getInputValue('q') || '';
        const documentType = getInputValue('documentType') || getInputValue('type') || '';
        const category = getInputValue('category') || '';
        
        console.log("Search parameters:", { 
            query: query, 
            documentType: documentType, 
            category: category 
        });
        
        // Validate search query - FIXED: Better validation
        if (!query || !query.trim()) {
            showError('Please enter a search query');
            return;
        }
        
        if (query.trim().length < 2) {
            showError('Please enter at least 2 characters for search');
            return;
        }
        
        performSearch(query.trim(), documentType, category);
    }

    // NEW: Helper function to get input values from multiple possible sources
    function getInputValue(fieldName) {
        // Try by ID first
        let element = document.getElementById(fieldName);
        
        // Try by name attribute
        if (!element) {
            element = document.querySelector(`[name="${fieldName}"]`);
        }
        
        // Try by data attribute
        if (!element) {
            element = document.querySelector(`[data-field="${fieldName}"]`);
        }
        
        // Try by class (as last resort)
        if (!element) {
            const elements = document.getElementsByClassName(fieldName);
            if (elements.length > 0) {
                element = elements[0];
            }
        }
        
        if (element) {
            const value = element.value || element.textContent || '';
            console.log(`Found ${fieldName} field:`, element, `Value: "${value}"`);
            return value;
        }
        
        console.log(`Field ${fieldName} not found`);
        return null;
    }

    function performSearch(query, documentType, category) {
        console.log("=== PERFORMING SEARCH ===");
        console.log("Final search parameters:", { query, documentType, category });
        
        // Show loading state
        if (loadingElement) {
            loadingElement.classList.remove('d-none');
            loadingElement.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Searching...';
            console.log("Loading indicator shown");
        }
        if (resultsSection) resultsSection.classList.add('d-none');
        if (noResultsElement) noResultsElement.classList.add('d-none');

        console.log("Sending request to /api/search...");
        
        fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                document_type: documentType,
                category: category
            })
        })
        .then(response => {
            console.log("Response received. Status:", response.status, response.statusText);
            
            // Handle authentication errors
            if (response.status === 401) {
                throw new Error('Authentication required. Please log in to search.');
            }
            
            // Handle not found errors
            if (response.status === 404) {
                throw new Error('Search service unavailable. Please try again later.');
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return response.json();
        })
        .then(data => {
            console.log("Search response data:", data);
            if (loadingElement) loadingElement.classList.add('d-none');
            
            if (data.success) {
                console.log("Search successful, displaying results...");
                displayResults(data.results);
            } else {
                console.error("Search failed:", data.error);
                showError('Search failed: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error("Search error:", error);
            if (loadingElement) {
                loadingElement.classList.add('d-none');
            }
            
            // Provide more user-friendly error messages
            let userMessage = error.message;
            if (error.message.includes('401')) {
                userMessage = 'Authentication required. Please log in to search.';
            } else if (error.message.includes('404')) {
                userMessage = 'Search service is currently unavailable. Please try again later.';
            } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                userMessage = 'Network error. Please check your internet connection and try again.';
            }
            
            showError(userMessage);
        });
    }

    function displayResults(results) {
        console.log("Displaying", results.length, "results");
        
        if (!resultsContainer || !noResultsElement || !resultsSection || !resultsCount) {
            console.error("Required DOM elements not found for displaying results");
            showError('Display error: Required elements not found');
            return;
        }
        
        if (results.length === 0) {
            console.log("No results found");
            noResultsElement.classList.remove('d-none');
            resultsSection.classList.add('d-none');
            return;
        }

        resultsCount.textContent = `${results.length} document(s) found`;
        console.log("Results count updated");
        
        let resultsHTML = '';
        
        results.forEach((doc, index) => {
            console.log(`Result ${index + 1}:`, doc.title);
            
            // Calculate relevance percentage
            const similarityScore = doc.similarity_score ? 
                `<span class="badge bg-success ms-2">Relevance: ${(doc.similarity_score * 100).toFixed(1)}%</span>` : '';
            
            // Truncate content for preview
            const contentPreview = doc.content ? 
                (doc.content.length > 200 ? doc.content.substring(0, 200) + '...' : doc.content) : 
                'No content available';
            
            resultsHTML += `
                <div class="card mb-3 border-0 shadow-sm search-result-card" data-doc-id="${doc.id}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="card-title text-primary">${doc.title || 'Untitled Document'}</h5>
                            <div>
                                <span class="badge bg-secondary">${doc.document_type || 'Unknown Type'}</span>
                                ${similarityScore}
                            </div>
                        </div>
                        
                        <div class="row mb-2">
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="fas fa-tag me-1"></i>Category: ${doc.category || 'N/A'}
                                </small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="fas fa-building me-1"></i>Department: ${doc.department || 'N/A'}
                                </small>
                            </div>
                        </div>
                        
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-calendar me-1"></i>Created: ${doc.created_date || 'N/A'}
                            </small>
                        </div>
                        
                        <p class="card-text text-muted">${contentPreview}</p>
                        
                        ${doc.keywords ? `
                            <div class="mt-2">
                                <small class="text-muted">
                                    <i class="fas fa-hashtag me-1"></i>Keywords: ${doc.keywords}
                                </small>
                            </div>
                        ` : ''}
                        
                        <!-- Action Buttons -->
                        <div class="mt-3 d-flex flex-wrap gap-2">
                            <button class="btn btn-sm btn-outline-primary view-document-btn" data-doc-id="${doc.id}">
                                <i class="fas fa-eye me-1"></i>View Details
                            </button>
                            <button class="btn btn-sm btn-outline-success download-summary-btn" data-doc-id="${doc.id}">
                                <i class="fas fa-download me-1"></i>Download Summary
                            </button>
                            ${doc.document_url ? `
                                <a href="${doc.document_url}" target="_blank" class="btn btn-sm btn-outline-info">
                                    <i class="fas fa-external-link-alt me-1"></i>Full Document
                                </a>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });

        resultsContainer.innerHTML = resultsHTML;
        resultsSection.classList.remove('d-none');
        noResultsElement.classList.add('d-none');
        
        // Add event listeners to the new buttons
        addResultEventListeners();
        console.log("Results displayed successfully");
    }

    function addResultEventListeners() {
        // Add click listeners to view buttons
        document.querySelectorAll('.view-document-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const docId = this.getAttribute('data-doc-id');
                viewDocument(docId);
            });
        });

        // Add click listeners to download buttons
        document.querySelectorAll('.download-summary-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const docId = this.getAttribute('data-doc-id');
                downloadSummary(docId, this);
            });
        });

        // Add click listeners to entire result cards
        document.querySelectorAll('.search-result-card').forEach(card => {
            card.addEventListener('click', function() {
                const docId = this.getAttribute('data-doc-id');
                viewDocument(docId);
            });
        });
    }

    function showError(message) {
        console.error("🔍 Showing error:", message);
        if (!resultsContainer || !resultsSection) return;
        
        resultsContainer.innerHTML = `
            <div class="alert alert-warning d-flex align-items-center" role="alert">
                <i class="fas fa-exclamation-triangle me-2 fs-5"></i>
                <div>
                    <strong>Search Alert:</strong> ${message}
                </div>
            </div>
        `;
        resultsSection.classList.remove('d-none');
        if (noResultsElement) noResultsElement.classList.add('d-none');
        
        // Also show as toast for better visibility
        showToast(message, 'warning');
    }

    console.log("=== SEARCH FUNCTIONALITY INITIALIZED ===");
}

// Global functions for document actions
function viewDocument(documentId) {
    console.log(`Viewing document ${documentId}`);
    
    // Show loading state
    showToast('Loading document details...', 'info');
    
    // In a real application, this would redirect to the document view page
    setTimeout(() => {
        showToast(`Redirecting to document ${documentId}...`, 'success');
        
        // Uncomment the line below when you have the actual document view page
        // window.location.href = `/document/${documentId}`;
        
        // For demonstration, show an alert
        alert(`In a real application, you would be redirected to view document ${documentId}\n\nURL: /document/${documentId}`);
    }, 1000);
}

function downloadSummary(documentId, buttonElement = null) {
    console.log(`Downloading summary for document ${documentId}`);
    
    // Show loading state for download
    let originalText = '';
    if (buttonElement) {
        originalText = buttonElement.innerHTML;
        buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Downloading...';
        buttonElement.disabled = true;
    }
    
    showToast('Preparing download...', 'info');

    // Simulate API call - replace with actual endpoint
    fetch(`/api/document/${documentId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to fetch document`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.document) {
                const doc = data.document;
                const summary = generateDocumentSummary(doc);
                
                // Create and download file
                downloadTextFile(summary, `ShikshaSetu_${doc.title.replace(/[^a-z0-9]/gi, '_')}_summary.txt`);
                
                showToast('Summary downloaded successfully!', 'success');
            } else {
                throw new Error(data.error || 'Failed to download document data');
            }
        })
        .catch(error => {
            console.error('Download error:', error);
            showToast('Download failed: ' + error.message, 'error');
        })
        .finally(() => {
            // Restore button state
            if (buttonElement) {
                buttonElement.innerHTML = originalText;
                buttonElement.disabled = false;
            }
        });
}

function generateDocumentSummary(doc) {
    const timestamp = new Date().toLocaleString();
    
    return `
SHIKSHA SETU - DOCUMENT SUMMARY
================================

Title: ${doc.title || 'N/A'}
Document Type: ${doc.document_type || 'N/A'}
Category: ${doc.category || 'N/A'}
Department: ${doc.department || 'N/A'}
Creation Date: ${doc.created_date || 'N/A'}

CONTENT SUMMARY:
${doc.content || 'No content available'}

${doc.keywords ? `KEYWORDS: ${doc.keywords}` : ''}

${doc.document_url ? `FULL DOCUMENT URL: ${doc.document_url}` : ''}

---
Retrieved from ShikshaSetu AI Search Platform
Generated on: ${timestamp}
Document ID: ${doc.id}
    `.trim();
}

function downloadTextFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.custom-toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast element
    const toast = document.createElement('div');
    const alertClass = type === 'error' ? 'danger' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info';
    
    toast.className = `custom-toast alert alert-${alertClass} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    
    const icon = type === 'error' ? 'exclamation-triangle' : 
                 type === 'success' ? 'check-circle' : 
                 type === 'warning' ? 'exclamation-circle' : 'info-circle';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${icon} me-2 fs-5"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// Initialize when DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSearch);
} else {
    initializeSearch();
}

// Theme-aware functionality for search results
function updateSearchResultsForTheme() {
    // This function can be used to update any theme-specific search result styles
    const currentTheme = window.themeManager ? window.themeManager.getCurrentTheme() : 'light';
    console.log(`Search results updated for ${currentTheme} theme`);
}

// Listen for theme changes
document.addEventListener('themeChanged', (event) => {
    console.log('Theme changed to:', event.detail.theme);
    updateSearchResultsForTheme();
});

// Enhanced download summary with theme awareness
function downloadSummary(documentId) {
    const currentTheme = window.themeManager ? window.themeManager.getCurrentTheme() : 'light';
    
    console.log(`Downloading summary for document ${documentId} in ${currentTheme} theme`);
    
    // Show loading state for download
    const originalText = event.target.innerHTML;
    event.target.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Downloading...';
    event.target.disabled = true;

    fetch(`/api/document/${documentId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const doc = data.document;
                const summary = `
SHIKSHA SETU - DOCUMENT SUMMARY
================================

Theme: ${currentTheme === 'dark' ? 'Dark Mode' : 'Light Mode'}
Generated on: ${new Date().toLocaleString()}

Title: ${doc.title}
Type: ${doc.document_type}
Category: ${doc.category}
Department: ${doc.department}
Date: ${doc.created_date}

SUMMARY:
${doc.content}

KEYWORDS:
${doc.keywords}

DOCUMENT URL:
${doc.document_url || 'Not available'}

---
Retrieved from ShikshaSetu AI Search Platform
                `.trim();

                // Create and download file
                const blob = new Blob([summary], { type: 'text/plain;charset=utf-8' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `ShikshaSetu - ${doc.title.replace(/[^a-z0-9]/gi, '_')}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                // Show success message
                showToast('Summary downloaded successfully!', 'success');
            } else {
                throw new Error(data.error || 'Failed to download document');
            }
        })
        .catch(error => {
            console.error('Download error:', error);
            showToast('Download failed: ' + error.message, 'error');
        })
        .finally(() => {
            // Restore button state
            event.target.innerHTML = originalText;
            event.target.disabled = false;
        });
}