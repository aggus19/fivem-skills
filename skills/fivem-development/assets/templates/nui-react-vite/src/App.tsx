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

  // Lua: SendNUIMessage({ action = 'open', data = { title = '...' } })
  useNuiEvent<OpenPayload>('open', (data) => {
    setTitle(data.title);
    setVisible(true);
  });
  useNuiEvent('close', () => setVisible(false));

  // Escape closes the UI and tells Lua to release focus.
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setVisible(false);
        void fetchNui('close');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [visible]);

  if (!visible) return null; // render nothing while hidden: no idle CEF cost

  return (
    <main className="panel">
      <h1>{title}</h1>
      <button
        onClick={async () => {
          const res = await fetchNui<{ ok: boolean }>('action', { kind: 'example' }, { ok: true });
          console.log('server answered', res);
        }}
      >
        Do action
      </button>
      <button
        onClick={() => {
          setVisible(false);
          void fetchNui('close');
        }}
      >
        Close
      </button>
    </main>
  );
}
