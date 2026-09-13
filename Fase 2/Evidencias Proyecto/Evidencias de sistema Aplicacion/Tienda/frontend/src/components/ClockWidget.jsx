import { CalendarDays, Clock3 } from 'lucide-react';
import { useEffect, useState } from 'react';

const DATE_FORMAT = new Intl.DateTimeFormat('es-CL', {
  weekday: 'long',
  day: '2-digit',
  month: 'long',
});

export function ClockWidget() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const date = DATE_FORMAT.format(now);

  return (
    <section className="clock-widget" aria-label="Fecha y hora actuales">
      <div className="clock-widget__time">
        <Clock3 aria-hidden="true" size={18} />
        <time dateTime={now.toISOString()}>
          {now.toLocaleTimeString('es-CL', { hour12: false })}
        </time>
      </div>
      <div className="clock-widget__date">
        <CalendarDays aria-hidden="true" size={14} />
        <span>{date.charAt(0).toUpperCase() + date.slice(1)}</span>
      </div>
    </section>
  );
}
