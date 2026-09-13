import React from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck, Sparkles, UserRound } from 'lucide-react';
import { authService } from '../services/api.js';
import loginArtwork from '../../assets/logo_login5.png';
import brandLogo from '../../assets/logo_girasol.png';

export function LoginPage({ onLogin }) {
  const [rut, setRut] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [error, setError] = React.useState('');
  const [invalid, setInvalid] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  async function submit(event) {
    event.preventDefault();
    const cleanRut = rut.trim();
    setError(''); setInvalid('');
    if (!cleanRut && !password) { setError('Ingresa tu usuario y clave para continuar.'); setInvalid('both'); return; }
    if (!cleanRut) { setError('Ingresa tu usuario o RUT.'); setInvalid('rut'); return; }
    if (!password) { setError('Ingresa tu clave.'); setInvalid('password'); return; }
    setLoading(true);
    try {
      onLogin(await authService.login(cleanRut, password));
    } catch (requestError) {
      const status = requestError.response?.status;
      setInvalid(status === 401 ? 'both' : '');
      setError(status === 401
        ? 'Usuario o contraseña incorrectos. Revisa los datos e inténtalo nuevamente.'
        : status === 503
          ? 'No fue posible conectar con la base de datos. Contacta al administrador.'
          : 'El servidor no está disponible en este momento. Inténtalo nuevamente.');
    } finally { setLoading(false); }
  }

  function clearError(field) {
    if (invalid === field || invalid === 'both') { setInvalid(''); setError(''); }
  }

  return <main className="login-shell">
    <section className="login-visual" style={{ '--login-artwork': `url(${loginArtwork})` }}>
      <div className="login-visual__brand"><img src={brandLogo} alt=""/><span>Girasol Boutique</span></div>
      <div className="login-visual__copy"><span><Sparkles/> Gestión simple y ordenada</span><h1>Todo tu negocio,<br/><em>en un solo lugar.</em></h1><p>Inventario, ventas, clientas y caja conectados para acompañar cada jornada.</p></div>
      <div className="login-visual__footer"><ShieldCheck/> Acceso exclusivo para personal autorizado</div>
    </section>

    <section className="login-access">
      <form className="login-card" onSubmit={submit} noValidate>
        <div className="login-card__mark">G</div>
        <p className="login-card__eyebrow">Panel administrativo</p>
        <h2>Bienvenido de vuelta</h2>
        <p className="login-card__intro">Ingresa tus credenciales para comenzar el turno.</p>

        <label className="login-field">
          <span>Usuario o RUT</span>
          <div className={invalid === 'rut' || invalid === 'both' ? 'is-invalid' : ''}><UserRound/><input autoFocus autoComplete="username" value={rut} onChange={e=>{setRut(e.target.value);clearError('rut')}} placeholder="Ej: 21300379" aria-invalid={invalid==='rut'||invalid==='both'}/></div>
        </label>
        <label className="login-field">
          <span>Clave</span>
          <div className={invalid === 'password' || invalid === 'both' ? 'is-invalid' : ''}><LockKeyhole/><input autoComplete="current-password" value={password} onChange={e=>{setPassword(e.target.value);clearError('password')}} placeholder="Ingresa tu clave" type={showPassword?'text':'password'} aria-invalid={invalid==='password'||invalid==='both'}/><button type="button" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?'Ocultar clave':'Mostrar clave'}>{showPassword?<EyeOff/>:<Eye/>}</button></div>
        </label>

        {error && <div className="login-error" role="alert"><span>!</span><p>{error}</p></div>}
        <button className="login-submit" type="submit" disabled={loading}>{loading?<><i/> Verificando…</>:<>Ingresar al sistema <ArrowRight/></>}</button>
        <p className="login-help">¿Problemas para ingresar? Contacta a la persona administradora.</p>
      </form>
      <footer>Girasol Boutique · Sistema de gestión</footer>
    </section>
  </main>;
}
