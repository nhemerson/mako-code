// This file can be deleted as we're not using stores anymore 

import { writable } from 'svelte/store';

interface ClosedTab {
    name: string;
    content: string;
    type: 'code' | 'dataset' | 'context';
    datasetPath?: string;
    datasetName?: string;
    timestamp: number;
}

function createClosedTabsStore() {
    const { subscribe, update } = writable<ClosedTab[]>([]);

    return {
        subscribe,
        addClosedTab: (tab: Omit<ClosedTab, 'timestamp'>) => {
            update(tabs => {
                const newTabs = [{ ...tab, timestamp: Date.now() }, ...tabs];
                // Keep only the last 10 closed tabs
                return newTabs.slice(0, 10);
            });
        },
        restoreLastTab: () => {
            let restoredTab: ClosedTab | undefined;
            update(tabs => {
                if (tabs.length === 0) return tabs;
                [restoredTab, ...tabs] = tabs;
                return tabs;
            });
            return restoredTab;
        },
        clear: () => update(() => [])
    };
}

export const closedTabs = createClosedTabsStore(); 