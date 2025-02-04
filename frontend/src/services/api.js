// services/api.js

// Define base API URL - use environment variable if available
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const migrateCode = async (repoUrl) => {
    try {
        const response = await fetch(`${API_BASE_URL}/convert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ repo_url: repoUrl }),
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                error: `HTTP error! status: ${response.status}`
            }));
            throw new Error(errorData.error || `Failed to migrate repository (Status: ${response.status})`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Migration error:', error);
        throw new Error(error.message || 'Failed to connect to migration service');
    }
};

export const downloadProject = async (projectName) => {
    try {
        // Open the download URL in a new tab
        window.open(`${API_BASE_URL}/download/${encodeURIComponent(projectName)}`, '_blank');
    } catch (error) {
        console.error('Download error:', error);
        throw new Error('Failed to download project files');
    }
};