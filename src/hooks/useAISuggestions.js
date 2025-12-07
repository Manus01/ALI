import { useState } from 'react';
import { collection, addDoc, serverTimestamp, updateDoc, doc } from 'firebase/firestore';
import { db } from '../firebase';

// Hook to generate and store AI suggestions and record evaluations
export default function useAISuggestions() {
  const [loading, setLoading] = useState(false);

  // Placeholder suggestion generator based on campaign data
  async function generateAISuggestions(uid, campaignSnapshot = {}) {
    setLoading(true);
    try {
      // Simulate AI generation latency
      await new Promise((r) => setTimeout(r, 400));

      const suggestions = [
        {
          title: 'Increase bid on top-performing keywords',
          rationale: 'Keywords A and B show high CTR but low spend — increasing bids may capture additional conversions.'
        },
        {
          title: 'Optimize mobile landing page',
          rationale: 'Mobile conversion rate is lower than desktop; simplifying the form can improve conversions.'
        }
      ];

      // Persist suggestions to Firestore with user link
      const saved = [];
      for (const s of suggestions) {
        const ref = await addDoc(collection(db, 'suggestions'), {
          uid: uid || 'TEST_USER_ID_123',
          title: s.title,
          rationale: s.rationale,
          generatedAt: serverTimestamp(),
          campaignSnapshot: campaignSnapshot || {},
          evaluation: null
        });
        saved.push({ id: ref.id, ...s });
      }

      return { success: true, suggestions: saved };
    } catch (e) {
      console.error('Failed to generate suggestions', e);
      return { success: false, error: e.message };
    } finally {
      setLoading(false);
    }
  }

  async function evaluateSuggestion(suggestionId, feedback, evaluatorUid) {
    setLoading(true);
    try {
      const ref = doc(db, 'suggestions', suggestionId);
      await updateDoc(ref, {
        evaluation: {
          user: evaluatorUid || 'TEST_USER_ID_123',
          feedback,
          evaluatedAt: serverTimestamp()
        }
      });
      return { success: true };
    } catch (e) {
      console.error('Failed to evaluate suggestion', e);
      return { success: false, error: e.message };
    } finally {
      setLoading(false);
    }
  }

  return { loading, generateAISuggestions, evaluateSuggestion };
}
