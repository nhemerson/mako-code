import { writable } from 'svelte/store';

export const hasUnsavedChanges = writable(false);

export function setHasUnsavedChanges(value: boolean) {
    hasUnsavedChanges.set(value);
} 