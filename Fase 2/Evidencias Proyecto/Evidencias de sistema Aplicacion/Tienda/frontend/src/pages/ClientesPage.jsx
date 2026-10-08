import React from "react";
import {
  ArrowLeft,
  BriefcaseBusiness,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  CreditCard,
  MapPin,
  Phone,
  Plus,
  Search,
  UserPlus,
  UsersRound,
  X,
} from "lucide-react";
import { AppLayout } from "../components/AppLayout.jsx";
import { clientService } from "../services/api.js";
const blank = {
    nombre: "",
    rut: "",
    celular: "",
    direccion: "",
    actividad_economica: "",
    descripcion: "",
    fono: "",
  },
  money = (v) =>
    new Intl.NumberFormat("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    }).format(Number(v || 0));
export function ClientesPage(props) {
  const [clients, setClients] = React.useState([]),
    [search, setSearch] = React.useState(""),
    [modal, setModal] = React.useState(false),
    [selected, setSelected] = React.useState(null),
    [credit, setCredit] = React.useState([]),
    [expandedCredit, setExpandedCredit] = React.useState(null),
    [creditDetails, setCreditDetails] = React.useState({}),
    [detailLoading, setDetailLoading] = React.useState(null),
    [detailError, setDetailError] = React.useState(""),
    [form, setForm] = React.useState(blank),
    [msg, setMsg] = React.useState(""),
    [summary, setSummary] = React.useState({
      total_clientas: 0,
      creditos_activos: 0,
      saldo_pendiente: 0,
    });
  React.useEffect(() => {
    clientService
      .summary()
      .then(setSummary)
      .catch(() => {});
  }, []);
  React.useEffect(() => {
    const t = setTimeout(
      () =>
        clientService
          .list(search)
          .then(setClients)
          .catch(() => setClients([])),
      250,
    );
    return () => clearTimeout(t);
  }, [search]);
  async function open(c) {
    setSelected(c);
    setExpandedCredit(null);
    setCreditDetails({});
    try {
      setCredit(await clientService.credit(c.rut));
    } catch {
      setCredit([]);
    }
  }
  async function toggleCreditDetail(id) {
    if (expandedCredit === id) {
      setExpandedCredit(null);
      return;
    }
    setExpandedCredit(id);
    setDetailError("");
    if (creditDetails[id]) return;
    setDetailLoading(id);
    try {
      const detail = await clientService.creditDetail(selected.rut, id);
      setCreditDetails((current) => ({ ...current, [id]: detail }));
    } catch (err) {
      setDetailError(
        err.response?.data?.detail || "No fue posible cargar el detalle.",
      );
    } finally {
      setDetailLoading(null);
    }
  }
  async function add(e) {
    e.preventDefault();
    try {
      const c = await clientService.create(form);
      setClients((x) => [c, ...x]);
      setMsg("");
      setModal(false);
      setForm(blank);
    } catch (err) {
      setMsg(
        err.response?.data?.detail || "No fue posible guardar la clienta.",
      );
      setModal(false);
    }
  }
  const debt = credit.reduce((s, x) => s + Number(x.saldo_pendiente ?? 0), 0);
  const pendingInstallments = credit.reduce(
    (s, x) => s + Number(x.cuotas_por_pagar || 0),
    0,
  );
  return (
    <AppLayout
      {...props}
      active="clientes"
      title="Clientas"
      eyebrow="Gestión de clientas"
      actions={
        <button className="primary-button" onClick={() => setModal(true)}>
          <Plus /> Nueva clienta
        </button>
      }
    >
      {selected ? (
        <>
          <button className="back-button" onClick={() => setSelected(null)}>
            <ArrowLeft /> Volver a clientas
          </button>
          <div className="client-profile">
            <div className="client-avatar">{initials(selected.nombre)}</div>
            <div>
              <span>Ficha de clienta</span>
              <h2>{selected.nombre || "Sin nombre"}</h2>
              <p>RUT {selected.rut || "—"}</p>
            </div>
            <span className="status-pill ok">Activa</span>
          </div>
          <div className="client-detail-grid">
            <section className="data-panel client-info">
              <div className="data-panel__top">
                <div>
                  <h2>Información de contacto</h2>
                  <p>Datos personales y comerciales.</p>
                </div>
              </div>
              <Info icon={<Phone />} label="Celular" value={selected.celular} />
              <Info
                icon={<Phone />}
                label="Fono alternativo"
                value={selected.fono}
              />
              <Info
                icon={<MapPin />}
                label="Dirección"
                value={selected.direccion}
              />
              <Info
                icon={<BriefcaseBusiness />}
                label="Actividad económica"
                value={selected.actividad_economica}
              />
              <div className="client-description">
                <small>Descripción</small>
                <p>{selected.descripcion || "Sin descripción registrada."}</p>
              </div>
            </section>
            <aside className="credit-summary">
              <small>Deuda pendiente</small>
              <strong>{money(debt)}</strong>
              <p>{pendingInstallments} cuotas por pagar</p>
              <CircleDollarSign />
            </aside>
          </div>
          <section className="data-panel credit-sheet">
            <div className="data-panel__top">
              <div>
                <h2>Hoja de crédito</h2>
                <p>Historial de cuotas y compromisos de pago.</p>
              </div>
              <span className="category-pill">{credit.length} registros</span>
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Próximo vencimiento</th>
                    <th>Cuotas pagadas / total</th>
                    <th>Precio cuota</th>
                    <th>Pie</th>
                    <th>Estado</th>
                    <th>Compra</th>
                  </tr>
                </thead>
                <tbody>
                  {credit.length ? (
                    credit.map((x, i) => (
                      <React.Fragment key={x.id ?? i}>
                        <tr>
                          <td>
                            <span className="date-cell">
                              <CalendarDays />
                              {date(x.proximo_vencimiento)}
                            </span>
                          </td>
                          <td>
                            {Math.max(
                              Number(x.cantidad_cuotas || 0) -
                                Number(x.cuotas_por_pagar || 0),
                              0,
                            )}{" "}
                            / {Number(x.cantidad_cuotas || 0)}
                          </td>
                          <td>
                            <strong>
                              {money(
                                Number(x.saldo_original ?? 0) /
                                  Math.max(Number(x.cantidad_cuotas || 0), 1),
                              )}
                            </strong>
                          </td>
                          <td>{money(x.pie)}</td>
                          <td>
                            <span
                              className={`status-pill ${Number(x.estado) === 3 ? "ok" : Number(x.estado) === 2 ? "out" : "low"}`}
                            >
                              {x.estado_nombre || "Pendiente"}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="secondary-button credit-detail-toggle"
                              onClick={() => toggleCreditDetail(x.id)}
                              aria-expanded={expandedCredit === x.id}
                            >
                              {expandedCredit === x.id ? "Ocultar" : "Ver compra"}
                              <ChevronDown />
                            </button>
                          </td>
                        </tr>
                        {expandedCredit === x.id && (
                          <tr className="credit-detail-row">
                            <td colSpan="6">
                              <CreditDetail
                                data={creditDetails[x.id]}
                                loading={detailLoading === x.id}
                                error={detailError}
                              />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6">
                        <div className="empty-state compact">
                          <CreditCard />
                          <strong>Sin movimientos de crédito</strong>
                          <span>
                            Esta clienta aún no tiene cuotas registradas.
                          </span>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : (
        <>
          <section className="metric-grid three">
            <Metric
              icon={<UsersRound />}
              label="Clientas registradas"
              value={summary.total_clientas || clients.length}
              sub="en la cartera"
            />
            <Metric
              icon={<CreditCard />}
              label="Con crédito activo"
              value={summary.creditos_activos}
              sub="hojas pendientes o atrasadas"
            />
            <Metric
              icon={<CircleDollarSign />}
              label="Saldo pendiente"
              value={money(summary.saldo_pendiente)}
              sub="según cuotas valorizadas"
            />
          </section>
          <section className="data-panel">
            <div className="data-panel__top">
              <div>
                <h2>Listado de clientas</h2>
                <p>Consulta sus datos y accede a la hoja de crédito.</p>
              </div>
            </div>
            <div className="toolbar">
              <label className="search-field">
                <Search />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar por nombre, RUT o teléfono..."
                />
              </label>
            </div>
            {msg && <div className="inline-notice">{msg}</div>}
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Clienta</th>
                    <th>RUT</th>
                    <th>Celular</th>
                    <th>Dirección</th>
                    <th>Actividad económica</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {clients.length ? (
                    clients.map((c, i) => (
                      <tr
                        className="clickable-row"
                        key={c.rut || i}
                        onClick={() => open(c)}
                      >
                        <td>
                          <div className="product-cell">
                            <span>{initials(c.nombre)}</span>
                            <strong>{c.nombre || "Sin nombre"}</strong>
                          </div>
                        </td>
                        <td className="mono">{c.rut || "—"}</td>
                        <td>{c.celular || c.fono || "—"}</td>
                        <td>{c.direccion || "—"}</td>
                        <td>{c.actividad_economica || "—"}</td>
                        <td>
                          <ChevronRight />
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6">
                        <div className="empty-state">
                          <UsersRound />
                          <strong>No hay clientas para mostrar</strong>
                          <span>
                            Agrega una nueva clienta o inicia el servicio local.
                          </span>
                          <button
                            className="primary-button"
                            onClick={() => setModal(true)}
                          >
                            <UserPlus /> Agregar clienta
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      {modal && (
        <div className="modal-backdrop" onMouseDown={() => setModal(false)}>
          <form
            className="client-modal"
            onSubmit={add}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <span>
                  <UserPlus />
                </span>
                <div>
                  <h2>Nueva clienta</h2>
                  <p>Ingresa sus datos personales y comerciales.</p>
                </div>
              </div>
              <button type="button" onClick={() => setModal(false)}>
                <X />
              </button>
            </div>
            <div className="form-grid">
              <Field
                label="Nombre completo"
                value={form.nombre}
                set={(v) => setForm((f) => ({ ...f, nombre: v }))}
                required
              />
              <Field
                label="RUT"
                value={form.rut}
                set={(v) => setForm((f) => ({ ...f, rut: v }))}
                placeholder="12.345.678-9"
                required
              />
              <Field
                label="Celular"
                value={form.celular}
                set={(v) => setForm((f) => ({ ...f, celular: v }))}
                type="tel"
                maxLength="11"
                required
              />
              <Field
                label="Fono alternativo"
                value={form.fono}
                set={(v) => setForm((f) => ({ ...f, fono: v }))}
                type="tel"
                maxLength="11"
              />
              <Field
                label="Dirección"
                value={form.direccion}
                set={(v) => setForm((f) => ({ ...f, direccion: v }))}
                maxLength="50"
                wide
              />
              <Field
                label="Actividad económica"
                value={form.actividad_economica}
                set={(v) => setForm((f) => ({ ...f, actividad_economica: v }))}
                maxLength="100"
                wide
              />
              <label className="wide">
                Descripción
                <textarea
                  value={form.descripcion}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, descripcion: e.target.value }))
                  }
                  maxLength="250"
                  placeholder="Información adicional..."
                />
                <small>{form.descripcion.length}/250</small>
              </label>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setModal(false)}
              >
                Cancelar
              </button>
              <button className="primary-button">Guardar clienta</button>
            </div>
          </form>
        </div>
      )}
    </AppLayout>
  );
}
function CreditDetail({ data, loading, error }) {
  if (loading) return <div className="credit-detail-state">Cargando detalle de compra...</div>;
  if (error) return <div className="credit-detail-state error">{error}</div>;
  if (!data) return null;

  const installments = data.cuotas || [];
  const completedCount = installments.filter((item) => Number(item.pagada) === 1).length;
  const paidAmount = installments.reduce(
    (total, item) => total + Number(item.monto_pagado || 0),
    0,
  );
  const financedAmount = installments.reduce(
    (total, item) => total + Number(item.monto_cuota || 0),
    0,
  );

  return (
    <div className="credit-detail">
      <div className="credit-detail__top">
        <div>
          <h3>Compra #{data.id_venta}</h3>
          <span>Realizada el {date(data.fecha_venta)}</span>
        </div>
        <strong>{completedCount} de {installments.length} cuotas pagadas</strong>
      </div>
      <div className="credit-detail__facts">
        <div><small>Total compra</small><strong>{money(data.total_venta)}</strong></div>
        <div><small>Pie pagado</small><strong>{money(data.pie)}</strong></div>
        <div><small>Saldo financiado</small><strong>{money(financedAmount)}</strong></div>
        <div><small>Abonado a cuotas</small><strong>{money(paidAmount)}</strong></div>
      </div>

      <section className="credit-detail__section">
        <h4>Prendas de esta compra</h4>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Prenda</th><th>SKU / variante</th><th>Cantidad</th><th>Precio unitario</th><th>Subtotal</th></tr>
            </thead>
            <tbody>
              {data.productos?.length ? data.productos.map((item, index) => (
                <tr key={`${item.sku}-${index}`}>
                  <td><strong>{item.nombre}</strong></td>
                  <td>{[item.sku, item.talla && `Talla ${item.talla}`, item.color].filter(Boolean).join(" · ") || item.codigo_base}</td>
                  <td>{item.cantidad}</td>
                  <td>{money(item.precio_unitario)}</td>
                  <td><strong>{money(item.subtotal)}</strong></td>
                </tr>
              )) : (
                <tr><td colSpan="5">No hay prendas registradas para esta venta.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="credit-detail__section">
        <h4>Calendario de cuotas</h4>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Cuota</th><th>Vencimiento</th><th>Valor cuota</th><th>Abonado</th><th>Restante</th><th>Pagada el</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {installments.map((item) => {
                const paid = Number(item.monto_pagado || 0);
                const remaining = Number(item.saldo_pendiente || 0);
                const status = remaining <= 0 ? "Pagada" : paid > 0 ? "Abono parcial" : "Pendiente";
                const statusClass = remaining <= 0 ? "ok" : paid > 0 ? "low" : "out";
                return (
                  <tr key={item.numero_cuota}>
                    <td>{item.numero_cuota} / {installments.length}</td>
                    <td>{date(item.fecha_vencimiento)}</td>
                    <td>{money(item.monto_cuota)}</td>
                    <td>{money(paid)}</td>
                    <td>{money(remaining)}</td>
                    <td>{date(item.fecha_pago)}</td>
                    <td><span className={`status-pill ${statusClass}`}>{status}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Field({ label, value, set, wide, ...rest }) {
  return (
    <label className={wide ? "wide" : ""}>
      {label}
      <input value={value} onChange={(e) => set(e.target.value)} {...rest} />
    </label>
  );
}
function Metric({ icon, label, value, sub }) {
  return (
    <article className="metric-card">
      <span className="metric-card__icon yellow">{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        <em>{sub}</em>
      </div>
    </article>
  );
}
function Info({ icon, label, value }) {
  return (
    <div className="info-row">
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value || "No registrado"}</strong>
      </div>
    </div>
  );
}
function initials(n = "") {
  return (
    n
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((x) => x[0])
      .join("")
      .toUpperCase() || "CL"
  );
}
function date(value) {
  if (!value) return "—";
  const text = String(value);
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(text)
    ? `${text}T00:00:00`
    : text.replace(" ", "T");
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime())
    ? "—"
    : new Intl.DateTimeFormat("es-CL").format(parsed);
}
