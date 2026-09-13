'use client';
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import {
  Leaf,
  CalendarDays,
  MessageCircle,
  BookOpen,
  Globe2,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  Clock3,
  ChevronRight,
  UserRound,
  LockKeyhole,
  Check,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { ChatRoom } from './chat-room';
import { LanguageNotice } from './language-notice';
import { useAgentTools } from './use-agent-tools';
import { useAdmission, type Booking } from './use-admission';
type Lang = 'tr' | 'en';
type Slot = { starts_at: string; available: boolean };
export default function Mindful() {
  const [lang, setLang] = useState<Lang>('en'),
    [selectedView, setView] = useState('booking'),
    [step, setStep] = useState(1);
  const [first, setFirst] = useState(''),
    [last, setLast] = useState(''),
    [gender, setGender] = useState('unspecified');
  const [slots, setSlots] = useState<Slot[]>([]),
    [bookings, setBookings] = useState<Booking[]>([]),
    [slot, setSlot] = useState('now'),
    [adult, setAdult] = useState(false),
    [online, setOnline] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [modal, setModal] = useState('');
  const [detailsSubmitted, setDetailsSubmitted] = useState(false);
  const nameIssue = (value: string) => {
    if (!value.trim()) return 'required';
    if (value.trim().length > 60) return 'invalid';
    for (const character of value) {
      if (character.charCodeAt(0) < 32) return 'invalid';
    }
    return null;
  };
  const firstIssue = detailsSubmitted ? nameIssue(first) : null;
  const lastIssue = detailsSubmitted ? nameIssue(last) : null;
  const {
    admission,
    verified,
    request: admissionRequest,
  } = useAdmission(online);
  const admittedBooking = admission?.booking;
  const inSessionView = selectedView === 'room' || selectedView === 'waiting';
  const view =
    inSessionView && verified && admission
      ? admission.state === 'active'
        ? 'room'
        : admission.state === 'waiting'
          ? 'waiting'
          : 'sessions'
      : selectedView;
  const t = (tr: string, en: string) => (lang === 'tr' ? tr : en);
  const date = (v: string, o: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat(lang === 'tr' ? 'tr-TR' : 'en-GB', o).format(
      new Date(v),
    );
  async function refresh() {
    try {
      await api('/bootstrap', 'POST');
      const [s, b] = await Promise.all([
        api<Slot[]>('/slots'),
        api<Booking[]>('/bookings'),
      ]);
      setSlots(s);
      setBookings(b);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }
  useEffect(() => {
    let active = true;
    void api('/bootstrap', 'POST')
      .then(() =>
        Promise.all([api<Slot[]>('/slots'), api<Booking[]>('/bookings')]),
      )
      .then(
        ([times, reservations]) => {
          if (active) {
            setSlots(times);
            setBookings(reservations);
            setOnline(true);
          }
        },
        () => {
          if (active) setOnline(false);
        },
      );
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const stageAppointment = useCallback((language: Lang) => {
    setLang(language);
    setStep(1);
    setView('booking');
  }, []);
  useAgentTools(stageAppointment);
  async function reserve() {
    setBusy(true);
    setError('');
    try {
      const booking = await api<Booking>('/bookings', 'POST', {
        first_name: first,
        last_name: last,
        gender,
        language: lang,
        starts_at: slot === 'now' ? null : slot,
        adult_consent: adult,
      });
      await refresh();
      setView('sessions');
      setStep(1);
      setFirst('');
      setLast('');
      setDetailsSubmitted(false);
      setSlot('now');
      setAdult(false);
      if (booking.booking_type === 'immediate') await enter(booking.id);
    } catch (e) {
      setError((e as Error).message);
      await refresh();
    } finally {
      setBusy(false);
    }
  }
  async function enter(bookingId: string) {
    setBusy(true);
    setError('');
    try {
      const result = await admissionRequest('join', bookingId);
      setView(result.state === 'active' ? 'room' : 'waiting');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function leave() {
    if (!admittedBooking) return;
    setBusy(true);
    setError('');
    try {
      await admissionRequest('leave', admittedBooking.id);
      setView('sessions');
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function cancel() {
    setBusy(true);
    try {
      await api('/bookings/' + modal, 'DELETE');
      await admissionRequest('status');
      await refresh();
      setModal('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const nav = [
    {
      id: 'booking',
      Icon: CalendarDays,
      label: t('Randevu oluştur', 'Book a session'),
    },
    {
      id: 'sessions',
      Icon: MessageCircle,
      label: t('Görüşmelerim', 'My sessions'),
    },
    { id: 'sources', Icon: BookOpen, label: t('Kaynaklar', 'Resources') },
  ];
  const heading = (eyebrow: string, title: string, sub: string) => (
    <div className="heading">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p>{sub}</p>
    </div>
  );
  const fieldSelect = (
    id: string,
    label: string,
    value: string,
    onChange: (v: string) => void,
    options: string[][],
  ) => (
    <div className="field">
      <label id={id}>{label}</label>
      <Select value={value} onValueChange={(v) => onChange(String(v))}>
        <SelectTrigger aria-labelledby={id}>
          <SelectValue>{options.find((o) => o[0] === value)?.[1]}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {options.map(([v, l]) => (
            <SelectItem key={v} value={v}>
              {l}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
  return (
    <div className="shell">
      <a className="skip" href="#main">
        {t('İçeriğe geç', 'Skip to content')}
      </a>
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span>
            <Leaf size={25} />
          </span>
          <div>
            mindful<em>.</em>
            <small>SPACE TO TALK</small>
          </div>
        </Link>
        <p className="nav-label">{t('KENDİNE BİR ALAN', 'YOUR SPACE')}</p>
        <nav aria-label={t('Ana menü', 'Main navigation')}>
          {nav.map(({ id, Icon, label }) => (
            <button
              key={id}
              className={view === id ? 'active' : ''}
              aria-current={view === id ? 'page' : undefined}
              onClick={() => {
                setView(id);
                setError('');
              }}
            >
              <Icon size={19} />
              {label}
              {id === 'sessions' && bookings.length > 0 && (
                <b>{bookings.length}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-quote">
          <Leaf size={25} />
          <p>
            {t(
              'Bazen iyi bir başlangıç, kendine ayırdığın küçük bir andır.',
              'Sometimes a good beginning is a little time for yourself.',
            )}
          </p>
          <small>— {t('kendi hızında', 'at your own pace')}</small>
        </div>
        <div className="local-status">
          <i />
          {t('Deneysel AI', 'Experimental AI')}
          <span>0.1</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            {t('Kişisel alanın', 'Your space')}
            <ChevronRight size={14} />
            <strong>
              {nav.find((n) => n.id === view)?.label ||
                t('Görüşme odası', 'Session room')}
            </strong>
          </div>
          <div>
            <span className="project-tag">
              {t('Deneysel proje', 'Experimental project')}
            </span>
            <fieldset className="language-switch" aria-label="Language / Dil">
              <Globe2 size={16} aria-hidden="true" />
              <button
                type="button"
                lang="en"
                aria-pressed={lang === 'en'}
                onClick={() => setLang('en')}
              >
                English
              </button>
              <span aria-hidden="true">/</span>
              <button
                type="button"
                lang="tr"
                aria-pressed={lang === 'tr'}
                onClick={() => setLang('tr')}
              >
                Türkçe
              </button>
            </fieldset>
          </div>
        </header>
        <main id="main" className="workspace">
          <div className="disclaimer">
            <ShieldCheck size={19} />
            <p>
              {t(
                'Burası deneysel bir AI destek alanı. Gerçek bir psikolog, terapi veya acil yardım hizmeti değildir.',
                'This is an experimental AI support space. It is not a psychologist, therapy, or emergency service.',
              )}
            </p>
            <button onClick={() => setModal('about')}>
              {t('Bilgi al', 'Learn more')}
              <ChevronRight size={14} />
            </button>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {inSessionView && verified && admission?.state === 'idle' && (
            <div className="notice">
              {t(
                'Görüşmen veya bekleme sıran sona erdi. Randevularından yeniden katılabilir veya yeni bir randevu oluşturabilirsin.',
                'Your session or waiting place has ended. Rejoin through your appointments or create a new one.',
              )}
            </div>
          )}
          {admission &&
            admission.state !== 'idle' &&
            view !== 'room' &&
            view !== 'waiting' && (
              <div className="admission-banner">
                <Clock3 size={19} />
                <span>
                  {admission.state === 'active'
                    ? t('Görüşme alanın açık.', 'Your session space is open.')
                    : t(
                        'Bekleme sıran korunuyor.',
                        'Your place in line is held.',
                      )}
                </span>
                <Button
                  variant="outline"
                  onClick={() =>
                    setView(admission.state === 'active' ? 'room' : 'waiting')
                  }
                >
                  {t('Geri dön', 'Return')}
                </Button>
              </div>
            )}
          {view === 'booking' && (
            <>
              {heading(
                t('KENDİN İÇİN KÜÇÜK BİR MOLA', 'A LITTLE TIME FOR YOURSELF'),
                t('Bugün, kendine yer aç.', 'Make space for yourself.'),
                t(
                  'Sana uygun zamanı seç ve kendine bir alan ayır.',
                  'Choose a time and make a little space for yourself.',
                ),
              )}
              <div className="booking-grid">
                <section
                  className="form-card"
                  aria-label={t('Randevu formu', 'Booking form')}
                >
                  <div className="steps">
                    {[
                      t('Seni tanıyalım', 'About you'),
                      t('Zamanını seç', 'Choose a time'),
                    ].map((s, i) => (
                      <div
                        key={s}
                        className={
                          step === i + 1
                            ? 'current'
                            : step > i + 1
                              ? 'done'
                              : ''
                        }
                      >
                        <span>
                          {step > i + 1 ? <Check size={14} /> : '0' + (i + 1)}
                        </span>
                        <strong>{s}</strong>
                      </div>
                    ))}
                  </div>
                  <form
                    noValidate
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (step === 1) {
                        setDetailsSubmitted(true);
                        const invalidName = nameIssue(first)
                          ? 'first_name'
                          : nameIssue(last)
                            ? 'last_name'
                            : null;
                        if (invalidName) {
                          const field =
                            e.currentTarget.elements.namedItem(invalidName);
                          if (field instanceof HTMLInputElement) field.focus();
                          return;
                        }
                      }
                      if (step < 2) setStep(step + 1);
                      else void reserve();
                    }}
                  >
                    {step === 1 && (
                      <div className="form-body">
                        <div className="section-heading">
                          <span>
                            <UserRound size={22} />
                          </span>
                          <div>
                            <h2>
                              {t(
                                'Önce birkaç küçük detay.',
                                'First, a few small details.',
                              )}
                            </h2>
                            <p>
                              {t(
                                'Görüşmeni sana göre hazırlayalım.',
                                'Let’s get your session ready.',
                              )}
                            </p>
                          </div>
                        </div>
                        <div className="fields">
                          <label>
                            {t('Adın', 'First name')}
                            <Input
                              name="first_name"
                              required
                              aria-invalid={!!firstIssue}
                              aria-describedby={
                                firstIssue ? 'first-name-error' : undefined
                              }
                              maxLength={60}
                              value={first}
                              onChange={(e) => setFirst(e.target.value)}
                              placeholder={t('Adını yaz', 'Your first name')}
                              autoComplete="off"
                            />
                            {firstIssue && (
                              <span
                                id="first-name-error"
                                className="field-error"
                                role="alert"
                              >
                                {firstIssue === 'required'
                                  ? t(
                                      'Lütfen adını yaz.',
                                      'Please enter your first name.',
                                    )
                                  : t(
                                      'Lütfen en fazla 60 karakterlik geçerli bir ad yaz.',
                                      'Please enter a valid first name of up to 60 characters.',
                                    )}
                              </span>
                            )}
                          </label>
                          <label>
                            {t('Soyadın', 'Last name')}
                            <Input
                              name="last_name"
                              required
                              aria-invalid={!!lastIssue}
                              aria-describedby={
                                lastIssue ? 'last-name-error' : undefined
                              }
                              maxLength={60}
                              value={last}
                              onChange={(e) => setLast(e.target.value)}
                              placeholder={t('Soyadını yaz', 'Your last name')}
                              autoComplete="off"
                            />
                            {lastIssue && (
                              <span
                                id="last-name-error"
                                className="field-error"
                                role="alert"
                              >
                                {lastIssue === 'required'
                                  ? t(
                                      'Lütfen soyadını yaz.',
                                      'Please enter your last name.',
                                    )
                                  : t(
                                      'Lütfen en fazla 60 karakterlik geçerli bir soyad yaz.',
                                      'Please enter a valid last name of up to 60 characters.',
                                    )}
                              </span>
                            )}
                          </label>
                        </div>
                        <div className="fields">
                          {fieldSelect(
                            'gender',
                            t('Cinsiyetin', 'Gender'),
                            gender,
                            setGender,
                            [
                              [
                                'unspecified',
                                t('Belirtmek istemiyorum', 'Prefer not to say'),
                              ],
                              ['female', t('Kadın', 'Woman')],
                              ['male', t('Erkek', 'Man')],
                              ['other', t('Diğer', 'Another identity')],
                            ],
                          )}
                          {fieldSelect(
                            'language',
                            t('Görüşme dili', 'Conversation language'),
                            lang,
                            (v) => setLang(v as Lang),
                            [
                              ['tr', 'Türkçe'],
                              ['en', 'English'],
                            ],
                          )}
                        </div>
                        {lang === 'tr' && <LanguageNotice language={lang} />}
                        <div className="privacy-note">
                          <LockKeyhole size={19} />
                          <div>
                            <strong>
                              {t(
                                'Her görüşme, yeni bir başlangıç.',
                                'Every session is a fresh start.',
                              )}
                            </strong>
                            <p>
                              {t(
                                'Planlanan yapıda sohbet geçmişin sonraki görüşmelere taşınmaz. Randevu bilgileri ayrı tutulur.',
                                'The planned conversation has no memory across sessions. Appointment details are stored separately.',
                              )}
                            </p>
                          </div>
                        </div>
                        <p className="hint">
                          {t(
                            'Bir takma ad kullanabilirsin; gereksiz kişisel veya hassas bilgi paylaşma.',
                            'You may use a nickname; avoid sharing unnecessary personal or sensitive details.',
                          )}
                        </p>
                      </div>
                    )}
                    {step === 2 && (
                      <div className="form-body">
                        <div className="section-heading">
                          <span>
                            <CalendarDays size={22} />
                          </span>
                          <div>
                            <h2>
                              {t(
                                'Kendine bir zaman ayır.',
                                'Set aside a little time.',
                              )}
                            </h2>
                            <p>
                              {t(
                                '20 dakikalık görüşme.',
                                'A 20-minute conversation.',
                              )}
                            </p>
                          </div>
                        </div>
                        <p className="hint">
                          {t(
                            'Saatler cihazının yerel saat diliminde gösterilir.',
                            'Times are shown in your device’s local time zone.',
                          )}
                        </p>
                        {online ? (
                          <RadioGroup
                            value={slot}
                            onValueChange={(v) => setSlot(String(v))}
                            className="slots"
                            aria-label={t('Randevu saati', 'Appointment time')}
                          >
                            <label
                              className={
                                'slot immediate-slot ' +
                                (slot === 'now' ? 'selected' : '')
                              }
                            >
                              <RadioGroupItem value="now" />
                              <span>
                                <strong>{t('Şimdi katıl', 'Join now')}</strong>
                                {t(
                                  'Yer varsa doğrudan gir, doluysa sıranı bekle.',
                                  'Enter when a space is free, or join the waiting room.',
                                )}
                              </span>
                              <ArrowRight size={20} />
                            </label>
                            {slots.map((s) => (
                              <label
                                key={s.starts_at}
                                className={
                                  'slot ' +
                                  (slot === s.starts_at ? 'selected ' : '') +
                                  (!s.available ? 'unavailable' : '')
                                }
                              >
                                <RadioGroupItem
                                  value={s.starts_at}
                                  disabled={!s.available}
                                />
                                <span>
                                  {date(s.starts_at, {
                                    day: 'numeric',
                                    month: 'short',
                                  })}
                                  <strong>
                                    {date(s.starts_at, {
                                      hour: '2-digit',
                                      minute: '2-digit',
                                    })}
                                  </strong>
                                </span>
                              </label>
                            ))}
                          </RadioGroup>
                        ) : (
                          <div className="notice">
                            {t(
                              'Hizmete şu anda ulaşılamıyor.',
                              'The service is currently unavailable.',
                            )}
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() => void refresh()}
                            >
                              {t('Tekrar bağlan', 'Reconnect')}
                            </Button>
                          </div>
                        )}
                        <label className="consent">
                          <Checkbox
                            checked={adult}
                            onCheckedChange={(v) => setAdult(Boolean(v))}
                          />
                          <span>
                            {t(
                              '18 yaşında veya üzerindeyim. Bunun deneysel bir AI destek uygulaması olduğunu ve profesyonel yardım sağlamadığını anladım.',
                              'I am 18 or older. I understand this is an experimental AI support application and does not provide professional care.',
                            )}
                          </span>
                        </label>
                        <div className="notice">
                          <Info size={18} />
                          {t(
                            'Sohbet, eğitim ve yanıt kontrolleri tamamlanan model kullanıma açıldığında çalışır. Güncel durumu görüşme alanında görebilirsin.',
                            'Chat is available once the trained model has completed its response checks and is enabled. The session space shows its current availability.',
                          )}
                        </div>
                      </div>
                    )}
                    <div className="form-footer">
                      {step > 1 ? (
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setStep(step - 1)}
                        >
                          <ArrowLeft size={16} />
                          {t('Geri', 'Back')}
                        </Button>
                      ) : (
                        <span>
                          <Clock3 size={15} />
                          {t('Yaklaşık 1 dakika', 'About 1 minute')}
                        </span>
                      )}
                      <Button
                        className="primary"
                        type="submit"
                        disabled={
                          busy || (step === 2 && (!slot || !adult || !online))
                        }
                      >
                        {busy
                          ? t('Kaydediliyor…', 'Saving…')
                          : step === 2
                            ? slot === 'now'
                              ? t('Görüşmeye katıl', 'Join session')
                              : t('Randevu oluştur', 'Book session')
                            : t('Devam et', 'Continue')}
                        <ArrowRight size={17} />
                      </Button>
                    </div>
                  </form>
                </section>
                <aside className="summary-column">
                  <div className="summary">
                    <div className="summary-top">
                      <span className="eyebrow">
                        {t('SENİN GÖRÜŞMEN', 'YOUR SESSION')}
                      </span>
                      <span>
                        <Leaf size={28} />
                      </span>
                    </div>
                    <h2>
                      {t('Kendi hızında.', 'At your pace.')}
                      <br />
                      {t('Kendi alanında.', 'In your own space.')}
                    </h2>
                    <p>
                      {t(
                        'Kusursuz cümleler kurmana gerek yok.',
                        'You don’t need to find the perfect words.',
                      )}
                    </p>
                    <div className="summary-details">
                      <div>
                        <Clock3 size={17} />
                        <span>{t('Görüşme süresi', 'Session length')}</span>
                        <strong>{t('20 dakika', '20 minutes')}</strong>
                      </div>
                      <div>
                        <Globe2 size={17} />
                        <span>{t('Dil', 'Language')}</span>
                        <strong>{lang === 'tr' ? 'Türkçe' : 'English'}</strong>
                      </div>
                      <div>
                        <MessageCircle size={17} />
                        <span>{t('Biçim', 'Style')}</span>
                        <strong>{t('Sohbet', 'Chat')}</strong>
                      </div>
                    </div>
                    <div className="summary-bottom">
                      <Check size={16} />
                      {t('Ücretsiz · 18 yaş ve üzeri', 'Free · Adults 18+')}
                    </div>
                  </div>
                  <div className="side-info">
                    <ShieldCheck size={22} />
                    <div>
                      <h3>{t('Kontrol sende.', 'You are in control.')}</h3>
                      <p>
                        {t(
                          'Randevunu iptal edebilir, görüşmeni istediğin zaman bitirebilirsin.',
                          'You can cancel your appointment or end a conversation whenever you wish.',
                        )}
                      </p>
                    </div>
                  </div>
                </aside>
              </div>
            </>
          )}
          {view === 'sessions' && (
            <>
              {heading(
                t('SANA AYRILAN ZAMAN', 'TIME FOR YOU'),
                t('Görüşmelerim', 'My sessions'),
                t(
                  'Randevularını buradan yönet.',
                  'Manage your appointments here.',
                ),
              )}
              <div className="notice">
                <Info size={19} />
                {t(
                  'Bu deneysel AI sohbeti profesyonel psikolojik yardımın yerini tutmaz. Sohbetin kullanılabilirliğini görüşme alanında görebilirsin.',
                  'This experimental AI conversation does not replace professional psychological care. Check availability inside your session space.',
                )}
              </div>
              {bookings.length === 0 ? (
                <div className="empty">
                  <CalendarDays size={38} />
                  <h2>
                    {t('Henüz bir randevun yok.', 'No appointments yet.')}
                  </h2>
                  <p>
                    {t(
                      'İlk deneme randevunu oluşturmakla başlayabilirsin.',
                      'Start by creating a practice appointment.',
                    )}
                  </p>
                  <Button
                    className="primary"
                    onClick={() => setView('booking')}
                  >
                    {t('Randevu oluştur', 'Book a session')}
                    <ArrowRight size={17} />
                  </Button>
                </div>
              ) : (
                <div className="appointments">
                  {bookings.map((b) => (
                    <article key={b.id}>
                      <div className="date-block">
                        <strong>{date(b.starts_at, { day: 'numeric' })}</strong>
                        <span>{date(b.starts_at, { month: 'short' })}</span>
                      </div>
                      <div>
                        <small>
                          {t('Deneme randevusu', 'Practice appointment')}
                        </small>
                        <h2>
                          {date(b.starts_at, {
                            weekday: 'long',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </h2>
                        <p>
                          20 {t('dakika', 'minutes')} ·{' '}
                          {b.language === 'tr' ? 'Türkçe' : 'English'} ·{' '}
                          {t('Sohbet', 'Chat')}
                        </p>
                      </div>
                      <div className="appointment-actions">
                        <Button
                          variant="outline"
                          disabled={busy}
                          onClick={() => void enter(b.id)}
                        >
                          {t('Görüşmeye katıl', 'Join session')}
                          <ArrowRight size={16} />
                        </Button>
                        <Button variant="ghost" onClick={() => setModal(b.id)}>
                          {t('İptal et', 'Cancel')}
                        </Button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
          {(view === 'room' || view === 'waiting') && !verified && (
            <section className="empty" aria-live="polite" aria-busy="true">
              <Clock3 size={32} />
              <h2>
                {t('Bağlantı kontrol ediliyor.', 'Checking your connection.')}
              </h2>
              <p>
                {t(
                  'Sıran ve giriş iznin sunucudan doğrulanıyor. Bağlantı kesilirse yerin en fazla 90 saniye korunur.',
                  'Your place and access are being verified. A disconnected place is held for up to 90 seconds.',
                )}
              </p>
              <Button variant="outline" onClick={() => void refresh()}>
                {t('Yeniden bağlan', 'Reconnect')}
              </Button>
            </section>
          )}
          {view === 'waiting' && verified && admission?.state === 'waiting' && (
            <section className="waiting-room" aria-labelledby="waiting-title">
              <div className="waiting-symbol">
                <Leaf size={36} />
              </div>
              <div className="eyebrow">
                {t('BEKLEME ALANI', 'WAITING ROOM')}
              </div>
              <h1 id="waiting-title">
                {t('Birazdan, senin zamanın.', 'Soon, a little time for you.')}
              </h1>
              <p>
                {t(
                  'Görüşme alanı şu an dolu. Yer açıldığında otomatik olarak içeri alınacaksın.',
                  'The session space is full. You will enter automatically when a place opens.',
                )}
              </p>
              <output
                className="queue-number"
                aria-live="polite"
                aria-atomic="true"
              >
                <strong>{admission.people_ahead}</strong>
                <span>{t('kişi senden önce', 'people ahead of you')}</span>
              </output>
              <div className="queue-details">
                <div>
                  <span>{t('İçeride', 'In session')}</span>
                  <strong>
                    {admission.active_count} / {admission.capacity}
                  </strong>
                </div>
                <div>
                  <span>
                    {t('Bekleyenler arasında sıran', 'Your waiting position')}
                  </span>
                  <strong>{admission.queue_position}</strong>
                </div>
              </div>
              <p className="queue-note">
                {t(
                  'Bu sekmeyi açık tut. Sıra 10 saniyede bir güncellenir. Görüşmeler en fazla 20 dakika sürer; kesin bekleme süresi verilemez.',
                  'Keep this tab open. Your place updates every 10 seconds. Sessions last up to 20 minutes; waiting time can vary.',
                )}
              </p>
              <div className="notice">
                <Info size={18} />
                {t(
                  'Sıran geldiğinde görüşme alanın açılır. AI hizmetinin durumu içeride ayrıca gösterilir.',
                  'Your session space opens when your turn arrives. AI availability is shown separately inside.',
                )}
              </div>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => void leave()}
              >
                {t('Sıradan ayrıl', 'Leave the queue')}
              </Button>
            </section>
          )}
          {view === 'room' && verified && admission?.state === 'active' && (
            <>
              {heading(
                t('GÖRÜŞME ALANI', 'YOUR SESSION SPACE'),
                t('Sözcüklerine bir alan.', 'A space for your words.'),
                t(
                  'Kendi hızında konuş. İstediğin zaman ara verebilirsin.',
                  'Talk at your own pace. You can pause whenever you like.',
                ),
              )}
              <div className="admission-banner">
                <Check size={19} />
                <span>
                  {t(
                    'Girişin onaylandı. Alanın şu saate kadar ayrıldı:',
                    'You are admitted. Your space is reserved until:',
                  )}{' '}
                  <strong>
                    {date(
                      new Date((admission.deadline || 0) * 1000).toISOString(),
                      { hour: '2-digit', minute: '2-digit' },
                    )}
                  </strong>
                </span>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => void leave()}
                >
                  {t('Görüşmeyi bitir', 'End session')}
                </Button>
              </div>
              <ChatRoom
                key={admittedBooking?.id}
                bookingId={admittedBooking!.id}
                language={lang}
                conversationLanguage={admittedBooking!.language}
              />
              <Button
                variant="ghost"
                className="back-button"
                disabled={busy}
                onClick={() => void leave()}
              >
                <ArrowLeft size={17} />
                {t('Görüşmeyi bitir ve çık', 'End session and leave')}
              </Button>
            </>
          )}
          {view === 'sources' && (
            <>
              {heading(
                t('BİLGİYE DAYALI BİR YAKLAŞIM', 'A SOURCE-GROUNDED APPROACH'),
                t('Okumak için bir başlangıç.', 'A place to start reading.'),
                t(
                  'Bilgi havuzu için seçilen, herkese açık kaynaklar.',
                  'Public resources selected for the future knowledge base.',
                ),
              )}
              <div className="resources">
                {[
                  {
                    title: 'Caring for Your Mental Health',
                    url: 'https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health',
                    tag: 'SELF-CARE',
                    text: t(
                      'Ruh sağlığını destekleyen günlük alışkanlıklar.',
                      'Everyday habits that support mental well-being.',
                    ),
                  },
                  {
                    title: 'I’m So Stressed Out!',
                    url: 'https://www.nimh.nih.gov/health/publications/so-stressed-out-fact-sheet',
                    tag: 'STRESS',
                    text: t(
                      'Stres, kaygı ve ne zaman destek aranabileceği.',
                      'Stress, anxiety, and when to seek support.',
                    ),
                  },
                ].map((s) => (
                  <a
                    key={s.url}
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <div>
                      <BookOpen size={25} />
                      <span>{s.tag}</span>
                    </div>
                    <small>NATIONAL INSTITUTE OF MENTAL HEALTH</small>
                    <h2>{s.title}</h2>
                    <p>{s.text}</p>
                    <strong>
                      {t('Kaynağı oku', 'Read the source')}
                      <ArrowRight size={17} />
                    </strong>
                  </a>
                ))}
              </div>
              <p className="source-note">
                {t(
                  'Kaynak metinler İngilizcedir ve genel bilgilendirme içindir. NIMH bu projeyi onaylamamıştır. Kaynak kullanımı klinik doğrulama anlamına gelmez.',
                  'Reference texts are in English and provide general information. NIMH does not endorse this project. Using references does not establish clinical validation.',
                )}
              </p>
            </>
          )}
          <footer>
            <span>
              mindful. <small>© 2026</small>
            </span>
            <div>
              <button onClick={() => setModal('privacy')}>
                {t('Gizlilik', 'Privacy')}
              </button>
              <button onClick={() => setModal('about')}>
                {t('Proje hakkında', 'About the project')}
              </button>
              <button onClick={() => setModal('help')}>
                {t('Acil desteğe ihtiyacım var', 'I need urgent support')}
              </button>
            </div>
          </footer>
        </main>
      </div>
      <Dialog
        open={!!modal}
        onOpenChange={(v) => {
          if (!v) setModal('');
        }}
      >
        <DialogContent className="info-dialog">
          <DialogTitle>
            {modal === 'help'
              ? t('Acil destek', 'Urgent support')
              : modal === 'privacy'
                ? t('Bu sürümde gizlilik', 'Privacy in this version')
                : modal === 'about'
                  ? t(
                      'Deneysel bir AI destek uygulaması',
                      'An experimental AI support application',
                    )
                  : t('Randevuyu iptal et', 'Cancel appointment')}
          </DialogTitle>
          <DialogDescription>
            {modal === 'help'
              ? t(
                  'Yakın bir tehlike varsa bulunduğun yerdeki acil yardım numarasını ara veya en yakın acil servise başvur. Mümkünse güvendiğin birine haber ver. Bu uygulama acil yardım gönderemez; randevu saatini bekleme.',
                  'If there is immediate danger, call your local emergency number or go to the nearest emergency department. If possible, tell someone you trust. This app cannot dispatch help; do not wait for an appointment.',
                )
              : modal === 'privacy'
                ? t(
                    'Uygulama ve AI, Hugging Face sunucularında çalışır. Mesajlar yanıt üretmek için bu hizmete gönderilir; uygulama kalıcı sohbet geçmişi tutmaz ve mesajlarını eğitim için toplamaz. Görüşme sona erdiğinde veya süresi dolduğunda oturum belleği temizlenir. Randevu bilgileri ayrı tutulur; 24 saatlik erişim çerezi sona erdikten sonra ilişkili kayıtlar temizlenir. Sunucu yeniden başlarsa randevular kaybolabilir. Hizmet sağlayıcının kendi gizlilik politikası geçerlidir.',
                    'The application and AI run on Hugging Face servers. Messages are sent to that service to generate replies; this application does not keep permanent chat history or collect messages for training. Session memory is cleared when a conversation ends or expires. Appointment details are stored separately and associated records are removed after the 24-hour access cookie expires. A server restart may reset appointments. The hosting provider has its own privacy policy.',
                  )
                : modal === 'about'
                  ? t(
                      'Mindful, deneysel bir AI destek uygulamasıdır. Klinik olarak doğrulanmamıştır; teşhis, tedavi veya profesyonel psikolojik yardım sunmaz. Model yanlış veya uygun olmayan yanıtlar verebilir. Renk geçişleri görsel bir tercihtir ve tedavi etkisi iddiası taşımaz.',
                      'Mindful is an experimental AI support application. It is not clinically validated and does not provide diagnosis, treatment, or professional psychological care. The model can produce incorrect or unsuitable replies. Color transitions are a visual preference without claims of therapeutic effects.',
                    )
                  : t(
                      'Bu randevu silinecek ve saat yeniden kullanılabilir olacak.',
                      'This appointment will be deleted and the slot released.',
                    )}
          </DialogDescription>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {!['about', 'privacy', 'help'].includes(modal) && (
            <Button
              className="primary"
              disabled={busy}
              onClick={() => void cancel()}
            >
              {t('Randevuyu iptal et', 'Cancel appointment')}
            </Button>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
