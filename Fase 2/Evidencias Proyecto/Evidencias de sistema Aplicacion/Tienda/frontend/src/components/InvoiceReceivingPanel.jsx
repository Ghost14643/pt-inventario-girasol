import React from 'react';
import {
  Check,
  Eye,
  FileText,
  LoaderCircle,
  Plus,
  RefreshCw,
  Save,
  ScanLine,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { inventoryService, invoiceService } from '../services/api.js';

const pendingStatus = 'PENDIENTE_APROBACION';
const processingStatus = 'EN_PROCESO_APROBACION';
const extractionLabels = {
  XML_DTE: 'XML del DTE',
  PDF_TEXTO: 'Texto del PDF',
  TESSERACT: 'OCR Tesseract',
  REVISION_MANUAL: 'Revisión manual',
};

function errorMessage(error, fallback) {
  return error?.response?.data?.detail || fallback;
}

function toEditableItems(items = []) {
  return items.map((item) => ({
    ...item,
    cantidad: String(item.cantidad),
    precio_costo: item.precio_costo == null ? '' : String(item.precio_costo),
    precio_venta: item.precio_venta == null ? '' : String(item.precio_venta),
  }));
}

export function InvoiceReceivingPanel() {
  const [file, setFile] = React.useState(null);
  const [invoices, setInvoices] = React.useState([]);
  const [catalogue, setCatalogue] = React.useState([]);
  const [selectedId, setSelectedId] = React.useState('');
  const [items, setItems] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState('');
  const [error, setError] = React.useState('');
  const [message, setMessage] = React.useState('');
  const [preview, setPreview] = React.useState(null);
  const [margin, setMargin] = React.useState('');
  const fileInput = React.useRef(null);
  const selectedInvoice = invoices.find((invoice) => invoice.id === selectedId);
  const canEdit = selectedInvoice?.estado === pendingStatus;

  const loadPending = React.useCallback(async () => {
    const pending = await invoiceService.pending();
    setInvoices(pending);
    setSelectedId((current) =>
      pending.some((invoice) => invoice.id === current) ? current : '',
    );
    return pending;
  }, []);

  React.useEffect(() => {
    loadPending()
      .catch((cause) => setError(errorMessage(cause, 'No se pudieron cargar las facturas pendientes.')))
      .finally(() => setLoading(false));
  }, [loadPending]);

  React.useEffect(() => {
    inventoryService.list()
      .then(setCatalogue)
      .catch((cause) => setError(errorMessage(cause, 'No se pudo cargar el catálogo para vincular los SKU.')));
  }, []);

  React.useEffect(() => {
    setItems(toEditableItems(selectedInvoice?.items));
  }, [
    selectedInvoice?.id,
    selectedInvoice?.fecha_actualizacion,
    selectedInvoice?.estado,
  ]);

  React.useEffect(() => {
    if (!preview) return undefined;
    return () => URL.revokeObjectURL(preview.url);
  }, [preview]);

  async function refresh() {
    setError('');
    try {
      await loadPending();
    } catch (cause) {
      setError(errorMessage(cause, 'No se pudieron cargar las facturas pendientes.'));
    }
  }

  async function scanInvoice() {
    if (!file) {
      setError('Selecciona un XML, PDF o imagen primero.');
      return;
    }
    setBusy('scan');
    setError('');
    setMessage('');
    try {
      const invoice = await invoiceService.scan(file);
      setInvoices((current) => [invoice, ...current.filter((item) => item.id !== invoice.id)]);
      setSelectedId(invoice.id);
      setFile(null);
      if (fileInput.current) fileInput.current.value = '';
      setMessage('Factura procesada. Revisa los productos, asígnalos al catálogo y confirma los precios antes de aprobar.');
    } catch (cause) {
      setError(errorMessage(cause, 'No se pudo escanear la factura.'));
    } finally {
      setBusy('');
    }
  }

  function changeItem(index, key, value) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [key]: value } : item,
      ),
    );
  }

  function selectInventorySku(index, value) {
    const product = catalogue.find((row) => String(row.barcode).trim() === value.trim());
    setItems((current) => current.map((item, itemIndex) => {
      if (itemIndex !== index) return item;
      if (!product) return { ...item, sku: value };
      return {
        ...item,
        sku: value,
        nombre: product.Prenda || item.nombre,
        precio_venta: String(Number(product.Precio || 0)),
      };
    }));
  }

  function validatedItems() {
    if (!items.length) {
      setError('Agrega al menos un producto a la factura.');
      return null;
    }
    const cleanItems = items.map((item) => ({
      sku: item.sku.trim(),
      codigo_proveedor: item.codigo_proveedor.trim(),
      nombre: item.nombre.trim(),
      cantidad: Number(item.cantidad),
      precio_costo: item.precio_costo === '' ? null : Number(item.precio_costo),
      precio_venta: item.precio_venta === '' ? null : Number(item.precio_venta),
    }));
    if (cleanItems.some((item) =>
      !item.sku
      || !Number.isInteger(item.cantidad)
      || item.cantidad < 1
      || item.precio_venta == null
      || !Number.isFinite(item.precio_venta)
      || item.precio_venta < 0
      || (item.precio_costo != null && (!Number.isFinite(item.precio_costo) || item.precio_costo < 0))
    )) {
      setError('Completa un SKU existente, una cantidad entera y un precio de venta válido para cada línea.');
      return null;
    }
    return cleanItems;
  }

  function applyMargin() {
    const percentage = Number(margin);
    if (!Number.isFinite(percentage) || percentage < 0) {
      setError('Ingresa un margen porcentual válido.');
      return;
    }
    const withoutCost = items.some((item) => item.precio_costo === '');
    setItems((current) => current.map((item) => {
      const cost = Number(item.precio_costo);
      if (!Number.isFinite(cost) || cost < 0) return item;
      return { ...item, precio_venta: String(Math.round(cost * (1 + percentage / 100))) };
    }));
    setError(withoutCost ? 'Se calcularon los precios de las líneas con costo; completa manualmente las que no tienen costo.' : '');
    setMessage('');
  }

  async function saveItems() {
    if (!selectedInvoice || !canEdit) return;
    const cleanItems = validatedItems();
    if (!cleanItems) return;
    setBusy('save');
    setError('');
    setMessage('');
    try {
      const updated = await invoiceService.saveItems(selectedInvoice.id, cleanItems);
      setInvoices((current) => current.map((invoice) => invoice.id === updated.id ? updated : invoice));
      setMessage('Líneas guardadas correctamente.');
    } catch (cause) {
      setError(errorMessage(cause, 'No se pudieron guardar los productos de la factura.'));
    } finally {
      setBusy('');
    }
  }

  async function openInvoicePreview() {
    if (!selectedInvoice) return;
    setBusy('preview');
    setError('');
    try {
      const fileContent = await invoiceService.file(selectedInvoice.id);
      setPreview({
        url: URL.createObjectURL(fileContent),
        contentType: selectedInvoice.content_type,
        filename: selectedInvoice.nombre_archivo,
        text: selectedInvoice.content_type.includes('xml') ? await fileContent.text() : '',
      });
    } catch (cause) {
      setError(errorMessage(cause, 'No se pudo abrir el archivo de la factura.'));
    } finally {
      setBusy('');
    }
  }

  async function approveInvoice() {
    if (!selectedInvoice) return;
    setError('');
    setMessage('');
    if (canEdit) {
      const cleanItems = validatedItems();
      if (!cleanItems) return;
      setBusy('approve');
      try {
        const updated = await invoiceService.saveItems(selectedInvoice.id, cleanItems);
        setInvoices((current) => current.map((invoice) => invoice.id === updated.id ? updated : invoice));
      } catch (cause) {
        setError(errorMessage(cause, 'No se pudieron guardar los productos de la factura.'));
        setBusy('');
        return;
      }
    } else {
      setBusy('approve');
    }

    try {
      await invoiceService.approve(selectedInvoice.id);
      setInvoices((current) => current.filter((invoice) => invoice.id !== selectedInvoice.id));
      setSelectedId('');
      setItems([]);
      setMessage('Factura aprobada y stock ingresado al inventario.');
    } catch (cause) {
      const approvalError = errorMessage(cause, 'No se pudo aprobar la factura.');
      setError(approvalError);
      try {
        await loadPending();
      } catch (refreshError) {
        setError(`${approvalError} ${errorMessage(refreshError, 'No se pudo actualizar la lista de facturas.')}`);
      }
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="invoice-workspace">
      <section className="data-panel invoice-upload">
        <div className="form-heading">
          <span><ScanLine /></span>
          <div>
            <h2>Escanear factura</h2>
            <p>Sube el XML del DTE; si no lo tienes, prueba con PDF o imagen. La extracción se ejecuta localmente.</p>
          </div>
        </div>
        <div className="invoice-upload__controls">
          <label className="invoice-file">
            <FileText size={20} />
            <span>{file?.name || 'Seleccionar XML, PDF o imagen (máximo 15 MB)'}</span>
            <input
              ref={fileInput}
              type="file"
              accept="application/xml,text/xml,application/pdf,image/jpeg,image/png,image/webp,.xml,.pdf,.jpg,.jpeg,.png,.webp"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <button
            className="primary-button"
            type="button"
            disabled={!file || Boolean(busy)}
            onClick={scanInvoice}
          >
            {busy === 'scan' ? <LoaderCircle className="invoice-spin" /> : <Upload />}
            {busy === 'scan' ? 'Procesando…' : 'Subir factura'}
          </button>
        </div>
        <p className="invoice-note">La extracción solo propone datos: siempre revisa los productos, cantidades y precios antes de aprobar.</p>
      </section>

      <div className="invoice-columns">
        <aside className="data-panel invoice-pending">
          <div className="invoice-section-heading">
            <div>
              <h2>Facturas por revisar</h2>
              <p>{invoices.length} pendientes</p>
            </div>
            <button
              className="icon-button"
              type="button"
              aria-label="Actualizar facturas"
              onClick={refresh}
              disabled={loading || Boolean(busy)}
            >
              <RefreshCw size={17} />
            </button>
          </div>
          <div className="invoice-pending__list">
            {loading ? (
              <div className="table-message">Cargando facturas…</div>
            ) : invoices.length ? invoices.map((invoice) => (
              <button
                className={`invoice-pending__item ${selectedId === invoice.id ? 'is-selected' : ''}`}
                type="button"
                key={invoice.id}
                onClick={() => {
                  setSelectedId(invoice.id);
                  setPreview(null);
                  setError('');
                  setMessage('');
                }}
              >
                <FileText size={19} />
                <span>
                  <strong>{invoice.nombre_archivo}</strong>
                  <small>{new Date(invoice.fecha_creacion).toLocaleString('es-CL')}</small>
                </span>
                <em className={invoice.estado === processingStatus ? 'is-processing' : ''}>
                  {invoice.estado === processingStatus ? 'En proceso' : 'Pendiente'}
                </em>
              </button>
            )) : (
              <div className="empty-state compact">
                <FileText />
                <strong>No hay facturas pendientes</strong>
                <span>Las facturas subidas aparecerán aquí para revisión.</span>
              </div>
            )}
          </div>
        </aside>

        <section className="data-panel invoice-review">
          {selectedInvoice ? (
            <>
              <div className="invoice-section-heading">
                <div>
                  <h2>Revisar productos</h2>
                  <p>{selectedInvoice.nombre_archivo}</p>
                </div>
                <div className="invoice-badges">
                  <span className="invoice-status">{extractionLabels[selectedInvoice.estado_ocr] || selectedInvoice.estado_ocr}</span>
                  <span className={`invoice-status ${canEdit ? '' : 'is-processing'}`}>
                    {canEdit ? 'Pendiente de aprobación' : 'Aprobación en proceso'}
                  </span>
                </div>
              </div>
              <div className="invoice-review__toolbar">
                <span>Selecciona el SKU del catálogo y confirma el precio de venta para cada producto.</span>
                <div>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={openInvoicePreview}
                    disabled={Boolean(busy)}
                  >
                    {busy === 'preview' ? <LoaderCircle className="invoice-spin" /> : <Eye size={17} />}
                    Ver factura
                  </button>
                  {canEdit && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => setItems((current) => [...current, {
                        sku: '',
                        codigo_proveedor: '',
                        nombre: '',
                        cantidad: '1',
                        precio_costo: '',
                        precio_venta: '',
                      }])}
                      disabled={Boolean(busy)}
                    >
                      <Plus size={17} /> Agregar producto
                    </button>
                  )}
                </div>
              </div>
              <datalist id="girasol-inventory-skus">
                {catalogue.map((product) => (
                  <option key={product.id} value={product.barcode}>
                    {product.Prenda} · {product.Marca}
                  </option>
                ))}
              </datalist>
              <div className="table-wrap">
                <table className="data-table invoice-table">
                  <thead>
                    <tr><th>SKU Girasol / proveedor</th><th>Producto</th><th>Cant.</th><th>Costo compra</th><th>Precio venta</th><th></th></tr>
                  </thead>
                  <tbody>
                    {items.length ? items.map((item, index) => (
                      <tr key={`${selectedInvoice.id}-${index}`}>
                        <td>
                          <input aria-label="SKU de Girasol" list="girasol-inventory-skus" value={item.sku} disabled={!canEdit || Boolean(busy)} onChange={(event) => selectInventorySku(index, event.target.value)} />
                          {item.codigo_proveedor && <small className="invoice-provider-code">Prov.: {item.codigo_proveedor}</small>}
                        </td>
                        <td><input aria-label="Producto" value={item.nombre} disabled={!canEdit || Boolean(busy)} onChange={(event) => changeItem(index, 'nombre', event.target.value)} /></td>
                        <td><input aria-label="Cantidad" type="number" min="1" step="1" value={item.cantidad} disabled={!canEdit || Boolean(busy)} onChange={(event) => changeItem(index, 'cantidad', event.target.value)} /></td>
                        <td><input aria-label="Costo de compra" type="number" min="0" step="1" value={item.precio_costo} disabled={!canEdit || Boolean(busy)} onChange={(event) => changeItem(index, 'precio_costo', event.target.value)} /></td>
                        <td><input aria-label="Precio de venta" type="number" min="0" step="1" value={item.precio_venta} disabled={!canEdit || Boolean(busy)} onChange={(event) => changeItem(index, 'precio_venta', event.target.value)} /></td>
                        <td>
                          {canEdit && (
                            <button
                              className="icon-button danger"
                              type="button"
                              aria-label="Eliminar producto"
                              disabled={Boolean(busy)}
                              onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                            >
                              <Trash2 size={17} />
                            </button>
                          )}
                        </td>
                      </tr>
                    )) : (
                      <tr><td colSpan="6" className="table-message">No se detectaron productos automáticamente. Usa “Agregar producto” o revisa la factura.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {canEdit && (
                <div className="invoice-margin">
                  <label>
                    Margen sobre costo (%)
                    <input type="number" min="0" step="1" value={margin} onChange={(event) => setMargin(event.target.value)} placeholder="Ej: 50" />
                  </label>
                  <button className="secondary-button" type="button" disabled={Boolean(busy) || margin === ''} onClick={applyMargin}>
                    Calcular precios con margen
                  </button>
                </div>
              )}
              <div className="invoice-review__actions">
                {canEdit && (
                  <button className="secondary-button" type="button" disabled={Boolean(busy)} onClick={saveItems}>
                    <Save size={17} /> Guardar revisión
                  </button>
                )}
                <button
                  className="primary-button"
                  type="button"
                  disabled={Boolean(busy)}
                  onClick={approveInvoice}
                >
                  {busy === 'approve' ? <LoaderCircle className="invoice-spin" /> : <Check />}
                  {busy === 'approve'
                    ? 'Ingresando…'
                    : canEdit
                      ? 'Aprobar e ingresar al inventario'
                      : 'Reintentar aprobación'}
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state invoice-review__empty">
              <ScanLine />
              <strong>Selecciona una factura</strong>
              <span>Sube una nueva o elige una pendiente para revisar sus productos.</span>
            </div>
          )}
        </section>
      </div>

      {(error || message) && (
        <p className={`feedback invoice-feedback ${error ? 'is-error' : 'is-success'}`} role="status">
          {error || message}
        </p>
      )}

      {preview && (
        <div className="modal-backdrop invoice-preview-backdrop" onMouseDown={() => setPreview(null)}>
          <section
            className="invoice-preview"
            role="dialog"
            aria-modal="true"
            aria-label="Vista previa de la factura"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header>
              <strong>{preview.filename}</strong>
              <button type="button" aria-label="Cerrar vista previa" onClick={() => setPreview(null)}>
                <X />
              </button>
            </header>
            {preview.contentType === 'application/pdf' ? (
              <iframe title={`Vista previa de ${preview.filename}`} src={preview.url} />
            ) : preview.contentType.includes('xml') ? (
              <pre className="invoice-xml-preview">{preview.text}</pre>
            ) : (
              <img src={preview.url} alt={`Factura ${preview.filename}`} />
            )}
          </section>
        </div>
      )}
    </section>
  );
}
