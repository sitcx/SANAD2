import { communicationPreferences } from './sanad-data';

// Both views resolve the same candidate-owned values; inactive free text stays private.
export function getSharedCommunicationNeeds(selected: readonly string[], additionalNeeds: string) {
  return communicationPreferences.filter(item => selected.includes(item.id)).map(item => ({
    ...item,
    additionalNeeds: item.id === 'other' ? additionalNeeds.trim() : '',
  }));
}