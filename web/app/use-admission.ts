'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';

export type Booking = {
  id: string;
  starts_at: string;
  ends_at: string;
  booking_type: 'immediate' | 'scheduled';
  language: 'tr' | 'en';
};
export type Admission = {
  state: 'idle' | 'waiting' | 'active';
  capacity: number;
  active_count: number;
  waiting_count: number;
  people_ahead: number;
  queue_position: number;
  booking?: Booking;
  deadline?: number;
  lease_until?: number;
};
export function useAdmission(online: boolean) {
  const [admission, setAdmission] = useState<Admission | null>(null);
  const [verified, setVerified] = useState(false);
  const mounted = useRef(false);
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  // Serialize heartbeat and user actions so an older response cannot undo a leave/join.
  const request = useCallback((path: string, bookingId?: string) => {
    const run = chain.current
      .catch(() => undefined)
      .then(async () => {
        try {
          const result = await api<Admission>(
            '/admission/' + path,
            'POST',
            bookingId ? { booking_id: bookingId } : undefined,
          );
          if (mounted.current) {
            setAdmission(result);
            setVerified(true);
          }
          return result;
        } catch (error) {
          if (mounted.current) setVerified(false);
          throw error;
        }
      });
    chain.current = run;
    return run;
  }, []);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!online) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        await request('status');
      } catch {
        /* Retry; access stays unverified. */
      }
      if (!stopped) timer = setTimeout(() => void poll(), 10000);
    }
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [online, request]);
  return { admission, verified: online && verified, request };
}
