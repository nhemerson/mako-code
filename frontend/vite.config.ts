import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
	// Load env variables
	const env = loadEnv(mode, process.cwd(), '');
	const apiUrl = env.VITE_API_URL || 'http://localhost:8001';

	return {
		plugins: [sveltekit()],
		server: {
			proxy: {
				'/api': {
					target: apiUrl,
					changeOrigin: true
				}
			}
		},
		define: {
			'import.meta.env.VITE_API_URL': JSON.stringify(apiUrl)
		}
	};
});
