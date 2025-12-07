import { useCallback, useEffect, useState } from 'react';
import { collection, addDoc, doc, setDoc, getDoc, updateDoc, serverTimestamp, query, where, getDocs } from 'firebase/firestore';
import { db, auth } from '../firebase';

const USER_ID_FALLBACK = 'TEST_USER_ID_123';

// Hook managing tutorials, AI generation placeholders, versioning and quiz results
export default function useTutorials() {
  const [available, setAvailable] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [loading, setLoading] = useState(false);

  const uid = (auth && auth.currentUser && auth.currentUser.uid) || USER_ID_FALLBACK;

  const fetchUserTutorials = useCallback(async () => {
    setLoading(true);
    try {
      const userRef = doc(db, 'users', uid);
      const q = query(collection(db, 'user_tutorials'));
      // For simplicity, fetch by user field
      const snaps = await getDocs(query(collection(db, 'user_tutorials')));
      const userTuts = [];
      snaps.forEach(s => {
        const data = s.data();
        if (data.uid === uid) userTuts.push({ id: s.id, ...data });
      });

      const av = userTuts.filter(t => !t.completed);
      const comp = userTuts.filter(t => t.completed);
      setAvailable(av);
      setCompleted(comp);
    } catch (e) {
      console.error('fetchUserTutorials failed', e);
    } finally {
      setLoading(false);
    }
  }, [uid]);

  useEffect(() => {
    fetchUserTutorials();
  }, [fetchUserTutorials]);

  async function generateAITutorial(topic, format = 'text', userProfile = {}) {
    setLoading(true);
    try {
      // Placeholder generation logic that uses learningStyle etc.
      const learningStyle = userProfile.learningStyle || 'Balanced';
      const content = `Tutorial on ${topic} (${format}) tailored for ${learningStyle} learners.`;
      const tutorial = {
        title: `${topic} - ${format}`,
        topic,
        format,
        content,
        meta: { learningStyle, generatedFor: uid },
        createdAt: serverTimestamp()
      };
      // store global tutorial
      const ref = await addDoc(collection(db, 'tutorials'), tutorial);
      // store user tutorial link
      const userTutRef = doc(db, 'user_tutorials', ref.id);
      await setDoc(userTutRef, { uid, tutorialId: ref.id, tutorial, completed: false, versions: [], createdAt: serverTimestamp() }, { merge: true });

      // refresh
      await fetchUserTutorials();
      return { success: true, id: ref.id, tutorial };
    } catch (e) {
      console.error('generateAITutorial failed', e);
      return { success: false, error: e.message };
    } finally {
      setLoading(false);
    }
  }

  async function submitQuizResult(userTutorialId, passed, score) {
    setLoading(true);
    try {
      const userTutDoc = doc(db, 'user_tutorials', userTutorialId);
      if (passed) {
        await updateDoc(userTutDoc, { completed: true, score, completedAt: serverTimestamp() });
      } else {
        // failed -> versioning: archive current tutorial content and regenerate
        const snap = await getDoc(userTutDoc);
        if (snap.exists()) {
          const data = snap.data();
          // save previous tutorial to tutorial_versions
          const versionRef = await addDoc(collection(db, 'tutorial_versions'), {
            userTutorialId,
            uid,
            tutorialId: data.tutorialId,
            tutorial: data.tutorial,
            createdAt: serverTimestamp()
          });
          // regenerate tutorial (placeholder)
          const newContent = data.tutorial.content + '\n\n[Regenerated version based on quiz results]';
          const newTutorial = { ...data.tutorial, content: newContent, regeneratedAt: serverTimestamp() };
          await updateDoc(userTutDoc, { tutorial: newTutorial, lastRegeneratedAt: serverTimestamp(), versions: (data.versions || []).concat([versionRef.id]) });
        }
      }
      await fetchUserTutorials();
      return { success: true };
    } catch (e) {
      console.error('submitQuizResult failed', e);
      return { success: false, error: e.message };
    } finally {
      setLoading(false);
    }
  }

  async function rateTutorial(userTutorialId, rating) {
    // rating: 'up' | 'down'
    try {
      const ref = doc(db, 'user_tutorials', userTutorialId);
      await updateDoc(ref, { lastRating: rating, lastRatingAt: serverTimestamp() });
      return { success: true };
    } catch (e) {
      console.error('rateTutorial failed', e);
      return { success: false, error: e.message };
    }
  }

  return { available, completed, loading, generateAITutorial, submitQuizResult, rateTutorial, fetchUserTutorials };
}
