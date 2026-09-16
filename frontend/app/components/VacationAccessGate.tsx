import ReportAccessGate, { clearSavedReportPassword } from './ReportAccessGate';

const SESSION_KEY = 'sharp-vacation-report-password';

type Props = {
  apiBase: string;
  onUnlock: (password: string) => void;
};

export function clearSavedVacationPassword() {
  clearSavedReportPassword(SESSION_KEY);
}

export default function VacationAccessGate({ apiBase, onUnlock }: Props) {
  return (
    <ReportAccessGate apiBase={apiBase} unlockPath="/reports/vacation/unlock" sessionKey={SESSION_KEY} mark="VB" eyebrow="Protected people view" title="Vacation access required" description="Employee vacation balances and estimated payouts are hidden until this tab is unlocked." passwordLabel="Vacation report password" submitLabel="Unlock vacation view" emptyMessage="Enter the vacation report password." onUnlock={onUnlock} />
  );
}
