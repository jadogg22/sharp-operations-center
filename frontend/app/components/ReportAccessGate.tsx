'use client';

import { useEffect, useState, type FormEvent } from 'react';

import { reportError } from '../reportClient';

type Props = {
  apiBase: string;
  unlockPath: string;
  sessionKey: string;
  mark: string;
  eyebrow: string;
  title: string;
  description: string;
  passwordLabel: string;
  submitLabel: string;
  emptyMessage: string;
  onUnlock: (password: string) => void;
};

export function clearSavedReportPassword(sessionKey: string) {
  window.sessionStorage.removeItem(sessionKey);
}

export default function ReportAccessGate({
  apiBase,
  unlockPath,
  sessionKey,
  mark,
  eyebrow,
  title,
  description,
  passwordLabel,
  submitLabel,
  emptyMessage,
  onUnlock,
}: Props) {
  const [password, setPassword] = useState('');
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');

  const verify = async (candidate: string) => {
    const response = await fetch(`${apiBase}${unlockPath}`, {
      method: 'POST',
      headers: { 'X-Report-Password': candidate },
    });
    if (!response.ok) await reportError(response, `${title} access could not be verified.`);
    window.sessionStorage.setItem(sessionKey, candidate);
    setPassword('');
    onUnlock(candidate);
  };

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      const saved = window.sessionStorage.getItem(sessionKey);
      if (!saved) return;
      setChecking(true);
      void verify(saved).catch(() => {
        clearSavedReportPassword(sessionKey);
        if (active) setChecking(false);
      });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
    // Verify the tab-scoped password once when the gate is mounted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, unlockPath, sessionKey]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!password) { setError(emptyMessage); return; }
    setChecking(true);
    setError('');
    try {
      await verify(password);
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : `${title} access could not be verified.`);
      setChecking(false);
    }
  };

  return (
    <section className="revenue-gate" aria-labelledby="report-gate-title">
      <div className="revenue-gate-mark" aria-hidden="true">{mark}</div>
      <div className="revenue-gate-copy">
        <p className="step-label">{eyebrow}</p>
        <h2 id="report-gate-title">{title}</h2>
        <p>{description}</p>
      </div>
      <form onSubmit={submit}>
        <label><span>{passwordLabel}</span><input type="password" name={`${sessionKey}-access-code`} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="off" data-1p-ignore="true" data-lpignore="true" placeholder="Enter password" disabled={checking} /></label>
        <button className="primary-button" type="submit" disabled={checking}>{checking ? 'Checking…' : submitLabel}<span aria-hidden="true">→</span></button>
        {error && <p className="revenue-gate-error" role="alert">{error}</p>}
      </form>
      <small>The password is kept only for this browser tab. Closing the tab locks the report again.</small>
    </section>
  );
}
