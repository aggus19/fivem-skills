import { useEffect, useState } from 'react';
import { useNuiEvent } from './hooks/useNuiEvent';
import { fetchNui } from './utils/fetchNui';
import { isEnvBrowser } from './utils/misc';

interface OpenPayload {
  title: string;
}

export default function App() {
  const [visible, setVisible] = useState(isEnvBrowser());
  const [title, setTitle] = useState('Dev preview');
  const [error, setError] = useState('');

  // Lua: SendNUIMessage({ action = 'open', data = { title = '...' } })
  useNuiEvent<OpenPayload>('open', (data) => {
    setTitle(data.title);
    setVisible(true);
  });
  useNuiEvent('close', () => setVisible(false));

  useEffect(() => {
    void fetchNui('ready').catch(() => setError('Unable to connect. Try reopening the interface.'));
  }, []);

  const close = () => {
    void fetchNui('close').then(() => setVisible(false))
      .catch(() => setError('Unable to close. Please try again.'));
  };

  // Escape closes the UI and tells Lua to release focus.
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        void fetchNui('close').then(() => setVisible(false))
          .catch(() => setError('Unable to close. Please try again.'));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [visible]);

  if (!visible) return null; // avoids rendering the panel; the CEF instance still exists

  return (
    <main className="panel">
      <h1>{title}</h1>
      {error && <p role="alert">{error}</p>}
      <button
        onClick={async () => {
          try {
            const res = await fetchNui<{ ok: boolean }>('action', { kind: 'example' }, { ok: true });
            setError(res.ok ? '' : 'Action could not be completed.');
          } catch {
            setError('Unable to complete the action. Please try again.');
          }
        }}
      >
        Do action
      </button>
      <button
        onClick={close}
      >
        Close
      </button>
    </main>
  );
}
