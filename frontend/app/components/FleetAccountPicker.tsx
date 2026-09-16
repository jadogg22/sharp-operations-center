'use client';

import { useEffect, useState } from 'react';

import { reportError } from '../reportClient';
import type { FleetCostAccount, FleetCostAccountSearch } from '../reportTypes';

type Props = {
  apiBase: string;
  accounts: FleetCostAccount[];
  disabled: boolean;
  accessPassword: string;
  onChange: (accounts: FleetCostAccount[]) => void;
  onAccessDenied: () => void;
};

const MAX_ACCOUNTS = 8;
const GROUPINGS_STORAGE_KEY = 'sharp-fleet-cost-account-groupings';

type SavedGrouping = {
  id: string;
  name: string;
  accounts: FleetCostAccount[];
};

const isSavedGrouping = (value: unknown): value is SavedGrouping => {
  if (!value || typeof value !== 'object') return false;
  const grouping = value as Partial<SavedGrouping>;
  return typeof grouping.id === 'string'
    && typeof grouping.name === 'string'
    && Array.isArray(grouping.accounts)
    && grouping.accounts.every((account) => (
      account
      && typeof account === 'object'
      && typeof account.gl_account === 'string'
      && typeof account.label === 'string'
      && typeof account.account_type === 'string'
    ));
};

