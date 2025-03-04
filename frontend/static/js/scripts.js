/**
 * Common JavaScript functions for MilesScrape 2.0
 */

// Toast notification helper
function showToast(title, message, type = 'info') {
    const toastEl = document.getElementById('notification');
    const toast = new bootstrap.Toast(toastEl);
    
    document.getElementById('toastTitle').textContent = title;
    document.getElementById('toastMessage').textContent = message;
    
    // Remove existing color classes
    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');
    
    // Add appropriate color class
    switch (type) {
        case 'success':
            toastEl.classList.add('text-bg-success');
            break;
        case 'error':
            toastEl.classList.add('text-bg-danger');
            break;
        case 'warning':
            toastEl.classList.add('text-bg-warning');
            break;
        default:
            toastEl.classList.add('text-bg-info');
            break;
    }
    
    toast.show();
}

// Format file size to human-readable format
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Format ISO date string to more readable format
function formatDate(isoString) {
    if (!isoString) return 'N/A';
    
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Poll job status
function pollJobStatus(jobId, callback) {
    const checkStatus = () => {
        fetch(`/api/job_status/${jobId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch job status');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'running') {
                    // Continue polling
                    setTimeout(checkStatus, 5000);
                } else {
                    // Job completed or failed
                    callback(data);
                }
            })
            .catch(error => {
                console.error('Error checking job status:', error);
                // Try again after a delay
                setTimeout(checkStatus, 10000);
            });
    };
    
    // Start polling
    checkStatus();
}

// Main script for home page
document.addEventListener('DOMContentLoaded', function() {
    // Start scraping form handler
    const scrapeForm = document.getElementById('scrapeForm');
    if (scrapeForm) {
        scrapeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const location = document.getElementById('location').value;
            const businessTypes = document.getElementById('businessTypes').value.split(',').map(type => type.trim());
            const maxResults = parseInt(document.getElementById('maxResults').value);
            
            // Validate inputs
            if (!location) {
                showToast('Error', 'Please enter a location', 'error');
                return;
            }
            
            if (businessTypes.length === 0 || !businessTypes[0]) {
                showToast('Error', 'Please enter at least one business type', 'error');
                return;
            }
            
            // Disable the button and show loading
            const startBtn = document.getElementById('startScrapeBtn');
            const originalBtnText = startBtn.innerHTML;
            startBtn.disabled = true;
            startBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
            
            // Start scraping job
            fetch('/api/start_scraping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    location: location,
                    business_types: businessTypes,
                    max_results: maxResults
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to start scraping job');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showToast('Success', `Scraping job started with ID: ${data.job_id}`, 'success');
                    
                    // Add job to active jobs list
                    updateActiveJobs(data.job_id, 'running', {
                        location: location,
                        business_types: businessTypes.join(', '),
                        max_results: maxResults
                    });
                    
                    // Start polling for job status
                    pollJobStatus(data.job_id, updateJobStatus);
                } else {
                    showToast('Error', data.message || 'Unknown error', 'error');
                }
            })
            .catch(error => {
                showToast('Error', error.message, 'error');
                console.error('Error starting scraping job:', error);
            })
            .finally(() => {
                // Re-enable the button
                startBtn.disabled = false;
                startBtn.innerHTML = originalBtnText;
            });
        });
    }
});

// Update active jobs display
function updateActiveJobs(jobId, status, jobInfo) {
    const activeJobsDiv = document.getElementById('activeJobs');
    if (!activeJobsDiv) return;
    
    // Clear "No active jobs" message if this is the first job
    if (activeJobsDiv.querySelector('.text-muted')) {
        activeJobsDiv.innerHTML = '';
    }
    
    // Check if job card already exists
    let jobCard = document.getElementById(`job-${jobId}`);
    
    if (!jobCard) {
        // Create new job card
        jobCard = document.createElement('div');
        jobCard.id = `job-${jobId}`;
        jobCard.className = 'job-card card p-3';
        activeJobsDiv.appendChild(jobCard);
    }
    
    // Update job card contents based on status
    let statusText, statusClass;
    switch (status) {
        case 'running':
            statusText = '<span class="spinner-border spinner-sm" role="status"></span> Running';
            statusClass = 'job-status-running';
            break;
        case 'completed':
            statusText = '✓ Completed';
            statusClass = 'job-status-completed';
            jobCard.classList.add('completed');
            break;
        case 'failed':
            statusText = '✗ Failed';
            statusClass = 'job-status-failed';
            jobCard.classList.add('failed');
            break;
        default:
            statusText = 'Unknown';
            statusClass = '';
    }
    
    jobCard.innerHTML = `
        <div class="d-flex justify-content-between">
            <h6>Job ID: ${jobId}</h6>
            <span class="${statusClass}">${statusText}</span>
        </div>
        <div>Location: ${jobInfo.location}</div>
        <div>Business Types: ${jobInfo.business_types}</div>
        <div>Max Results: ${jobInfo.max_results}</div>
        <div class="mt-2">
            <a href="/results?job=${jobId}" class="btn btn-sm btn-outline-primary">View Results</a>
        </div>
    `;
}

// Update job status when polling returns a change
function updateJobStatus(jobData) {
    if (!jobData || !jobData.status) return;
    
    updateActiveJobs(
        jobData.job_id, 
        jobData.status, 
        {
            location: jobData.location,
            business_types: Array.isArray(jobData.business_types) ? jobData.business_types.join(', ') : jobData.business_types,
            max_results: jobData.max_results
        }
    );
    
    if (jobData.status === 'completed') {
        showToast('Job Completed', `Scraping job ${jobData.job_id} completed successfully`, 'success');
    } else if (jobData.status === 'failed') {
        showToast('Job Failed', `Scraping job ${jobData.job_id} failed: ${jobData.error || 'Unknown error'}`, 'error');
    }
}