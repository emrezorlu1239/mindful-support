'use client';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Info, MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { api } from '@/lib/api';
import { LanguageNotice } from './language-notice';
import { checkedReply } from '@/lib/chat-transport';

type Lang = 'tr' | 'en';
type Message = {
  role: 'user' | 'assistant';
  content: string;
  sources?: { id: string; title: string; url: string }[];
};
type Reply = {
  reply: string;
  sources: NonNullable<Message['sources']>;
  palette: 'neutral' | 'sage' | 'tide' | 'warm';
};
export function ChatRoom({
  bookingId,
  language,
  conversationLanguage,
}: {
  bookingId: string;
  language: Lang;
  conversationLanguage: Lang;
}) {
  const [ready, setReady] = useState(false);
  const [historyReady, setHistoryReady] = useState(false);
  const [historyAttempt, setHistoryAttempt] = useState(0);
  const [historyError, setHistoryError] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const [ambient, setAmbient] = useState(true);
  const [palette, setPalette] = useState<Reply['palette']>('neutral');
  const pending = useRef<{ message: string; id: string } | null>(null);
  const t = (tr: string, en: string) => (language === 'tr' ? tr : en);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const status = await api<{ chat_enabled: boolean }>('/health');
        if (active) setReady(status.chat_enabled);
      } catch {
        if (active) setReady(false);
      }
      if (active) timer = setTimeout(() => void poll(), 15000);
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);
  useEffect(() => {
    let active = true;
    void api<{ messages: Message[] }>('/chat/history?booking_id=' + bookingId)
      .then((result) => {
        if (active) {
          setMessages(result.messages);
          setHistoryReady(true);
        }
      })
      .catch(() => {
        if (active) setHistoryError(true);
      });
    return () => {
      active = false;
    };
  }, [bookingId, historyAttempt]);
  async function send() {
    if (!ready || !historyReady || busy || !input.trim()) return;
    const content = input.trim();
    if (pending.current?.message !== content) {
      pending.current = { message: content, id: crypto.randomUUID() };
    }
    setBusy(true);
    setError(false);
    try {
      const signal = AbortSignal.timeout(120000);
      const response = await fetch('/api/chat', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        signal,
        body: JSON.stringify({
          booking_id: bookingId,
          request_id: pending.current.id,
          message: content,
        }),
      });
      if (!response.ok) throw Error('Chat unavailable');
      const result = (await checkedReply(response, signal)) as Reply;
      setMessages((previous) => [
        ...previous,
        { role: 'user', content },
        { role: 'assistant', content: result.reply, sources: result.sources },
      ]);
      setPalette(result.palette);
      setInput('');
      pending.current = null;
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="conversation-space"
      data-palette={ambient ? palette : 'neutral'}
      data-motion={ambient ? 'on' : 'off'}
      aria-label={t('Sohbet alanı', 'Conversation space')}
    >
      <div className="conversation-toolbar">
        <div>
          <MessageCircle size={20} />
          <strong>{t('Görüşme', 'Conversation')}</strong>
          <span>{conversationLanguage === 'tr' ? 'Türkçe' : 'English'}</span>
        </div>
        <label className="ambient-toggle">
          <Switch checked={ambient} onCheckedChange={setAmbient} />
          <span>{t('Yumuşak renk geçişleri', 'Gentle color transitions')}</span>
        </label>
      </div>
      {conversationLanguage === 'tr' && <LanguageNotice language={language} />}
      <p className="ambient-note">
        {t(
          'Renkler yalnızca görsel bir tercihtir; ruhsal durumunu teşhis etmez.',
          'Colors are a visual preference; they do not diagnose your mental state.',
        )}
      </p>
      <div
        className="conversation-messages"
        aria-live="polite"
        aria-relevant="additions"
      >
        {!ready && (
          <div className="chat-empty">
            <Info size={28} />
            <h2>
              {t(
                'Sohbet şu anda kullanılamıyor.',
                'Chat is currently unavailable.',
              )}
            </h2>
            <p>
              {t(
                'Görüşmeyi bitirip daha sonra geri gelebilirsin.',
                'You can end this session and return later.',
              )}
            </p>
          </div>
        )}
        {ready && messages.length === 0 && (
          <div className="chat-empty">
            <MessageCircle size={28} />
            <h2>
              {t(
                'Bugün ne hakkında konuşmak istersin?',
                'What would you like to talk about today?',
              )}
            </h2>
            <p>
              {t(
                'Bu deneysel bir AI sohbetidir. Sana uygun gelmeyen önerileri uygulamak zorunda değilsin.',
                'This is an experimental AI conversation. You can decline any suggestion that does not feel right for you.',
              )}
            </p>
          </div>
        )}
        {messages.map((message, index) => (
          <article
            key={index}
            className={'conversation-message ' + message.role}
          >
            <strong>
              {message.role === 'user' ? t('Sen', 'You') : 'Mindful · AI'}
            </strong>
            <p>{message.content}</p>
            {message.sources?.map((source) => (
              <a
                key={source.id}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {source.title}
              </a>
            ))}
          </article>
        ))}
        {busy && (
          <p>
            {t(
              'Yanıt hazırlanıyor ve kontrol ediliyor…',
              'Preparing and checking the reply…',
            )}
          </p>
        )}
      </div>
      {historyError && (
        <div role="alert">
          <p>{t('Oturum yüklenemedi.', 'The session could not be loaded.')}</p>
          <Button
            type="button"
            onClick={() => {
              setHistoryError(false);
              setHistoryAttempt((value) => value + 1);
            }}
          >
            {t('Yeniden dene', 'Try again')}
          </Button>
        </div>
      )}
      {error && (
        <p className="error" role="alert">
          {t(
            'Yanıt tamamlanamadı. Mesajın kutuda duruyor; bağlantını kontrol edip yeniden deneyebilirsin.',
            'The reply could not be completed. Your message is still in the box; check your connection and try again.',
          )}
        </p>
      )}
      <form
        className="conversation-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <Input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={!ready || !historyReady || busy}
          maxLength={1500}
          aria-label={t('Mesajın', 'Your message')}
          placeholder={t(
            'Aklından geçenleri yaz…',
            'Write what is on your mind…',
          )}
        />
        <Button
          type="submit"
          disabled={!ready || !historyReady || busy || !input.trim()}
          size="icon"
          aria-label={t('Gönder', 'Send')}
        >
          <ArrowRight size={20} />
        </Button>
      </form>
      <p className="ambient-note">
        {t(
          'Oturum içeriği kalıcı sohbet geçmişine kaydedilmez. Görüşme bitince oturum belleği silinir.',
          'Conversation content is not saved as permanent chat history. Session memory is cleared when the session ends.',
        )}
      </p>
    </section>
  );
}