export default function FleetAccountPicker({ apiBase, accounts, disabled, accessPassword, onChange, onAccessDenied }: Props) {
  const [adding, setAdding] = useState(false);
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<FleetCostAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [groupingName, setGroupingName] = useState('');
  const [groupings, setGroupings] = useState<SavedGrouping[]>([]);
  const [loadingGrouping, setLoadingGrouping] = useState('');

  useEffect(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem(GROUPINGS_STORAGE_KEY) ?? '[]') as unknown;
      // Browser storage is only available after mount, so hydrate saved groups here.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (Array.isArray(saved)) setGroupings(saved.filter(isSavedGrouping));
    } catch {
      setGroupings([]);
    }
  }, []);

  const persistGroupings = (next: SavedGrouping[]) => {
    setGroupings(next);
    try {
      window.localStorage.setItem(GROUPINGS_STORAGE_KEY, JSON.stringify(next));
    } catch {
      setMessage('The browser could not save this grouping.');
    }
  };

  useEffect(() => {
    let active = true;
    const loadDefaults = async () => {
      if (accounts.length > 0) return;
      try {
        const response = await fetch(`${apiBase}/reports/fleet-cost-revenue/accounts`, { headers: { 'X-Report-Password': accessPassword } });
        if (response.status === 401) onAccessDenied();
        if (!response.ok) await reportError(response, 'Default GL accounts could not be loaded.');
        const result = await response.json() as FleetCostAccountSearch;
        if (active && result.default_accounts.length > 0) onChange(result.default_accounts);
      } catch (errorValue) {
        if (active) setMessage(errorValue instanceof Error ? errorValue.message : 'Default GL accounts could not be loaded.');
      }
    };
    void loadDefaults();
    return () => { active = false; };
    // Account initialization should run only when the data source changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  useEffect(() => {
    if (!adding || query.trim().length === 0) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setMessage('');
      try {
        const parameters = new URLSearchParams({ search: query.trim() });
        const response = await fetch(`${apiBase}/reports/fleet-cost-revenue/accounts?${parameters.toString()}`, { signal: controller.signal, headers: { 'X-Report-Password': accessPassword } });
        if (response.status === 401) onAccessDenied();
        if (!response.ok) await reportError(response, 'GL accounts could not be searched.');
        const result = await response.json() as FleetCostAccountSearch;
        setMatches(result.accounts);
        if (result.accounts.length === 0) setMessage(`No active GL account matches “${query.trim()}”.`);
      } catch (errorValue) {
        if (!(errorValue instanceof DOMException && errorValue.name === 'AbortError')) {
          setMessage(errorValue instanceof Error ? errorValue.message : 'GL accounts could not be searched.');
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [accessPassword, adding, apiBase, onAccessDenied, query]);

  const addAccount = (account: FleetCostAccount) => {
    if (accounts.some((selected) => selected.gl_account === account.gl_account)) {
      setMessage(`${account.gl_account} is already in the cost stack.`);
      return;
    }
    onChange([...accounts, account]);
    setAdding(false);
    setQuery('');
    setMatches([]);
    setMessage('');
  };

  const updateQuery = (value: string) => {
    setQuery(value);
    if (value.trim().length === 0) {
      setMatches([]);
      setLoading(false);
      setMessage('');
    }
  };

  const removeAccount = (glAccount: string) => {
    const next = accounts.filter((account) => account.gl_account !== glAccount);
    onChange(next);
    if (next.length === 0) {
      setAdding(true);
      setMessage('Add at least one verified account before building the report.');
    }
  };

  const saveGrouping = () => {
    const name = groupingName.trim();
    if (!name) {
      setMessage('Name the account grouping before saving it.');
      return;
    }
    if (accounts.length === 0) {
      setMessage('Add at least one verified account before saving a grouping.');
      return;
    }
    const existing = groupings.find((grouping) => grouping.name.toLowerCase() === name.toLowerCase());
    const nextGrouping: SavedGrouping = { id: existing?.id ?? crypto.randomUUID(), name, accounts };
    persistGroupings(existing
      ? groupings.map((grouping) => grouping.id === existing.id ? nextGrouping : grouping)
      : [...groupings, nextGrouping]);
    setGroupingName('');
    setMessage(`${name} saved for this browser.`);
  };

  const loadGrouping = async (grouping: SavedGrouping) => {
    setLoadingGrouping(grouping.id);
    setMessage('');
    try {
      const verifiedAccounts = await Promise.all(grouping.accounts.map(async (savedAccount) => {
        const parameters = new URLSearchParams({ search: savedAccount.gl_account });
        const response = await fetch(`${apiBase}/reports/fleet-cost-revenue/accounts?${parameters.toString()}`, {
          headers: { 'X-Report-Password': accessPassword },
        });
        if (response.status === 401) onAccessDenied();
        if (!response.ok) await reportError(response, 'The saved account grouping could not be verified.');
        const result = await response.json() as FleetCostAccountSearch;
        return result.accounts.find((account) => account.gl_account.toUpperCase() === savedAccount.gl_account.toUpperCase()) ?? null;
      }));
      if (verifiedAccounts.some((account) => account === null)) {
        throw new Error('One or more accounts in this grouping are no longer active.');
      }
      onChange(verifiedAccounts as FleetCostAccount[]);
      setMessage(`${grouping.name} loaded and verified.`);
    } catch (errorValue) {
      setMessage(errorValue instanceof Error ? errorValue.message : 'The saved account grouping could not be loaded.');
    } finally {
      setLoadingGrouping('');
    }
  };

  const deleteGrouping = (grouping: SavedGrouping) => {
    persistGroupings(groupings.filter((saved) => saved.id !== grouping.id));
    setMessage(`${grouping.name} removed from this browser.`);
  };

  return (
    <section className="fleet-account-picker" aria-labelledby="fleet-account-title">
      <div className="fleet-account-heading">
        <div><span>Cost stack</span><strong id="fleet-account-title">GL accounts included</strong><small>Each verified account stays visible as its own chart segment and contributes to the total cost.</small></div>
        <button type="button" className="add-account-button" onClick={() => { setAdding(true); setMessage(''); }} disabled={disabled || adding || accounts.length >= MAX_ACCOUNTS}>+ Add account number</button>
      </div>

      <div className="selected-account-list">
        {accounts.map((account, index) => (
          <article key={account.gl_account} className="selected-account">
            <span className="account-order">{String(index + 1).padStart(2, '0')}</span>
            <div><strong>{account.label}</strong><small>{account.gl_account}{account.account_type ? ` · ${account.account_type}` : ''}</small></div>
            <span className="verified-account">Verified</span>
            <button type="button" aria-label={`Remove ${account.label}`} onClick={() => removeAccount(account.gl_account)} disabled={disabled}>Remove</button>
          </article>
        ))}
      </div>

      <div className="account-groupings">
        <div className="account-groupings-heading"><div><strong>Saved account groupings</strong><small>Keep a reusable bundle in this browser. Loading always rechecks every account.</small></div></div>
        <div className="account-grouping-save">
          <input type="text" value={groupingName} onChange={(event) => setGroupingName(event.target.value)} placeholder="Name this grouping" maxLength={60} aria-label="New account grouping name" disabled={disabled} />
          <button type="button" onClick={saveGrouping} disabled={disabled || accounts.length === 0}>Save grouping</button>
        </div>
        {groupings.length > 0 && <div className="account-grouping-list">{groupings.map((grouping) => <div className="account-grouping" key={grouping.id}><span><strong>{grouping.name}</strong><small>{grouping.accounts.length} {grouping.accounts.length === 1 ? 'account' : 'accounts'}</small></span><button type="button" onClick={() => void loadGrouping(grouping)} disabled={disabled || Boolean(loadingGrouping)}>{loadingGrouping === grouping.id ? 'Checking…' : 'Load'}</button><button type="button" className="delete-grouping" onClick={() => deleteGrouping(grouping)} disabled={disabled || Boolean(loadingGrouping)} aria-label={`Delete ${grouping.name}`}>×</button></div>)}</div>}
      </div>

      {adding && (
        <div className="account-search-panel">
          <div className="account-search-heading"><div><strong>Find an active account</strong><small>Search by full number, number prefix, or account name.</small></div><button type="button" onClick={() => { setAdding(false); setQuery(''); setMatches([]); setMessage(''); }}>Cancel</button></div>
          <label><span>Account number or name</span><input autoFocus type="search" value={query} onChange={(event) => updateQuery(event.target.value)} placeholder="Try 50100, fuel, or driver wages" maxLength={60} /></label>
          <div className="account-search-shortcuts"><span>Suggested searches</span><button type="button" onClick={() => setQuery('fuel')}>Fuel</button><button type="button" onClick={() => setQuery('driver wages')}>Driver wages</button></div>
          {loading && <p className="account-search-message">Checking the active GL catalog…</p>}
          {!loading && matches.length > 0 && <div className="account-search-results">{matches.map((account) => <button type="button" key={account.gl_account} onClick={() => addAccount(account)}><span><strong>{account.gl_account}</strong><small>{account.account_type || 'Active account'}</small></span><span>{account.label}</span><b>Add</b></button>)}</div>}
          {!loading && message && <p className="account-search-message error">{message}</p>}
        </div>
      )}
      {!adding && message && <p className="account-search-message error">{message}</p>}
      <p className="account-validation-note">Only active accounts returned by the company GL catalog can be selected. The backend verifies the full list again before querying ledger entries.</p>
    </section>
  );
}
