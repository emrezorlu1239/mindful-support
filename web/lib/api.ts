export async function api<T = Record<string, unknown>>(
  path: string,
  method = 'GET',
  body?: object,
): Promise<T> {
  const response = await fetch('/api' + path, {
    method,
    credentials: 'same-origin',
    signal: AbortSignal.timeout(10000),
    headers: { 'Content-Type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) {
    const details = (await response.json().catch(() => ({}))) as {
      detail?: unknown;
    };
    throw new Error(
      typeof details.detail === 'string'
        ? details.detail
        : 'İşlem tamamlanamadı / Request failed.',
    );
  }
  return (await response.json()) as T;
}
