<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import Sidebar from '$lib/components/Sidebar.svelte';
</script>

<div class="flex h-screen bg-black overflow-hidden">
	<Sidebar />
	<div class="flex-1 min-w-0 bg-[#1A1A1A]">
		<slot />
	</div>
</div>
