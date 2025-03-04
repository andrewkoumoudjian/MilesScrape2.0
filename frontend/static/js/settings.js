    // Save Google Cloud Storage settings
    function saveGcsSettings() {
        const bucketName = document.getElementById('gcsBucketName').value;
        const credentialsFile = document.getElementById('gcsCredentialsFile').files[0];
        
        if (!bucketName) {
            showToast('Error', 'Please enter a bucket name', 'error');
            return;
        }
        
        // In a production app, you'd upload the credentials file securely
        // For this example, we'll just show a success message
        
        /* 
        const formData = new FormData();
        formData.append('bucket_name', bucketName);
        if (credentialsFile) {
            formData.append('credentials_file', credentialsFile);
        }
        
        fetch('/api/settings/gcs', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to save GCS settings');
            return response.json();
        })
        .then(data => {
            showToast('Success', 'GCS settings saved successfully', 'success');
        })
        .catch(error => {
            console.error('Error saving GCS settings:', error);
            showToast('Error', 'Failed to save GCS settings', 'error');
        });
        */
        
        // For demonstration purposes:
        let message = 'GCS bucket settings saved successfully';
        if (credentialsFile) {
            message += ` with credentials file: ${credentialsFile.name}`;
        }
        showToast('Success', message, 'success');
        document.getElementById('gcsCredentialsFile').value = '';
    }

    // Save scraping settings
    function saveScrapingSettings() {
        const minDelay = document.getElementById('minDelay').value;
        const maxDelay = document.getElementById('maxDelay').value;
        const maxRequestsPerMinute = document.getElementById('maxRequestsPerMinute').value;
        const milestoneKeywords = document.getElementById('milestoneKeywords').value
            .split(',')
            .map(keyword => keyword.trim())
            .filter(keyword => keyword);
        
        if (parseFloat(minDelay) >= parseFloat(maxDelay)) {
            showToast('Error', 'Minimum delay must be less than maximum delay', 'error');
            return;
        }
        
        if (milestoneKeywords.length === 0) {
            showToast('Error', 'Please enter at least one milestone keyword', 'error');
            return;
        }
        
        // In a production app, you'd send this to an API endpoint
        // For this example, we'll just show a success message
        
        /*
        fetch('/api/settings/scraping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                min_delay: parseFloat(minDelay),
                max_delay: parseFloat(maxDelay),
                max_requests_per_minute: parseInt(maxRequestsPerMinute),
                milestone_keywords: milestoneKeywords
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to save scraping settings');
            return response.json();
        })
        .then(data => {
            showToast('Success', 'Scraping settings saved successfully', 'success');
        })
        .catch(error => {
            console.error('Error saving scraping settings:', error);
            showToast('Error', 'Failed to save scraping settings', 'error');
        });
        */
        
        // For demonstration purposes:
        showToast('Success', 'Scraping settings saved successfully', 'success');
    }
}