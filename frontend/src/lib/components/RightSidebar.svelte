<script lang="ts">
	import { onMount } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let isSidebarCollapsed: boolean;
	export let datasets: Array<{ name: string; path: string }>;
	export let addDatasetTab: (name: string, path: string) => void;
	export let deleteDataset: (path: string) => void;
	export let addDatasetContext: (dataset: { name: string; path: string }) => void;
	export let analyzeDataset: (dataset: { name: string; path: string }) => void;

	let isExploreExpanded = true;  // State for the explore section
	let showDropdownForDataset: string | null = null;  // Track which dataset's dropdown is open

	// const dispatch = createEventDispatcher();
	// let isMenuOpen = false;

	// function handleDropdownClick(datasetPath: string) {
	// 	showDropdownForDataset = showDropdownForDataset === datasetPath ? null : datasetPath;
	// }

	// function toggleMenu() {
	// 	isMenuOpen = !isMenuOpen;
	// }

	// function closeMenu() {
	// 	isMenuOpen = false;
	// }

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.dataset-dropdown') && !target.closest('.dataset-menu-button')) {
			showDropdownForDataset = null;
		}
	}

	onMount(() => {
		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});

	function toggleDropdown(datasetPath: string, event: MouseEvent) {
		event.stopPropagation();
		showDropdownForDataset = showDropdownForDataset === datasetPath ? null : datasetPath;
	}

	function handleMenuAction(action: (dataset: { name: string; path: string }) => void, dataset: { name: string; path: string }) {
		action(dataset);
		showDropdownForDataset = null;  // Close dropdown after action
	}

	function handleImportClick() {
		dispatch('importClick');
	}

	function toggleSidebar() {
		isSidebarCollapsed = !isSidebarCollapsed;
	}
</script>

<div class="{isSidebarCollapsed ? 'w-[50px]' : 'w-[20%]'} border-l border-[#333333] flex flex-col bg-[#181818] p-4 relative transition-all duration-150 ease-in-out">
	
	<button
		class="absolute top-4 {isSidebarCollapsed ? 'left-1/2 -translate-x-1/2' : 'right-4'} text-gray-400 hover:text-white transition-colors"
		on:click={toggleSidebar}
		aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}	
	>
		<svg 
			xmlns="http://www.w3.org/2000/svg" 
			class="h-5 w-5 transform transition-transform duration-300 {!isSidebarCollapsed ? 'rotate-180' : ''}" 
			viewBox="0 0 24 24" 
			fill="none" 
			stroke="currentColor" 
			stroke-width="2" 
			stroke-linecap="round" 
			stroke-linejoin="round"
		>
			<circle cx="12" cy="12" r="1" />
			<circle cx="12" cy="5" r="1" />
			<circle cx="12" cy="19" r="1" />
		</svg>
	</button>

	<div class="right-panel h-full overflow-y-auto {isSidebarCollapsed ? 'opacity-0' : 'opacity-100'} transition-opacity duration-50" style="visibility: {isSidebarCollapsed ? 'hidden' : 'visible'}">
		<h2 class="text-white font-semibold mb-4 text-xs uppercase tracking-wider">Data Management</h2>
		<div class="space-y-4">
			<button
				class="w-full px-4 py-2 bg-[#181818] hover:bg-[#222222] text-white rounded-lg transition-colors text-xs flex items-center justify-center gap-2 border border-[#333333]"
				on:click={handleImportClick}
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
					<polyline points="17 8 12 3 7 8" />
					<line x1="12" y1="3" x2="12" y2="15" />
				</svg>
				Import Data
			</button>

			<h2 
				class="text-white font-semibold mt-8 mb-4 text-xs uppercase tracking-wider flex items-center justify-between cursor-pointer hover:text-gray-300 transition-colors"
				on:click={() => isExploreExpanded = !isExploreExpanded}
			>
				<span>Local Datasets</span>
				<button 
					class="text-gray-400 hover:text-white transition-colors"
				>
					<svg 
						xmlns="http://www.w3.org/2000/svg" 
						class="h-4 w-4 transform transition-transform duration-200 {isExploreExpanded ? 'rotate-0' : '-rotate-90'}" 
						viewBox="0 0 24 24" 
						fill="none" 
						stroke="currentColor" 
						stroke-width="2" 
						stroke-linecap="round" 
						stroke-linejoin="round"
					>
						<polyline points="6 9 12 15 18 9"></polyline>
					</svg>
				</button>
			</h2>
			<div 
				class="space-y-1 overflow-hidden transition-all duration-200"
				style="max-height: {isExploreExpanded ? '500px' : '0px'}; opacity: {isExploreExpanded ? '1' : '0'}"
			>
				{#if datasets.length === 0}
					<div class="text-gray-400 text-xs p-1">
						No datasets available
					</div>
				{:else}
					{#each datasets as dataset}
						<div 
							class="flex items-center justify-between gap-2 text-gray-400 py-1 px-2 hover:bg-[#222222] rounded-lg transition-colors group"
						>
							<div 
								class="flex items-center gap-2 flex-1 cursor-pointer"
								on:click={() => addDatasetTab(dataset.name, dataset.path)}
							>
								<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
									<line x1="3" y1="9" x2="21" y2="9"/>
									<line x1="3" y1="15" x2="21" y2="15"/>
									<line x1="9" y1="9" x2="9" y2="21"/>
								</svg>
								<span class="text-xs">{dataset.name}</span>
							</div>
							<div class="dataset-dropdown relative">
								<button
									class="p-1 opacity-0 group-hover:opacity-100 hover:bg-[#333333] rounded transition-all"
									on:click={(e) => toggleDropdown(dataset.path, e)}
								>
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
										<circle cx="12" cy="12" r="1" />
										<circle cx="12" cy="5" r="1" />
										<circle cx="12" cy="19" r="1" />
									</svg>
								</button>
								
								{#if showDropdownForDataset === dataset.path}
									<div 
										class="fixed mt-1 w-48 bg-[#222222] rounded-lg shadow-lg border border-[#333333] z-[100]"
										style="left: calc(100% - 200px); transform: translateY(-50%);"
										on:click|stopPropagation
									>
										<button
											class="w-full px-4 py-2 text-xs text-left text-gray-400 hover:bg-[#333333] hover:text-white transition-colors flex items-center gap-2"
											on:click={() => handleMenuAction(analyzeDataset, dataset)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
												<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
											</svg>
											Analyze Dataset
										</button>
										<button
											class="w-full px-4 py-2 text-xs text-left text-gray-400 hover:bg-[#333333] hover:text-white transition-colors flex items-center gap-2"
											on:click={() => handleMenuAction(addDatasetContext, dataset)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
												<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
											</svg>
											Add Context
										</button>
										<button
											class="w-full px-4 py-2 text-xs text-left text-red-400 hover:bg-[#333333] hover:text-red-300 transition-colors flex items-center gap-2"
											on:click={() => handleMenuAction(deleteDataset, dataset.path)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<path d="M3 6h18"></path>
												<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
												<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
											</svg>
											Delete Dataset
										</button>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				{/if}
			</div>
		</div>
	</div>
</div> 