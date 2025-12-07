import { useEffect, useState, useCallback } from 'react';
import { doc, setDoc, getDoc, serverTimestamp } from 'firebase/firestore';
import { db } from '../firebase';

const USER_ID = 'TEST_USER_ID_123';

export const PLATFORMS = [
  { id: 'facebook', name: 'Facebook' },
  { id: 'instagram', name: 'Instagram' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'linkedin', name: 'LinkedIn' },
  { id: 'google_analytics', name: 'Google Analytics' },
  { id: 'google_adwords', name: 'Google Adwords' },
  { id: 'facebook_ads', name: 'Facebook Ads' },
  { id: 'yandex_ads', name: 'Yandex Ads' },
  { id: 'bing_ads', name: 'Bing Ads' }
];

// Placeholder validator that simulates checking credentials
async function validateCredentials(platform, credentials) {
  // Simulate network latency
  await new Promise((r) => setTimeout(r, 500));

  // Basic heuristic for placeholder validation
  if (!credentials || Object.values(credentials).every(v => !v)) {
    return { status: 'Error', statusCode: 400, statusMessage: 'No credentials provided' };
  }
  if (credentials.apiKey && credentials.apiKey.startsWith('bad')) {
    return { status: 'Error', statusCode: 401, statusMessage: 'Invalid API key' };
  }
  // Otherwise assume OK
  return { status: 'OK', statusCode: 200, statusMessage: 'Connected' };
}

export default function useIntegrations() {
  const [integrations, setIntegrations] = useState({});
  const [loading, setLoading] = useState(false);

  const fetchIntegrations = useCallback(async () => {
    setLoading(true);
    try {
      const ref = doc(db, 'user_integrations', USER_ID);
      const snap = await getDoc(ref);
      if (snap.exists()) {
        setIntegrations(snap.data());
      } else {
        setIntegrations({});
      }
    } catch (e) {
      console.error('Failed to fetch integrations', e);
      setIntegrations({});
    } finally {
      setLoading(false);
    }
  }, []);

  const saveCredentials = useCallback(async (platformId, credentials) => {
    setLoading(true);
    try {
      // Validate first
      const validation = await validateCredentials(platformId, credentials);
      const statusPayload = {
        [`${platformId}_status`]: validation.status,
        [`${platformId}_statusCode`]: validation.statusCode,
        [`${platformId}_statusMessage`]: validation.statusMessage,
        [`${platformId}_lastSyncTime`]: serverTimestamp(),
        [`${platformId}_credentials`]: credentials
      };

      const ref = doc(db, 'user_integrations', USER_ID);
      await setDoc(ref, statusPayload, { merge: true });
      await fetchIntegrations();
      return { success: validation.status === 'OK', validation };
    } catch (e) {
      console.error('Failed to save credentials', e);
      return { success: false, validation: { status: 'Error', statusCode: 500, statusMessage: e.message } };
    } finally {
      setLoading(false);
    }
  }, [fetchIntegrations]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  return { integrations, loading, fetchIntegrations, saveCredentials, PLATFORMS, USER_ID };
}
