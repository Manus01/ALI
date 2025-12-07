import { useCallback, useEffect, useState } from 'react';
import { collection, addDoc, doc, setDoc, getDoc, updateDoc, serverTimestamp, getDocs, query } from 'firebase/firestore';
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

  // Placeholder AI evaluation of a regenerated version before exposing to users
  async function evaluateVersionPlaceholder(tutorial) {
    // Simulate model evaluation - accept if length > 20 chars or learningStyle matches
    await new Promise(r => setTimeout(r, 200));
    const ok = tutorial && tutorial.content && tutorial.content.length > 20;
    return { ok, score: ok ? 0.9 : 0.1, note: ok ? 'Pass' : 'Fail' };
  }

  async function generateAITutorial(topic, format = 'text', userProfile = {}) {
    setLoading(true);
    try {
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
      // store user tutorial link (use tutorial id as doc id)
      const userTutRef = doc(db, 'user_tutorials', ref.id);
      await setDoc(userTutRef, { uid, tutorialId: ref.id, tutorial, completed: false, versions: [], preferredFormat: format, createdAt: serverTimestamp() }, { merge: true });

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

  async function switchFormat(userTutorialId, newFormat) {
    setLoading(true);
    try {
      const userTutDoc = doc(db, 'user_tutorials', userTutorialId);
      const snap = await getDoc(userTutDoc);
      if (!snap.exists()) return { success: false, error: 'Not found' };
      const data = snap.data();
      // generate a new version in desired format (placeholder)
      const newContent = `${data.tutorial.content}\n\n[Converted to ${newFormat} format]`;
      const newTutorial = { ...data.tutorial, content: newContent, format: newFormat, regeneratedAt: serverTimestamp() };
      // archive old version
      const versionRef = await addDoc(collection(db, 'tutorial_versions'), {
        userTutorialId,
        uid,
        tutorialId: data.tutorialId,
        tutorial: data.tutorial,
        reason: 'format switch',
        createdAt: serverTimestamp()
      });
      // evaluate via placeholder AI
      const evalRes = await evaluateVersionPlaceholder(newTutorial);
      if (!evalRes.ok) {
        // if AI evaluation fails, keep old and return
        return { success: false, evaluation: evalRes };
      }
      await updateDoc(userTutDoc, { tutorial: newTutorial, preferredFormat: newFormat, lastRegeneratedAt: serverTimestamp(), versions: (data.versions || []).concat([versionRef.id]) });
      await fetchUserTutorials();
      return { success: true, evaluation: evalRes };
    } catch (e) {
      console.error('switchFormat failed', e);
      return { success: false, error: e.message };
    } finally {
      setLoading(false);
    }
  }

  async function submitQuizResult(userTutorialId, passed, score) {
    setLoading(true);
    try {
      const userTutDoc = doc(db, 'user_tutorials', userTutorialId);
      const snap = await getDoc(userTutDoc);
      if (!snap.exists()) return { success: false, error: 'Not found' };
      const data = snap.data();

      if (passed) {
        await updateDoc(userTutDoc, { completed: true, score, completedAt: serverTimestamp() });
      } else {
        // failed -> versioning: archive current tutorial content and regenerate
        const versionRef = await addDoc(collection(db, 'tutorial_versions'), {
          userTutorialId,
          uid,
          tutorialId: data.tutorialId,
          tutorial: data.tutorial,
          reason: 'failed_quiz',
          createdAt: serverTimestamp()
        });
        // regenerate tutorial (placeholder logic creates new content)
        const newContent = data.tutorial.content + '\n\n[Regenerated version based on quiz results]';
        const newTutorial = { ...data.tutorial, content: newContent, regeneratedAt: serverTimestamp() };
        // AI evaluate regenerated version before exposing
        const evalRes = await evaluateVersionPlaceholder(newTutorial);
        if (!evalRes.ok) {
          // if AI says fail, still store version and keep it in available for manual review
          await updateDoc(userTutDoc, { lastRegeneratedAt: serverTimestamp(), versions: (data.versions || []).concat([versionRef.id]) });
          await fetchUserTutorials();
          return { success: false, evaluation: evalRes };
        }
        // if evaluation passes, replace tutorial for retry
        await updateDoc(userTutDoc, { tutorial: newTutorial, lastRegeneratedAt: serverTimestamp(), versions: (data.versions || []).concat([versionRef.id]) });
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
    try {
      const ref = doc(db, 'user_tutorials', userTutorialId);
      await updateDoc(ref, { lastRating: rating, lastRatingAt: serverTimestamp() });
      return { success: true };
    } catch (e) {
      console.error('rateTutorial failed', e);
      return { success: false, error: e.message };
    }
  }

  return { available, completed, loading, generateAITutorial, submitQuizResult, rateTutorial, fetchUserTutorials, switchFormat, evaluateVersionPlaceholder };
}
