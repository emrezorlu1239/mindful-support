'use client';
import { useEffect } from 'react';
import { flushSync } from 'react-dom';

type Tool = {
  name: string;
  description: string;
  inputSchema: object;
  annotations: { readOnlyHint: boolean };
  execute(input: unknown): unknown;
};
type Registry = {
  registerTool(
    tool: Tool,
    options: { signal: AbortSignal },
  ): void | Promise<void>;
};

export function useAgentTools(stage: (language: 'tr' | 'en') => void) {
  useEffect(() => {
    const registry = (document as Document & { modelContext?: Registry })
      .modelContext;
    if (!registry?.registerTool) return;
    const lifecycle = new AbortController();
    const tools: Tool[] = [
      {
        name: 'read_available_appointment_times',
        description:
          'Read local practice appointment times. Does not reserve a time or start a conversation.',
        inputSchema: {
          type: 'object',
          properties: {},
          additionalProperties: false,
        },
        annotations: { readOnlyHint: true },
        async execute(input) {
          if (
            !input ||
            typeof input !== 'object' ||
            Array.isArray(input) ||
            Object.keys(input).length
          )
            throw Error('Expected an empty object.');
          const response = await fetch('/api/slots', { cache: 'no-store' });
          if (!response.ok) throw Error('Local booking service unavailable.');
          return response.json();
        },
      },
      {
        name: 'stage_practice_appointment',
        description:
          'Open the booking form with a language preference. Does not submit a reservation, assert adult consent, or start AI chat.',
        inputSchema: {
          type: 'object',
          properties: {
            language: { enum: ['tr', 'en'] },
          },
          required: ['language'],
          additionalProperties: false,
        },
        annotations: { readOnlyHint: false },
        execute(input) {
          if (!input || typeof input !== 'object' || Array.isArray(input))
            throw Error('Expected preferences.');
          const value = input as Record<string, unknown>;
          if (
            Object.keys(value).sort().join(',') !== 'language' ||
            !['tr', 'en'].includes(String(value.language))
          )
            throw Error('Invalid preferences.');
          flushSync(() => stage(value.language as 'tr' | 'en'));
          return { stage: 'booking_form', reserved: false };
        },
      },
    ];
    for (const tool of tools) {
      try {
        void Promise.resolve(
          registry.registerTool(tool, { signal: lifecycle.signal }),
        ).catch(() => {});
      } catch {
        /* Experimental browser API; ordinary UI remains available. */
      }
    }
    return () => lifecycle.abort();
  }, [stage]);
}
