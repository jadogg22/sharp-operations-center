export async function reportError(response: Response, fallback: string): Promise<never> {
  const payload = await response.json().catch(() => null);
  throw new Error(payload?.detail ?? fallback);
}

export async function downloadResponse(
  response: Response,
  fallbackFilename: string,
): Promise<string> {
  if (!response.ok) await reportError(response, 'The report could not be generated.');
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') ?? '';
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? fallbackFilename;
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(downloadUrl);
  return filename;
}
