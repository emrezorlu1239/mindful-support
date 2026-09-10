// Same-origin Gradio calls contain an opaque ticket, never the message or reply.
export async function checkedReply(response: Response, signal: AbortSignal) {
  const payload = await response.json();
  if (response.status !== 202) return payload;
  if (payload.transport !== 'gradio' || !/^[A-Za-z0-9_-]{43}$/.test(payload.ticket)) {
    throw Error('Invalid compute handoff');
  }
  const base = '/api/gpu/gradio_api/call/reply';
  const queued = await fetch(base, {
    method: 'POST', credentials: 'same-origin', signal,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: [payload.ticket] }),
  });
  if (!queued.ok) throw Error('GPU queue unavailable');
  const { event_id } = await queued.json();
  if (!/^[a-f0-9]{32}$/.test(event_id)) throw Error('Invalid GPU event');
  const events = await fetch(base + '/' + event_id, { credentials: 'same-origin', signal });
  if (!events.ok || !events.body) throw Error('GPU unavailable');
  const reader = events.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let complete = false;
  try {
    while (!complete) {
      const part = await reader.read();
      if (part.done) break;
      buffer += decoder.decode(part.value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n');
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const event = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (/^event: error$/m.test(event)) throw Error('GPU quota or execution unavailable');
        if (/^event: complete$/m.test(event)) complete = true;
      }
      if (buffer.length > 8192) throw Error('Invalid GPU response');
    }
  } finally {
    await reader.cancel();
  }
  if (!complete) throw Error('GPU reply interrupted');
  const result = await fetch('/api/chat/result?ticket=' + payload.ticket, {
    credentials: 'same-origin', signal,
  });
  if (!result.ok || result.status === 202) throw Error('Reply unavailable');
  return result.json();
}
