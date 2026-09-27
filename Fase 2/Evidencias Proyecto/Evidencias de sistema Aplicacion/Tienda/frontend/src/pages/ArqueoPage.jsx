import React from 'react';
import { Banknote, CheckCircle2, CreditCard, Landmark, ReceiptText, Wallet } from 'lucide-react';
import { AppLayout } from '../components/AppLayout.jsx';
import { cashService } from '../services/api.js';

const money = value => new Intl.NumberFormat('es-CL', {style:'currency', currency:'CLP', maximumFractionDigits:0}).format(Number(value || 0));
const localDate = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };

export function ArqueoPage(props) {
  const today = localDate();
  const [data, setData] = React.useState(null);
  const [cash, setCash] = React.useState('');
  const [expenses, setExpenses] = React.useState('0');
  const [msg, setMsg] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const load = React.useCallback(async () => { setLoading(true); try { const result=await cashService.get(today); setData(result); setExpenses(String(result.gastos_turno || 0)); setMsg(result.existe===false ? result.aviso : ''); } catch (e) { setData(null); setMsg(e?.response?.data?.detail || 'No fue posible consultar la caja.'); } finally { setLoading(false); } }, [today]);
  React.useEffect(() => { load(); }, [load]);
  const missing = data?.existe === false;
  const sales = Number(data?.total_ventas || 0);
  const expected = Number(data?.total_efectivo || 0) - Number(expenses || 0);
  const difference = data?.cerrada ? Number(data.diferencia || 0) : Number(cash || 0) - expected;
  async function open() {
    if (!window.confirm('¿Deseas abrir la caja de hoy y comenzar el turno?')) return;
    try { await cashService.open(today); setMsg('Caja abierta correctamente.'); await load(); }
    catch (error) { setMsg(error?.response?.data?.detail || 'No se pudo abrir la caja.'); }
  }
  async function close() {
    if (!window.confirm('¿Confirmas el cierre de caja? Después de cerrar no podrás modificar este arqueo.')) return;
    try { const result=await cashService.close({fecha:today, efectivo_contado:Number(cash||0), gastos_turno:Number(expenses||0)}); setData(result); setMsg('Caja cerrada correctamente.'); }
    catch (error) { setMsg(error?.response?.data?.detail || 'No se pudo cerrar la caja.'); }
  }
  return <AppLayout {...props} active="arqueo" title="Cierre de caja" eyebrow="Resumen del turno">
    <div className="closing-banner"><div><span>Turno actual</span><h2>Resumen de hoy</h2><p>{new Intl.DateTimeFormat('es-CL',{dateStyle:'full'}).format(new Date())}</p></div><div><small>Estado de caja</small><strong><i className={data?.cerrada?'closed':''}/> {data?.cerrada?'Caja cerrada':data?.abierta?'Caja abierta':'Sin apertura'}</strong></div></div>
    {missing && <div className="cash-opening-notice"><div><strong>{data.aviso}</strong><span>Abre la caja para comenzar a recopilar las ventas del turno.</span></div><button className="primary-button" onClick={open}><CheckCircle2/> Abrir caja ahora</button></div>}
    <section className="metric-grid three"><Metric icon={<ReceiptText/>} label="Ventas realizadas" value={loading?'…':data?.ventas_cantidad || 0} sub="durante el turno"/><Metric icon={<Wallet/>} label="Total vendido" value={money(sales)} sub="venta bruta"/><Metric icon={<Banknote/>} label="Efectivo esperado" value={money(expected)} sub="menos gastos"/></section>
    <div className="cash-grid"><section className="data-panel"><div className="data-panel__top"><div><h2>Ventas por medio de pago</h2><p>Recopilación real desde la apertura del turno.</p></div></div><div className="payment-summary"><Payment icon={<Banknote/>} label="Efectivo" value={data?.total_efectivo}/><Payment icon={<Landmark/>} label="Débito" value={data?.total_debito}/><Payment icon={<CreditCard/>} label="Crédito bancario" value={data?.total_credito}/><Payment icon={<Wallet/>} label="Crédito Girasol" value={data?.total_credito_girasol}/><Payment icon={<Landmark/>} label="Transferencia" value={data?.total_transferencia}/><Payment icon={<Wallet/>} label="Otros" value={data?.total_otro}/></div></section>
      <aside className="checkout close-box"><h2>{missing?'Apertura de caja':data?.cerrada?'Arqueo final':'Realizar arqueo'}</h2><label>Monto contado en caja<input type="number" min="0" disabled={!data?.abierta} value={data?.cerrada?data.efectivo_contado ?? '':cash} onChange={e=>setCash(e.target.value)} placeholder="$ 0"/></label><label>Gastos del turno<input type="number" min="0" disabled={!data?.abierta} value={expenses} onChange={e=>setExpenses(e.target.value)}/></label><div className={`difference ${difference===0?'even':difference>0?'up':'down'}`}><span>Diferencia</span><strong>{money(difference)}</strong></div>{!missing && data ? <button className="primary-button full" disabled={!data?.abierta} onClick={close}><CheckCircle2/> {data?.cerrada?'Caja cerrada':'Cerrar caja'}</button> : <button className="primary-button full" onClick={open}><CheckCircle2/> Abrir caja de hoy</button>}{msg&&<p className="feedback center">{msg}</p>}</aside>
    </div>
  </AppLayout>;
}
function Metric({icon,label,value,sub}) { return <article className="metric-card"><span className="metric-card__icon yellow">{icon}</span><div><small>{label}</small><strong>{value}</strong><em>{sub}</em></div></article>; }
function Payment({icon,label,value}) { return <div><span className="pay-icon">{icon}</span><p><strong>{label}</strong><small>Ventas procesadas</small></p><b>{money(value)}</b></div>; }
