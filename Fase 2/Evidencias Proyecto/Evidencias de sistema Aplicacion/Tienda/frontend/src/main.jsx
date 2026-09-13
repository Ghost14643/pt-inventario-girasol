import React from 'react';
import { createRoot } from 'react-dom/client';
import { LogOut, Store, X } from 'lucide-react';
import './styles.css';
import { MainMenu } from './pages/MainMenu.jsx';
import { InventarioPage } from './pages/InventarioPage.jsx';
import { VentasPage } from './pages/VentasPage.jsx';
import { ArqueoPage } from './pages/ArqueoPage.jsx';
import { IngresoMercaderiaPage } from './pages/IngresoMercaderiaPage.jsx';
import { ClientesPage } from './pages/ClientesPage.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { ConfiguracionPage } from './pages/ConfiguracionPage.jsx';
import { authService, cashService } from './services/api.js';

const localDate = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };

function App() {
  const [page, setPage] = React.useState('menu');
  const [dark, setDark] = React.useState(false);
  const [session, setSession] = React.useState(() => { try { return JSON.parse(localStorage.getItem('girasol:session')); } catch { return null; } });
  const [logoutPrompt, setLogoutPrompt] = React.useState(false);
  const [cashPrompt, setCashPrompt] = React.useState(null);
  const [openingCash, setOpeningCash] = React.useState(false);

  const finishLogout = React.useCallback(async () => { try { await authService.logout(); } catch { /* el cierre local debe continuar aunque el API no esté disponible */ } localStorage.removeItem('girasol:session'); setSession(null); setLogoutPrompt(false); setCashPrompt(null); }, []);
  React.useEffect(() => { const logout = () => setLogoutPrompt(true); window.addEventListener('girasol:logout', logout); return () => window.removeEventListener('girasol:logout', logout); }, []);
  React.useEffect(() => {
    if (!session) return;
    let active=true;
    cashService.status(localDate()).then(status => { if (active && !status.existe) setCashPrompt({type:'ask'}); }).catch(error => { if (active) setCashPrompt({type:'error', message:error?.response?.data?.detail || 'No fue posible comprobar el estado de la caja.'}); });
    return () => { active=false; };
  }, [session]);
  const login = data => { localStorage.setItem('girasol:session', JSON.stringify(data)); setSession(data); };
  async function openCash() {
    setOpeningCash(true);
    try { const result=await cashService.open(localDate()); setCashPrompt({type:'opened', result}); }
    catch (error) { setCashPrompt({type:'error', message:error?.response?.data?.detail || 'No fue posible abrir la caja.'}); }
    finally { setOpeningCash(false); }
  }
  const navigate = destination => { const routes={inventario:'/inventario',ventas:'/ventas',configuracion:'/configuracion',clientes:'/clientes',arqueo:'/arqueo','ingreso-mercaderia':'/ingreso-mercaderia',menu:'/'}; window.history.pushState({},'',routes[destination]??'/'); setPage(destination); };
  if (!session) return <LoginPage onLogin={login}/>;
  const common={session,dark,onToggleTheme:()=>setDark(v=>!v),onNavigate:navigate,onLogout:()=>setLogoutPrompt(true)};
  let content;
  if(page==='inventario') content=<InventarioPage {...common}/>;
  else if(page==='ventas') content=<VentasPage {...common}/>;
  else if(page==='arqueo') content=<ArqueoPage {...common}/>;
  else if(page==='clientes') content=<ClientesPage {...common}/>;
  else if(page==='ingreso-mercaderia') content=<IngresoMercaderiaPage {...common}/>;
  else if(page==='configuracion') content=<ConfiguracionPage {...common}/>;
  else content=<MainMenu {...common}/>;
  return <>{content}
    {logoutPrompt&&<div className={`modal-backdrop ${dark?'theme-dark':''}`}><div className="confirm-dialog"><span className="confirm-dialog__icon danger"><LogOut/></span><h2>¿Cerrar sesión?</h2><p>Se cerrará tu acceso a Girasol Boutique. Los datos guardados no se perderán.</p><div className="modal-actions"><button className="secondary-button" onClick={()=>setLogoutPrompt(false)}>Cancelar</button><button className="danger-button" onClick={finishLogout}>Sí, cerrar sesión</button></div></div></div>}
    {cashPrompt&&<div className={`modal-backdrop ${dark?'theme-dark':''}`}><div className="confirm-dialog cash-dialog"><button className="dialog-close" onClick={()=>setCashPrompt(null)} aria-label="Cerrar"><X/></button><span className="confirm-dialog__icon"><Store/></span>{cashPrompt.type==='ask'?<><h2>No hay caja abierta hoy</h2><p>Para dejar constancia del inicio del turno, ¿deseas abrir la caja del {new Intl.DateTimeFormat('es-CL',{dateStyle:'long'}).format(new Date())}?</p><div className="cash-dialog__note">Al abrirla se registrará la fecha y la hora. Los montos del cierre permanecerán pendientes.</div><div className="modal-actions"><button className="secondary-button" onClick={()=>setCashPrompt(null)}>Ahora no</button><button className="primary-button" disabled={openingCash} onClick={openCash}>{openingCash?'Abriendo…':'Abrir caja'}</button></div></>:cashPrompt.type==='opened'?<><h2>Caja abierta correctamente</h2><p>La apertura del turno quedó registrada. Las ventas de hoy se recopilarán desde este momento.</p><button className="primary-button full" onClick={()=>setCashPrompt(null)}>Continuar</button></>:<><h2>No se pudo verificar la caja</h2><p>{cashPrompt.message}</p><button className="secondary-button full" onClick={()=>setCashPrompt(null)}>Continuar</button></>}</div></div>}
  </>;
}
createRoot(document.getElementById('root')).render(<App/>);
