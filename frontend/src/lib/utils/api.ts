/**
 * API utilities for the Mako application
 */

// Get the API URL from environment variables or use a default
// Define a type for the environment variables
interface ImportMetaEnv {
    VITE_API_URL?: string;
    [key: string]: any;
}

// Access the environment variables safely
const env = (import.meta.env as ImportMetaEnv);
export const API_URL = env.VITE_API_URL || 'http://localhost:8001';

// Log the API URL for debugging
console.log('API URL:', API_URL);

/**
 * Get the full URL for an API endpoint
 * @param endpoint The API endpoint path (should start with /)
 * @returns The full URL
 */
export function getApiUrl(endpoint: string): string {
    // Make sure the endpoint starts with a slash
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_URL}${path}`;
    console.log('API URL for endpoint:', endpoint, 'is', url);
    return url;
}

/**
 * Fetch data from the API
 * @param endpoint The API endpoint path
 * @param options Fetch options
 * @returns The fetch response
 */
export async function fetchApi(endpoint: string, options?: RequestInit): Promise<Response> {
    const url = getApiUrl(endpoint);
    console.log('Fetching from:', url, 'with options:', options);
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            console.error('Fetch error: Response not OK', response.status, response.statusText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
} 