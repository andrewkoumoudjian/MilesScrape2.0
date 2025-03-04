                    const messages = [
                        `Searching for companies in ${location}`,
                        `Found a new milestone post`,
                        `Analyzing milestone sentiment`,
                        `Processing location data`,
                        `Extracting company information`,
                        `Validating milestone data`
                    ];
                    const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                    this.addScanLogEntry(randomMessage);
                }
            }
        }, 2000);
    }
    
    // Poll scan status updates from the API
    pollScanStatus() {
        if (!this.activeScan) return;
        
        clearInterval(this.scanIntervalId);
        
        this.scanIntervalId = setInterval(() => {
            fetch(`${this.apiBaseUrl}/scan/${this.activeScan.id}/status`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'completed' || data.status === 'failed') {
                        clearInterval(this.scanIntervalId);
                        
                        if (data.status === 'completed') {
                            this.updateScanProgress(100, data.stats);
                            this.addScanLogEntry("Scan completed successfully");
                            
                            // Refresh dashboard data
                            this.loadDashboardData();
                        } else {
                            this.addScanLogEntry(`Scan failed: ${data.error || 'Unknown error'}`);
                        }
                    } else if (data.status === 'in_progress') {
                        this.updateScanProgress(data.progress || 0, data.stats);
                        
                        // Add log entry if present
                        if (data.recent_log) {
                            this.addScanLogEntry(data.recent_log);
                        }
                    }
                })
                .catch(error => {
                    console.error("Error polling scan status:", error);
                });
        }, this.scanPollingInterval);
    }
    
    // Show scan progress UI
    showScanProgress() {
        // Hide placeholder and show progress
        this.noScanPlaceholder.classList.add('hidden');
        this.scanProgressContainer.classList.remove('hidden');
        
        // Update scan ID
        this.currentScanIdElement.textContent = this.activeScan.id;
        
        // Update location stat
        this.statLocationElement.textContent = this.activeScan.location;
        
        // Reset stats
        this.statCompaniesElement.textContent = '0';
        this.statPostsElement.textContent = '0';
        this.statLeadsElement.textContent = '0';
        
        // Reset progress bar
        this.scanProgressBar.style.width = '0%';
        this.scanProgressText.textContent = '0%';
        
        // Clear log
        this.scanLogContainer.innerHTML = '';
    }
    
    // Update scan progress display
    updateScanProgress(progress, stats) {
        // Update progress bar
        const roundedProgress = Math.round(progress);
        this.scanProgressBar.style.width = `${roundedProgress}%`;
        this.scanProgressText.textContent = `${roundedProgress}%`;
        
        // Update stats if provided
        if (stats) {
            if (stats.companies !== undefined) this.statCompaniesElement.textContent = stats.companies;
            if (stats.posts !== undefined) this.statPostsElement.textContent = stats.posts;
            if (stats.leads !== undefined) this.statLeadsElement.textContent = stats.leads;
        }
    }
    
    // Add entry to scan log
    addScanLogEntry(message) {
        const now = new Date("2025-03-04T02:59:23Z");
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-time">${timeString}</span>
            <span class="log-message">${message}</span>
        `;
        
        this.scanLogContainer.appendChild(logEntry);
        this.scanLogContainer.scrollTop = this.scanLogContainer.scrollHeight;
    }
    
    // Cancel the current scan
    cancelScan() {
        if (!this.activeScan) return;
        
        if (confirm("Are you sure you want to cancel the current scan?")) {
            // Send API request to cancel scan
            fetch(`${this.apiBaseUrl}/scan/${this.activeScan.id}/cancel`, {
                method: 'POST'
            })
            .then(response => {
                if (response.ok) {
                    this.addScanLogEntry("Scan cancelled by user");
                    clearInterval(this.scanIntervalId);
                    
                    // Hide progress after delay
                    setTimeout(() => {
                        this.activeScan = null;
                        this.scanProgressContainer.classList.add('hidden');
                        this.noScanPlaceholder.classList.remove('hidden');
                    }, 2000);
                }
            })
            .catch(error => {
                console.error("Error cancelling scan:", error);
                
                // For development/demo: Clean up mock scan
                clearInterval(this.scanIntervalId);
                this.addScanLogEntry("Scan cancelled by user (DEMO MODE)");
                
                setTimeout(() => {
                    this.activeScan = null;
                    this.scanProgressContainer.classList.add('hidden');
                    this.noScanPlaceholder.classList.remove('hidden');
                }, 2000);
            });
        }
    }
    
    // Check for active scan on page load
    checkForActiveScan() {
        fetch(`${this.apiBaseUrl}/scan/active`)
            .then(response => {
                if (!response.ok) return Promise.reject("No active scan");
                return response.json();
            })
            .then(data => {
                if (data.scan_id) {
                    // Resume displaying active scan
                    this.activeScan = {
                        id: data.scan_id,
                        location: data.location || "Unknown location",
                        startTime: data.start_time || new Date().toISOString(),
                        progress: data.progress || 0
                    };
                    
                    // Show scan progress
                    this.showScanProgress();
                    
                    // Start polling for updates
                    this.pollScanStatus();
                    
                    // Add log entry
                    this.addScanLogEntry("Resumed tracking active scan");
                }
            })
            .catch(error => {
                // No active scan, nothing to do
                console.log("No active scan found");
            });
    }
    
    // View scan details
    viewScanDetails(scanId) {
        // Navigate to the scan section
        document.getElementById('scan-link').click();
        
        // Display scan details (would fetch from API in production)
        alert(`Viewing details for scan ${scanId} - Full history view coming in next update`);
    }
    
    // Utility methods
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
    
    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }
}