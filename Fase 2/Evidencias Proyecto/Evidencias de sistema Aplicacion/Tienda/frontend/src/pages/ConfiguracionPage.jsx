import React from 'react';
import { AlertTriangle, KeyRound, Percent, RefreshCw, Save, Settings, ShieldCheck, Trash2, UserCog, UserPlus, Users } from 'lucide-react';
import { AppLayout } from '../components/AppLayout.jsx';
import { adminService } from '../services/api.js';

const errorText = error => error?.response?.data?.detail || 'No fue posible completar la operación.';

export function ConfiguracionPage({ session, ...props }) {
  const [tab, setTab] = React.useState('usuarios');
  const [users, setUsers] = React.useState([]);
  const [roles, setRoles] = React.useState([]);
  const [discounts, setDiscounts] = React.useState([]);
  const [summary, setSummary] = React.useState({ usuarios: 0, roles: 0, descuentos: 0 });
  const [notice, setNotice] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [passwordUser, setPasswordUser] = React.useState(null);
  const [password, setPassword] = React.useState('');
  const [employeeModal, setEmployeeModal] = React.useState(false);
  const [deleteUser, setDeleteUser] = React.useState(null);
  const [newEmployee, setNewEmployee] = React.useState({ rut: '', nombre: '', clave: '' });
  const [savingEmployee, setSavingEmployee] = React.useState(false);

  const load = React.useCallback(async () => {
    if (!session?.is_admin) return;
    setLoading(true); setNotice('');
    try {
      const [u, r, d, s] = await Promise.all([adminService.users(), adminService.roles(), adminService.discounts(), adminService.summary()]);
      setUsers(u); setRoles(r); setDiscounts(d); setSummary(s);
    } catch (error) { setNotice(errorText(error)); }
    finally { setLoading(false); }
  }, [session?.is_admin]);

  React.useEffect(() => { load(); }, [load]);
  if (!session?.is_admin) return <AppLayout {...props} active="configuracion" title="Acceso restringido" eyebrow="Administración"><div className="admin-denied"><ShieldCheck/><h2>Esta sección es solo para administradores</h2><p>Tu cuenta no tiene permisos para revisar usuarios, claves ni descuentos.</p><button className="primary-button" onClick={()=>props.onNavigate('menu')}>Volver al inicio</button></div></AppLayout>;

  async function saveRole(user, id_rol) {
    try { await adminService.updateRole(user.rut, Number(id_rol)); setNotice(`Rol de ${user.nombre} actualizado.`); await load(); }
    catch (error) { setNotice(errorText(error)); }
  }
  async function savePassword(e) {
    e.preventDefault();
    try { await adminService.updatePassword(passwordUser.rut, password); setPasswordUser(null); setPassword(''); setNotice('Clave actualizada de forma segura.'); }
    catch (error) { setNotice(errorText(error)); }
  }
  async function createEmployee(e) {
    e.preventDefault(); setSavingEmployee(true);
    try { const created=await adminService.createEmployee(newEmployee); setEmployeeModal(false); setNewEmployee({rut:'',nombre:'',clave:''}); await load(); setNotice(`Empleado ${created.nombre} creado correctamente.`); }
    catch (error) { setNotice(errorText(error)); }
    finally { setSavingEmployee(false); }
  }
  async function removeEmployee() {
    if (!deleteUser) return;
    try { const removed=await adminService.deleteEmployee(deleteUser.rut); setDeleteUser(null); await load(); setNotice(`Empleado ${removed.nombre} eliminado.`); }
    catch (error) { setDeleteUser(null); setNotice(errorText(error)); }
  }
  function editDiscount(id, field, value) { setDiscounts(current => current.map(d => d.id === id ? {...d, [field]: value} : d)); }
  async function saveDiscount(item) {
    try { await adminService.saveDiscount(item.id, item.tipoDescuento, Number(item.valorDescuento)); setNotice('Descuento guardado.'); await load(); }
    catch (error) { setNotice(errorText(error)); }
  }
  async function createDiscount() {
    try { await adminService.createDiscount('Nuevo descuento', 0); setNotice('Descuento creado; ahora puedes editarlo.'); await load(); }
    catch (error) { setNotice(errorText(error)); }
  }

  return <AppLayout {...props} active="configuracion" title="Configuración" eyebrow="Centro de administración" actions={<button className="secondary-button" onClick={load}><RefreshCw/>Actualizar</button>}>
    <div className="admin-intro"><div><span><Settings/></span><div><h2>Control administrativo</h2><p>Gestiona accesos y reglas sensibles del sistema desde un solo lugar.</p></div></div><small><ShieldCheck/> Sesión de administrador · {session.rut}</small></div>
    <div className="metric-grid three"><div className="metric-card"><span className="metric-card__icon yellow"><Users/></span><div><small>Usuarios</small><strong>{summary.usuarios}</strong><em>cuentas registradas</em></div></div><div className="metric-card"><span className="metric-card__icon blue"><UserCog/></span><div><small>Roles</small><strong>{summary.roles}</strong><em>niveles de acceso</em></div></div><div className="metric-card"><span className="metric-card__icon green"><Percent/></span><div><small>Descuentos</small><strong>{summary.descuentos}</strong><em>reglas configuradas</em></div></div></div>
    {notice && <div className="admin-notice">{notice}</div>}
    <div className="admin-tabs"><button className={tab==='usuarios'?'active':''} onClick={()=>setTab('usuarios')}><Users/>Usuarios y roles</button><button className={tab==='descuentos'?'active':''} onClick={()=>setTab('descuentos')}><Percent/>Descuentos</button><button className={tab==='seguridad'?'active':''} onClick={()=>setTab('seguridad')}><ShieldCheck/>Seguridad</button></div>
    {loading ? <div className="data-panel admin-loading">Cargando configuración…</div> : tab==='usuarios' ? <div className="data-panel"><div className="data-panel__top"><div><h2>Usuarios del sistema</h2><p>Crea empleados, administra roles y establece nuevas claves.</p></div><button className="primary-button" onClick={()=>setEmployeeModal(true)}><UserPlus/>Nuevo empleado</button></div><div className="table-wrap"><table className="data-table"><thead><tr><th>Usuario</th><th>RUT</th><th>Rol</th><th>Clave</th><th>Acciones</th></tr></thead><tbody>{users.map(u=><tr key={u.rut}><td><strong>{u.nombre}</strong></td><td className="mono">{u.rut}-{u.digito_ver}</td><td><select value={u.id_rol} disabled={String(u.rut)===String(session.rut)||['admin','administrador','developer','desarrollador'].includes(String(u.rol).toLowerCase())} onChange={e=>saveRole(u,e.target.value)}>{roles.map(r=><option key={r.id} value={r.id}>{r.nombre}</option>)}</select></td><td><button className="secondary-button" onClick={()=>setPasswordUser(u)}><KeyRound/>Cambiar clave</button></td><td>{['empleado','employee'].includes(String(u.rol).toLowerCase())?<button className="employee-delete" onClick={()=>setDeleteUser(u)}><Trash2/>Eliminar</button>:<span className="protected-user"><ShieldCheck/>Protegido</span>}</td></tr>)}</tbody></table></div></div>
    : tab==='descuentos' ? <div className="data-panel"><div className="data-panel__top"><div><h2>Reglas de descuento</h2><p>El valor se expresa como porcentaje y se guarda en la base local.</p></div><button className="primary-button" onClick={createDiscount}>Nuevo descuento</button></div><div className="discount-list">{discounts.map(d=><div key={d.id}><input value={d.tipoDescuento} onChange={e=>editDiscount(d.id,'tipoDescuento',e.target.value)}/><label><input type="number" min="0" max="100" step="1" value={Math.round(Number(d.valorDescuento)*100)} onChange={e=>editDiscount(d.id,'valorDescuento',Number(e.target.value)/100)}/><span>%</span></label><button className="secondary-button" onClick={()=>saveDiscount(d)}><Save/>Guardar</button></div>)}</div></div>
    : <div className="security-grid"><div className="data-panel"><ShieldCheck/><h2>Acceso protegido</h2><p>Los endpoints de esta sección requieren una sesión administrativa válida, además del control visual.</p></div><div className="data-panel"><KeyRound/><h2>Claves no recuperables</h2><p>Solo se permite establecer una clave nueva de 8 caracteres o más. El hash almacenado nunca sale del servidor.</p></div><div className="data-panel"><UserCog/><h2>Protección de rol propio</h2><p>El administrador conectado no puede quitarse su propio rol durante la sesión, evitando bloquear el acceso por error.</p></div></div>}
    {employeeModal && <div className="modal-backdrop"><form className="client-modal employee-modal" onSubmit={createEmployee}><div className="modal-head"><div><span><UserPlus/></span><div><h2>Nuevo empleado</h2><p>La cuenta se creará únicamente con rol empleado.</p></div></div><button type="button" onClick={()=>setEmployeeModal(false)}>×</button></div><div className="form-grid"><label>Nombre completo<input autoFocus maxLength="60" value={newEmployee.nombre} onChange={e=>setNewEmployee(v=>({...v,nombre:e.target.value}))} required/></label><label>RUT con dígito verificador<input placeholder="12345678-9" maxLength="15" value={newEmployee.rut} onChange={e=>setNewEmployee(v=>({...v,rut:e.target.value}))} required/></label><label className="wide">Clave inicial<input type="password" minLength="8" maxLength="128" value={newEmployee.clave} onChange={e=>setNewEmployee(v=>({...v,clave:e.target.value}))} required/><small>Mínimo 8 caracteres; nunca se mostrará después de guardar.</small></label></div><div className="modal-actions"><button type="button" className="secondary-button" onClick={()=>setEmployeeModal(false)}>Cancelar</button><button className="primary-button" disabled={savingEmployee}>{savingEmployee?'Creando…':'Crear empleado'}</button></div></form></div>}
    {deleteUser && <div className="modal-backdrop"><div className="confirm-dialog"><span className="confirm-dialog__icon danger"><AlertTriangle/></span><h2>¿Eliminar empleado?</h2><p>Se eliminará la cuenta de <strong>{deleteUser.nombre}</strong> ({deleteUser.rut}-{deleteUser.digito_ver}). Esta acción no puede deshacerse.</p><div className="protected-note"><ShieldCheck/>Las cuentas admin y developer nunca pueden eliminarse desde esta función.</div><div className="modal-actions"><button className="secondary-button" onClick={()=>setDeleteUser(null)}>Cancelar</button><button className="danger-button" onClick={removeEmployee}>Sí, eliminar empleado</button></div></div></div>}
    {passwordUser && <div className="modal-backdrop"><form className="brand-modal" onSubmit={savePassword}><div className="modal-head"><div><span><KeyRound/></span><div><h2>Nueva clave</h2><p>{passwordUser.nombre} · {passwordUser.rut}</p></div></div><button type="button" onClick={()=>setPasswordUser(null)}>×</button></div><label>Clave temporal<input autoFocus type="password" minLength="8" value={password} onChange={e=>setPassword(e.target.value)} required/><small>Mínimo 8 caracteres</small></label><div className="modal-actions"><button type="button" className="secondary-button" onClick={()=>setPasswordUser(null)}>Cancelar</button><button className="primary-button">Actualizar clave</button></div></form></div>}
  </AppLayout>;
}
