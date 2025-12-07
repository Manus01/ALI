import { useEffect, useState, useCallback } from 'react';
import { doc, setDoc, getDoc } from 'firebase/firestore';
import { db } from '../firebase';

const USER_ID = 'TEST_USER_ID_123';

export default function useIntegrations() {
  const [integrations, setIntegrations] = useState(null);
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

  const saveApiKey = useCallback(async (platform, key) => {
    setLoading(true);
    try {
      const ref = doc(db, 'user_integrations', USER_ID);
      const payload = { [platform + '_key']: key };
      await setDoc(ref, payload, { merge: true });
      await fetchIntegrations();
      return { success: true };
    } catch (e) {
      console.error('Failed to save key', e);
      return { success: false, message: e.message };
    } finally {
      setLoading(false);
    }
  }, [fetchIntegrations]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  return { integrations, loading, fetchIntegrations, saveApiKey, USER_ID };
}
