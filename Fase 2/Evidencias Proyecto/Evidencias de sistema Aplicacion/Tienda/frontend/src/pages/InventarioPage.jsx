import React from "react";
import {
  AlertTriangle,
  Archive,
  ArchiveRestore,
  Boxes,
  ChevronDown,
  ChevronRight,
  PackageCheck,
  Search,
  Tags,
  X,
} from "lucide-react";
import { AppLayout } from "../components/AppLayout.jsx";
import { brandService, inventoryService } from "../services/api.js";

const money = (value) =>
  new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

export function InventarioPage({ session, ...props }) {
  const [expandedProducts, setExpandedProducts] = React.useState(new Set());
  const [search, setSearch] = React.useState("");
  const [brand, setBrand] = React.useState("");
  const [brands, setBrands] = React.useState([]);
  const [rows, setRows] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [feedback, setFeedback] = React.useState("");
  const [includeDisabled, setIncludeDisabled] = React.useState(false);
  const [pendingProduct, setPendingProduct] = React.useState(null);
  const [statusError, setStatusError] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [summary, setSummary] = React.useState({
    prendas_registradas: 0,
    unidades_disponibles: 0,
    marcas: 0,
    stock_bajo: 0,
    umbral_stock_bajo: 5,
  });
  const isAdmin = Boolean(session?.is_admin);

  const products = React.useMemo(() => {
    const grouped = new Map();

    for (const row of rows) {
      let product = grouped.get(row.id_producto);

      if (!product) {
        product = { ...row, variantes: [], stockTotal: 0 };
        grouped.set(row.id_producto, product);
      }

      product.variantes.push(row);
      product.stockTotal += Number(row["Total Stock"] || 0);
    }

    return [...grouped.values()];
  }, [rows]);

  function toggleProduct(id) {
    setExpandedProducts((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  React.useEffect(() => {
    Promise.all([inventoryService.summary(), brandService.list()])
      .then(([stats, list]) => {
        setSummary(stats);
        setBrands(list);
      })
      .catch(() => setError("No pudimos cargar el resumen del inventario."));
  }, []);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(true);
      const request =
        isAdmin && includeDisabled
          ? inventoryService.listAdmin(search, brand)
          : inventoryService.list(search, brand);
      request
        .then((result) => {
          setRows(result);
          setError("");
        })
        .catch(requestError =>
          setError(requestError?.response?.data?.detail || "No pudimos conectar con el inventario."),
        )
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [search, brand, isAdmin, includeDisabled]);

  async function changeStatus() {
    if (!pendingProduct) return;
    const active = !pendingProduct.activo;
    setSaving(true);
    setStatusError("");
    setFeedback("");
    try {
      await inventoryService.setActive(pendingProduct.id_producto, active);
      setPendingProduct(null);
      setFeedback(
        active
          ? `${pendingProduct.nombre} fue reactivado.`
          : `${pendingProduct.nombre} fue deshabilitado. Su stock e historial se conservaron.`,
      );
      setIncludeDisabled(!active);
      try {
        setSummary(await inventoryService.summary());
      } catch {
        setFeedback((message) => `${message} El resumen no pudo actualizarse.`);
      }
    } catch (requestError) {
      setStatusError(
        requestError?.response?.data?.detail || "No fue posible actualizar el producto.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppLayout {...props} session={session} active="inventario" title="Inventario" eyebrow="Control de existencias">
      <section className="metric-grid">
        <Metric icon={<Boxes />} tone="yellow" label="Prendas registradas" value={summary.prendas_registradas} sub="productos diferentes" />
        <Metric icon={<PackageCheck />} tone="green" label="Unidades disponibles" value={summary.unidades_disponibles} sub="stock total" />
        <Metric icon={<Tags />} tone="blue" label="Marcas" value={summary.marcas} sub="registradas" />
        <Metric icon={<AlertTriangle />} tone="red" label="Stock bajo" value={summary.stock_bajo} sub={`hasta ${summary.umbral_stock_bajo} unidades`} />
      </section>

      <section className="data-panel">
        <div className="data-panel__top">
          <div>
            <h2>Listado de prendas</h2>
            <p>Consulta stock, precio y marca de cada producto.</p>
          </div>
        </div>
        <div className="toolbar">
          <label className="search-field">
            <Search size={19} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nombre o código de barra..."
            />
          </label>
          <select value={brand} onChange={event => setBrand(event.target.value)}>
            <option value="">Todas las marcas</option>
            {brands.map(item => <option value={item.nombre} key={item.id}>{item.nombre}</option>)}
          </select>
          {isAdmin && (
            <select
              aria-label="Filtrar productos deshabilitados"
              value={includeDisabled ? "all" : "active"}
              onChange={event => setIncludeDisabled(event.target.value === "all")}
            >
              <option value="active">Solo activos</option>
              <option value="all">Todos los productos</option>
            </select>
          )}
        </div>

        {error ? (
          <div className="empty-state">
            <AlertTriangle />
            <strong>{error}</strong>
            <span>Comprueba que el servidor local esté iniciado.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Prenda</th><th>Código</th><th>Marca</th><th>Precio</th>
                  <th>Stock</th><th>Estado</th>{isAdmin && <th>Acción</th>}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={isAdmin ? 7 : 6} className="table-message">Cargando inventario…</td></tr>
                ) : rows.length ? (
                  products.map((product) => {
                    const expanded = expandedProducts.has(product.id_producto);
                    const stock = product.stockTotal;
                    const active = product.activo !== false;

                    return (
                      <React.Fragment key={product.id_producto}>
                        <tr>
                          <td>
                            <div className="product-cell">
                              <button
                                type="button"
                                className="inventory-expand"
                                aria-expanded={expanded}
                                aria-label={`${expanded ? "Ocultar" : "Mostrar"} variantes de ${product.Prenda}`}
                                onClick={() =>
                                  toggleProduct(product.id_producto)
                                }
                              >
                                {expanded ? (
                                  <ChevronDown size={16} />
                                ) : (
                                  <ChevronRight size={16} />
                                )}
                              </button>
                              <span>{String(product.Prenda || "P")[0]}</span>
                              <strong>{product.Prenda || "Sin nombre"}</strong>
                            </div>
                          </td>
                          <td className="mono">{product.codigo_base || "—"}</td>
                          <td>
                            <span className="category-pill">
                              {product.Marca || "Sin marca"}
                            </span>
                          </td>
                          <td>
                            <strong>{money(product.Precio)}</strong>
                          </td>
                          <td>{stock} un.</td>
                          <td>
                            <span
                              className={`status-pill ${!active || stock === 0 ? "out" : stock <= 5 ? "low" : "ok"}`}
                            >
                              {!active
                                ? "Deshabilitado"
                                : stock === 0
                                  ? "Agotado"
                                  : stock <= 5
                                    ? "Stock bajo"
                                    : "Disponible"}
                            </span>
                          </td>
                          {isAdmin && (
                            <td>
                              <button
                                type="button"
                                className="secondary-button"
                                onClick={() => {
                                  setStatusError("");
                                  setPendingProduct({
                                    id_producto: product.id_producto,
                                    nombre: product.Prenda || "Este producto",
                                    activo: active,
                                  });
                                }}
                              >
                                {active ? (
                                  <Archive size={16} />
                                ) : (
                                  <ArchiveRestore size={16} />
                                )}
                                {active ? "Deshabilitar" : "Reactivar"}
                              </button>
                            </td>
                          )}
                        </tr>

                        {expanded &&
                          product.variantes.map((variant) => {
                            const variantStock = Number(
                              variant["Total Stock"] || 0,
                            );

                            return (
                              <tr
                                className="inventory-variant-row"
                                key={variant.id}
                              >
                                <td className="inventory-variant-name">
                                  {variant.talla || "Sin talla"}
                                  {variant.color ? ` · ${variant.color}` : ""}
                                </td>
                                <td className="mono">
                                  {variant.barcode || "—"}
                                </td>
                                <td>{product.Marca || "Sin marca"}</td>
                                <td>{money(product.Precio)}</td>
                                <td>{variantStock} un.</td>
                                <td>
                                  <span
                                    className={`status-pill ${!active || variantStock === 0 ? "out" : variantStock <= 5 ? "low" : "ok"}`}
                                  >
                                    {!active
                                      ? "Deshabilitado"
                                      : variantStock === 0
                                        ? "Agotado"
                                        : variantStock <= 5
                                          ? "Stock bajo"
                                          : "Disponible"}
                                  </span>
                                </td>
                                {isAdmin && <td />}
                              </tr>
                            );
                          })}
                      </React.Fragment>
                    );
                  })
                ) : (
                  <tr><td colSpan={isAdmin ? 7 : 6} className="table-message">No encontramos prendas con esos filtros.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <footer className="panel-footer">
          Mostrando <strong>{products.length}</strong> prendas
        </footer>
        {feedback && <p role="status">{feedback}</p>}
      </section>

      {pendingProduct && (
        <div className={`modal-backdrop ${props.dark ? "theme-dark" : ""}`}>
          <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="inventory-status-title">
            <button className="dialog-close" type="button" onClick={() => setPendingProduct(null)} aria-label="Cerrar">
              <X />
            </button>
            <span className="confirm-dialog__icon">
              {pendingProduct.activo ? <Archive /> : <ArchiveRestore />}
            </span>
            <h2 id="inventory-status-title">
              {pendingProduct.activo ? "¿Deshabilitar producto?" : "¿Reactivar producto?"}
            </h2>
            <p>
              <strong>{pendingProduct.nombre}</strong>
              {pendingProduct.activo
                ? " dejará de estar disponible para nuevas ventas. Se conservarán el stock y el historial."
                : " volverá a estar disponible en inventario y ventas."}
            </p>
            {statusError && <p className="login-error" role="alert">{statusError}</p>}
            <div className="modal-actions">
              <button className="secondary-button" type="button" disabled={saving} onClick={() => setPendingProduct(null)}>
                Cancelar
              </button>
              <button className="primary-button" type="button" disabled={saving} onClick={changeStatus}>
                {saving ? "Guardando…" : pendingProduct.activo ? "Sí, deshabilitar" : "Sí, reactivar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

function Metric({ icon, tone, label, value, sub }) {
  return (
    <article className="metric-card">
      <span className={`metric-card__icon ${tone}`}>{icon}</span>
      <div><small>{label}</small><strong>{value}</strong><em>{sub}</em></div>
    </article>
  );
}
