/**
 * Results page specific JavaScript for MilesScrape 2.0
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load files list on page load
    loadFilesList();
    
    // Refresh files list button
    const refreshBtn = document.getElementById('refreshFilesBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadFilesList();
        });
    }
    
    // Load job results button
    const loadResultsBtn = document.getElementById('loadResultsBtn');
    if (loadResultsBtn) {
        loadResultsBtn.addEventListener('click', function() {
            const jobId = document.getElementById('jobIdInput').value.trim();
            if (jobId) {
                loadJobResults(jobId);
            } else {
                showToast('Error', 'Please enter a job ID', 'error');
            }
        });
    }
    
    // Check if job ID is in the URL params
    const urlParams = new URLSearchParams(window.location.search);
    const jobId = urlParams.get('job');
    if (jobId) {
        document.getElementById('jobIdInput').value = jobId;
        loadJobResults(jobId);
    }
});

// Load files list from cloud storage
function loadFilesList() {
    const filesTable = document.getElementById('filesList');
    
    // Show loading message
    filesTable.innerHTML = '<tr><td colspan="4" class="text-center">Loading files...</td></tr>';
    
    fetch('/api/list_files')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch files list');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && Array.isArray(data.files)) {
                if (data.files.length === 0) {
                    filesTable.innerHTML = '<tr><td colspan="4" class="text-center">No files found</td></tr>';
                } else {
                    // Sort files by date (most recent first)
                    const sortedFiles = data.files.sort((a, b) => {
                        return new Date(b.updated || 0) - new Date(a.updated || 0);
                    });
                    
                    // Populate table
                    filesTable.innerHTML = sortedFiles.map(file => `
                        <tr>
                            <td>${file.name}</td>
                            <td class="file-size">${formatFileSize(file.size)}</td>
                            <td class="file-date">${formatDate(file.updated)}</td>
                            <td>
                                <a href="/api/download/${encodeURIComponent(file.name)}" class="btn btn-sm btn-outline-primary">Download</a>
                            </td>
                        </tr>
                    `).join('');
                }
            } else {
                throw new Error(data.message || 'Failed to get files');
            }
        })
        .catch(error => {
            filesTable.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Error: ${error.message}</td></tr>`;
            console.error('Error loading files:', error);
        });
}

// Load results for a specific job ID
function loadJobResults(jobId) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    // Show loading message
    resultsContainer.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    fetch(`/api/job_results/${jobId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch job results');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && Array.isArray(data.results)) {
                if (data.results.length === 0) {
                    resultsContainer.innerHTML = '<p class="text-muted">No results found for this job.</p>';
                } else {
                    // Create table for results
                    let html = `
                        <p>Found ${data.results.length} results for job ${jobId}</p>
                        <div class="table-responsive">
                            <table class="table table-hover milestone-table">
                                <thead>
                                    <tr>
                                        <th>Company</th>
                                        <th>Owner</th>
                                        <th>Milestone</th>
                                        <th>Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    // Add row for each result
                    data.results.forEach((result, index) => {
                        html += `
                            <tr data-result-id="${index}" onclick="showCompanyDetails(${index})">
                                <td>${result.company_name || 'N/A'}</td>
                                <td>${result.company_owner || 'N/A'}</td>
                                <td>${result.milestone_description ? result.milestone_description.substring(0, 100) + (result.milestone_description.length > 100 ? '...' : '') : 'N/A'}</td>
                                <td><button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); showCompanyDetails(${index})">View</button></td>
                            </tr>
                        `;
                    });
                    
                    html += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    resultsContainer.innerHTML = html;
                    
                    // Store results data in window object for modal access
                    window.jobResults = data.results;
                }
            } else {
                throw new Error(data.message || 'Failed to get results');
            }
        })
        .catch(error => {
            resultsContainer.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
            console.error('Error loading job results:', error);
        });
}

// Display company details in modal
function showCompanyDetails(resultIndex) {
    if (!window.jobResults || !window.jobResults[resultIndex]) return;
    
    const result = window.jobResults[resultIndex];
    const modal = new bootstrap.Modal(document.getElementById('companyModal'));
    
    // Set modal title
    document.getElementById('companyModalTitle').textContent = result.company_name || 'Company Details';
    
    // Create modal body content
    let html = `
        <dl>
            <dt>Company Name</dt>
            <dd>${result.company_name || 'N/A'}</dd>
            
            <dt>Address</dt>
            <dd>${result.company_address || 'N/A'}</dd>
            
            <dt>Website</dt>
            <dd>${result.company_website ? `<a href="${result.company_website}" target="_blank">${result.company_website}</a>` : 'N/A'}</dd>
            
            <dt>Company Owner</dt>
            <dd>${result.company_owner || 'N/A'}</dd>
            
            <dt>LinkedIn Profile</dt>
            <dd>${result.linkedin_profile ? `<a href="${result.linkedin_profile}" target="_blank">${result.linkedin_profile}</a>` : 'N/A'}</dd>
            
            <dt>LinkedIn Company Page</dt>
            <dd>${result.linkedin_company_url ? `<a href="${result.linkedin_company_url}" target="_blank">${result.linkedin_company_url}</a>` : 'N/A'}</dd>
            
            <dt>Milestone Description</dt>
            <dd>${result.milestone_description || 'No milestone identified'}</dd>
            
            <dt>Data Sources</dt>
            <dd>
                <ul class="list-unstyled">
                    <li><i class="bi ${result.data_sources?.google_maps ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}"></i> Google Maps</li>
                    <li><i class="bi ${result.data_sources?.linkedin ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}"></i> LinkedIn</li>
                    <li><i class="bi ${result.data_sources?.google_search ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}"></i> Google Search</li>
                </ul>
            </dd>
        </dl>
    `;
    
    document.getElementById('companyModalBody').innerHTML = html;
    
    // Show the modal
    modal.show();
}

// Make the function globally available
window.showCompanyDetails = showCompanyDetails;