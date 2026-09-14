export class ChatError extends Error {
  constructor(public code: string) { super(code); }
}
async function responseError(response: Response): Promise<never> {
  const body = await response.json().catch(() => null);
  const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
  const code = detail && typeof detail === 'object' && 'code' in detail ? detail.code : null;
  const allowed = ['gpu_quota', 'gpu_duration', 'compute_unavailable'];
  throw new ChatError(typeof code === 'string' && allowed.includes(code) ? code :
    response.status === 429 ? 'busy' : [401, 403, 404, 409].includes(response.status) ? 'session' : 'compute_unavailable');
}
export function chatErrorText(error: unknown, language: 'tr' | 'en'): string {
  const code = error instanceof ChatError ? error.code :
    error instanceof DOMException && ['TimeoutError', 'AbortError'].includes(error.name) ? 'timeout' : 'network';
  const messages: Record<string, [string, string]> = {
    gpu_quota: ['Ücretsiz GPU kotası doldu. Daha sonra tekrar dene; mesajını değiştirmek kotayı yenilemez.', 'The free GPU quota has been reached. Please return later; changing your message will not reset it.'],
    gpu_duration: ['Sunucunun GPU süre sınırı bu isteğe izin vermiyor. Lütfen daha sonra tekrar dene.', 'The server GPU time limit does not allow this request. Please try again later.'],
    compute_unavailable: ['Yanıt sunucusu şu anda isteği tamamlayamadı. Biraz bekleyip tekrar dene.', 'The reply service could not complete this request. Please wait before trying again.'],
    busy: ['Bir yanıt bekliyor veya oturum sınırına ulaştın. Biraz bekle; sorun sürerse görüşmeyi bitir.', 'A reply is pending or a session limit was reached. Please wait; if this persists, end the session.'],
    session: ['Oturum veya yanıt isteği sona erdi. Görüşmelerim bölümünden oturum durumunu kontrol et.', 'The session or reply request expired. Check your session in My sessions.'],
    timeout: ['Yanıt zaman aşımına uğradı. Aynı mesajı yeniden deneyebilirsin.', 'The reply timed out. You can retry the same message.'],
    network: ['Sunucuya bağlantı tamamlanamadı. Bağlantını kontrol edip yeniden dene.', 'The connection to the service was interrupted. Check your connection and retry.'],
  };
  return (messages[code] ?? messages.compute_unavailable)[language === 'tr' ? 0 : 1] +
    (language === 'tr' ? ' Mesajın kutuda duruyor.' : ' Your message is still in the box.');
}

// Same-origin Gradio calls contain an opaque ticket, never the message or reply.
export async function checkedReply(response: Response, signal: AbortSignal) {
  if (!response.ok) return responseError(response);
  const payload = await response.json();
  if (response.status !== 202) return payload;
  if (!payload || typeof payload !== 'object' || !('transport' in payload) ||
      payload.transport !== 'gradio' || !('ticket' in payload) ||
      typeof payload.ticket !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(payload.ticket)) {
    throw Error('Invalid compute handoff');
  }
  // The official client performs HF's visitor quota handshake inside the Space iframe.
  const { Client } = await import('@gradio/client');
  signal.throwIfAborted();
  const client = await Client.connect(window.location.origin + '/api/gpu', {
    credentials: 'same-origin', events: ['data', 'status'],
  });
  const job = client.submit('/reply', [payload.ticket]);
  const cancel = () => { void job.cancel(); client.close(); };
  signal.addEventListener('abort', cancel, { once: true });
  try {
    signal.throwIfAborted();
    for await (const event of job) {
      signal.throwIfAborted();
      if (event.type === 'status' && event.stage === 'error') throw new ChatError('compute_unavailable');
    }
  } catch (failure) {
    signal.throwIfAborted();
    throw failure instanceof ChatError ? failure : new ChatError('compute_unavailable');
  } finally {
    signal.removeEventListener('abort', cancel);
    client.close();
  }
  signal.throwIfAborted();
  const result = await fetch('/api/chat/result?ticket=' + payload.ticket, {
    credentials: 'same-origin', signal,
  });
  if (!result.ok) return responseError(result);
  if (result.status === 202) throw new ChatError('busy');
  return result.json();
}
