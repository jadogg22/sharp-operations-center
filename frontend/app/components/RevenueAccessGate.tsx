'use client';

import ReportAccessGate, { clearSavedReportPassword } from './ReportAccessGate';

const SESSION_KEY = 'sharp-revenue-report-password';

type Props = {
  apiBase: string;
  onUnlock: (password: string) => void;
};

export function clearSavedRevenuePassword() {
  clearSavedReportPassword(SESSION_KEY);
}

export default function RevenueAccessGate({ apiBase, onUnlock }: Props) {
  return (
    <ReportAccessGate apiBase={apiBase} unlockPath="/reports/fleet-cost-revenue/unlock" sessionKey={SESSION_KEY} mark="$" eyebrow="Protected financial view" title="Revenue access required" description="Fleet costs, wages, fuel, and operating revenue are hidden until this tab is unlocked." passwordLabel="Revenue password" submitLabel="Unlock revenue view" emptyMessage="Enter the revenue report password." onUnlock={onUnlock} />
  );
}
