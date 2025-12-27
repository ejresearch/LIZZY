/**
 * LIZZY - API Client Module
 * Centralized API communication for frontend
 */

/**
 * Base API client with error handling
 */
class LizzyAPI {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async fetch(endpoint, options = {}) {
        try {
            const response = await fetch(this.baseURL + endpoint, options);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    /**
     * GET request
     */
    async get(endpoint) {
        return this.fetch(endpoint, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    /**
     * POST request
     */
    async post(endpoint, body) {
        return this.fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.fetch(endpoint, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    // ===== PROJECT ENDPOINTS =====

    /**
     * Get all projects
     */
    async getProjects() {
        return this.get('/api/projects');
    }

    /**
     * Get project details
     */
    async getProject(projectName) {
        return this.get(`/api/project/${encodeURIComponent(projectName)}`);
    }

    /**
     * Save project (create or update)
     */
    async saveProject(projectData) {
        return this.post('/api/project/save', projectData);
    }

    /**
     * Delete project
     */
    async deleteProject(projectName) {
        return this.delete(`/api/project/${encodeURIComponent(projectName)}`);
    }

    // ===== BRAINSTORM ENDPOINTS =====

    /**
     * Get batch status for brainstorms
     */
    async getBrainstormBatchStatus(projectName) {
        return this.get(`/api/brainstorm/batch/status?project=${encodeURIComponent(projectName)}`);
    }

    /**
     * Start batch brainstorm generation
     */
    async startBrainstormBatch(projectName) {
        return this.post('/api/brainstorm/batch/start', { project: projectName });
    }

    /**
     * Generate single scene brainstorm
     */
    async generateSceneBrainstorm(projectName, sceneNumber) {
        return this.post('/api/brainstorm/batch/generate-scene', {
            project: projectName,
            scene_number: sceneNumber
        });
    }

    /**
     * Get all brainstorms for project
     */
    async getBrainstorms(projectName) {
        return this.get(`/api/brainstorm/brainstorms/${encodeURIComponent(projectName)}`);
    }

    // ===== WRITE ENDPOINTS =====

    /**
     * Get all drafts for project
     */
    async getDrafts(projectName) {
        return this.get(`/api/write/drafts/${encodeURIComponent(projectName)}`);
    }

    /**
     * Generate scene draft
     */
    async generateSceneDraft(projectName, sceneNumber, targetWords = 800) {
        return this.post('/api/write/generate', {
            project: projectName,
            scene_number: sceneNumber,
            target_words: targetWords
        });
    }

    /**
     * Export single scene
     */
    async exportScene(projectName, sceneNumber, version = 1, format = 'docx') {
        return this.post('/api/generate/export-scene', {
            project_name: projectName,
            scene_number: sceneNumber,
            version: version,
            format: format
        });
    }

    /**
     * Export full screenplay
     */
    async exportFullScreenplay(projectName, scenes, format = 'docx') {
        return this.post('/api/generate/export-full-screenplay', {
            project_name: projectName,
            scenes: scenes,
            format: format
        });
    }

    // ===== GENERATION ENDPOINTS =====

    /**
     * Generate random romcom project
     */
    async generateRandomRomcom() {
        return this.post('/api/generate/random-romcom', {});
    }

    // ===== PROMPT STUDIO ENDPOINTS =====

    /**
     * Send chat message
     */
    async sendChatMessage(projectName, message) {
        return this.post('/api/chat', {
            project: projectName,
            message: message
        });
    }

    /**
     * Execute prompt
     */
    async executePrompt(projectName, systemPrompt, userPrompt) {
        return this.post('/api/execute', {
            project: projectName,
            system_prompt: systemPrompt,
            user_prompt: userPrompt
        });
    }
}

// Create singleton instance
const api = new LizzyAPI();

// Export for use in HTML scripts
if (typeof window !== 'undefined') {
    window.LizzyAPI = LizzyAPI;
    window.api = api;
}
