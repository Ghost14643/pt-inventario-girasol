import React from "react";
import {
  Banknote,
  CreditCard,
  HeartHandshake,
  Minus,
  Plus,
  ScanBarcode,
  Search,
  ShoppingBag,
  Trash2,
  UserRound,
  WalletCards,
  X,
} from "lucide-react";
import { AppLayout } from "../components/AppLayout.jsx";
import {
  clientService,
  inventoryService,
  salesService,
} from "../services/api.js";

const money = (value) =>
  new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
export function VentasPage({ session, ...props }) {
  const [barcode, setBarcode] = React.useState("");
  const [items, setItems] = React.useState([]);
  const [method, setMethod] = React.useState("efectivo");
  const [msg, setMsg] = React.useState("");
  const [clientSearch, setClientSearch] = React.useState("");
  const [clientResults, setClientResults] = React.useState([]);
  const [selectedClient, setSelectedClient] = React.useState(null);
  const [manualClientRut, setManualClientRut] = React.useState("");
  const [searching, setSearching] = React.useState(false);
  const [cardPayment, setCardPayment] = React.useState({
    ultimos_4_digitos: "",
    codigo_autorizacion: "",
    numero_comprobante: "",
    cantidad_cuotas: "1",
    marca_tarjeta: "",
  });
  React.useEffect(() => {
    if (method !== "credito_girasol" || clientSearch.trim().length < 2) {
      setClientResults([]);
      return;
    }
    let active = true;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const rows = await clientService.creditSearch(clientSearch);
        if (active) setClientResults(rows);
      } catch {
        if (active) setMsg("No fue posible buscar clientas.");
      } finally {
        if (active) setSearching(false);
      }
    }, 280);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [clientSearch, method]);
  async function add() {
    if (!barcode) return;
    try {
      const p = await inventoryService.bySku(barcode);
      setItems((current) => {
        const index = current.findIndex((x) => x.barcode === p.barcode);
        return index < 0
          ? [...current, { ...p, cantidad: 1 }]
          : current.map((x, n) =>
              n === index ? { ...x, cantidad: x.cantidad + 1 } : x,
            );
      });
      setBarcode("");
      setMsg("");
    } catch {
      setMsg("No encontramos ese código de barra.");
    }
  }
  function qty(index, delta) {
    setItems((current) =>
      current.map((x, n) =>
        n === index ? { ...x, cantidad: Math.max(1, x.cantidad + delta) } : x,
      ),
    );
  }
  const total = items.reduce(
    (sum, item) => sum + item.precio * item.cantidad,
    0,
  );
  const creditInvalid = method === "credito_girasol" && !selectedClient;
  const isCardPayment = method === "debito" || method === "credito";
  async function sell() {
    if (isCardPayment) {
      if (!/^\d{4}$/.test(cardPayment.ultimos_4_digitos)) {
        setMsg("Ingresa los 4 últimos dígitos de la tarjeta.");
        return;
      }

      if (
        !cardPayment.codigo_autorizacion.trim() ||
        cardPayment.codigo_autorizacion.trim().length > 20
      ) {
        setMsg("Ingresa un código de autorización de hasta 20 caracteres.");
        return;
      }

      if (
        !cardPayment.numero_comprobante.trim() ||
        cardPayment.numero_comprobante.trim().length > 30
      ) {
        setMsg("Ingresa un número de comprobante de hasta 30 caracteres.");
        return;
      }

      const cuotas =
        method === "debito" ? 1 : Number(cardPayment.cantidad_cuotas);
      if (!Number.isInteger(cuotas) || cuotas < 1) {
        setMsg(
          "La cantidad de cuotas debe ser un número entero mayor que cero.",
        );
        return;
      }

      if (cardPayment.marca_tarjeta.trim().length > 30) {
        setMsg("La marca de tarjeta no debe superar 30 caracteres.");
        return;
      }
    }
    if (method === "credito_girasol") {
      let resolvedClient = selectedClient;
      if (!resolvedClient && manualClientRut.trim()) {
        const rows = await clientService.list(manualClientRut.trim());
        resolvedClient =
          rows.find(
            (row) =>
              row.rut.replace(".", "").toLowerCase() ===
              manualClientRut.trim().replace(".", "").toLowerCase(),
          ) ||
          rows[0] ||
          null;
        if (resolvedClient) setSelectedClient(resolvedClient);
      }
      if (!resolvedClient) {
        setMsg(
          "Selecciona una clienta o ingresa un RUT válido para usar Crédito Girasol.",
        );
        return;
      }
      try {
        const result = await salesService.create({
          subtotal: total,
          productos: items,
          descuento_total: 0,
          metodo_pago: method,
          rut_empleado: session.rut || "sistema",
          cliente_rut: resolvedClient.rut,
        });
        setItems([]);
        setSelectedClient(null);
        setClientSearch("");
        setManualClientRut("");
        setMsg(
          method === "credito_girasol"
            ? `Venta a Crédito Girasol registrada. Disponible restante: ${money(result.sale.credito.disponible)}.`
            : "Venta registrada correctamente.",
        );
        return;
      } catch (error) {
        setMsg(
          error?.response?.data?.detail || "No fue posible registrar la venta.",
        );
        return;
      }
    }
    try {
      const result = await salesService.create({
        subtotal: total,
        productos: items,
        descuento_total: 0,
        metodo_pago: method,
        rut_empleado: session.rut || "sistema",
        cliente_rut: null,
        ...(isCardPayment && {
          ultimos_4_digitos: cardPayment.ultimos_4_digitos,
          codigo_autorizacion: cardPayment.codigo_autorizacion.trim(),
          numero_comprobante: cardPayment.numero_comprobante.trim(),
          cantidad_cuotas:
            method === "debito" ? 1 : Number(cardPayment.cantidad_cuotas),
          marca_tarjeta: cardPayment.marca_tarjeta.trim() || null,
        }),
      });
      setItems([]);
      setSelectedClient(null);
      setClientSearch("");
      setManualClientRut("");
      setCardPayment({
        ultimos_4_digitos: "",
        codigo_autorizacion: "",
        numero_comprobante: "",
        cantidad_cuotas: "1",
        marca_tarjeta: "",
      });
      setMsg("Venta registrada correctamente.");
    } catch (error) {
      setMsg(
        error?.response?.data?.detail || "No fue posible registrar la venta.",
      );
    }
  }
  function chooseMethod(id) {
    setMethod(id);
    setMsg("");
    if (id !== "credito_girasol") {
      setSelectedClient(null);
      setClientSearch("");
      setManualClientRut("");
    }
  }
  return (
    <AppLayout
      {...props}
      session={session}
      active="ventas"
      title="Nueva venta"
      eyebrow="Punto de venta"
    >
      <div className="sales-grid">
        <section>
          <div className="scan-card">
            <div className="scan-card__icon">
              <ScanBarcode />
            </div>
            <div>
              <h2>Escanear o ingresar producto</h2>
              <p>Usa el lector o escribe el código manualmente.</p>
              <div className="scan-input">
                <input
                  autoFocus
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && add()}
                  placeholder="Ej: 7801234567890"
                />
                <button onClick={add}>Agregar producto</button>
              </div>
            </div>
          </div>
          <div className="data-panel cart">
            <div className="data-panel__top">
              <div>
                <h2>Detalle de la venta</h2>
                <p>{items.length} productos agregados</p>
              </div>
              <button className="text-button" onClick={() => setItems([])}>
                Limpiar venta
              </button>
            </div>
            {items.length ? (
              <div className="cart-list">
                {items.map((x, i) => (
                  <div className="cart-item" key={`${x.barcode}-${i}`}>
                    <span className="cart-thumb">
                      <ShoppingBag />
                    </span>
                    <div>
                      <strong>{x.nombre}</strong>
                      <small>Cód. {x.barcode}</small>
                    </div>
                    <div className="stepper">
                      <button onClick={() => qty(i, -1)}>
                        <Minus />
                      </button>
                      <b>{x.cantidad}</b>
                      <button onClick={() => qty(i, 1)}>
                        <Plus />
                      </button>
                    </div>
                    <strong>{money(x.precio * x.cantidad)}</strong>
                    <button
                      className="delete"
                      onClick={() =>
                        setItems((c) => c.filter((_, n) => n !== i))
                      }
                    >
                      <Trash2 />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <ShoppingBag />
                <strong>Tu venta está vacía</strong>
                <span>Escanea un producto para comenzar.</span>
              </div>
            )}
          </div>
        </section>
        <aside className="checkout">
          <h2>Resumen</h2>
          <div className="totals">
            <span>
              Subtotal <b>{money(total)}</b>
            </span>
            <span>
              Descuento <b>{money(0)}</b>
            </span>
            <hr />
            <span className="grand-total">
              Total <b>{money(total)}</b>
            </span>
          </div>
          <h3>Método de pago</h3>
          <div className="payment-grid payment-grid--four">
            {[
              ["efectivo", Banknote, "Efectivo"],
              ["debito", WalletCards, "Débito"],
              ["credito", CreditCard, "Crédito"],
              ["credito_girasol", HeartHandshake, "Crédito Girasol"],
            ].map(([id, Icon, label]) => (
              <button
                key={id}
                className={method === id ? "active" : ""}
                onClick={() => chooseMethod(id)}
              >
                <Icon />
                <span>{label}</span>
              </button>
            ))}
          </div>
          {isCardPayment && (
            <div className="girasol-credit card-payment">
              <div className="girasol-credit__title">
                <CreditCard />
                <div>
                  <strong>Datos del pago con tarjeta</strong>
                  <small>Completa los datos del comprobante</small>
                </div>
              </div>

              <div className="card-payment__fields">
                <label>
                  Últimos 4 dígitos
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={4}
                    placeholder="Ej: 1234"
                    value={cardPayment.ultimos_4_digitos}
                    onChange={(event) =>
                      setCardPayment((current) => ({
                        ...current,
                        ultimos_4_digitos: event.target.value
                          .replace(/\D/g, "")
                          .slice(0, 4),
                      }))
                    }
                  />
                </label>

                <label>
                  Código de autorización
                  <input
                    type="text"
                    maxLength={20}
                    value={cardPayment.codigo_autorizacion}
                    onChange={(event) =>
                      setCardPayment((current) => ({
                        ...current,
                        codigo_autorizacion: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  Número de comprobante
                  <input
                    type="text"
                    maxLength={30}
                    value={cardPayment.numero_comprobante}
                    onChange={(event) =>
                      setCardPayment((current) => ({
                        ...current,
                        numero_comprobante: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  Cuotas
                  <input
                    type="number"
                    min="1"
                    step="1"
                    disabled={method === "debito"}
                    value={
                      method === "debito" ? 1 : cardPayment.cantidad_cuotas
                    }
                    onChange={(event) =>
                      setCardPayment((current) => ({
                        ...current,
                        cantidad_cuotas: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  Marca de tarjeta (opcional)
                  <input
                    type="text"
                    maxLength={30}
                    placeholder="Ej: Visa"
                    value={cardPayment.marca_tarjeta}
                    onChange={(event) =>
                      setCardPayment((current) => ({
                        ...current,
                        marca_tarjeta: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>
            </div>
          )}
          {method === "credito_girasol" && (
            <div className="girasol-credit">
              <div className="girasol-credit__title">
                <HeartHandshake />
                <div>
                  <strong>Clienta para Crédito Girasol</strong>
                  <small>Busca por nombre o RUT</small>
                </div>
              </div>
              {selectedClient ? (
                <div className="selected-credit-client">
                  <span>
                    <UserRound />
                  </span>
                  <div>
                    <strong>{selectedClient.nombre}</strong>
                    <small>{selectedClient.rut}</small>
                    <p>
                      Disponible{" "}
                      <b>{money(selectedClient.credito_disponible)}</b> de{" "}
                      {money(selectedClient.tope_credito)}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedClient(null)}
                    aria-label="Quitar clienta"
                  >
                    <X />
                  </button>
                </div>
              ) : (
                <>
                  <div className="credit-client-search">
                    <Search />
                    <input
                      value={clientSearch}
                      onChange={(e) => setClientSearch(e.target.value)}
                      placeholder="Nombre o RUT de la clienta"
                    />
                  </div>
                  {searching && (
                    <small className="credit-search-status">Buscando…</small>
                  )}
                  <div className="credit-client-results">
                    {clientResults.map((client) => (
                      <button
                        key={client.rut}
                        onClick={() => {
                          setSelectedClient(client);
                          setClientResults([]);
                        }}
                      >
                        <span>
                          <strong>{client.nombre}</strong>
                          <small>{client.rut}</small>
                        </span>
                        <span>
                          <small>Disponible</small>
                          <b>{money(client.credito_disponible)}</b>
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}{" "}
          {creditInvalid && selectedClient && (
            <p className="credit-warning">
              El total supera el crédito disponible de la clienta.
            </p>
          )}
          <button
            className="primary-button full"
            disabled={!items.length || creditInvalid}
            onClick={sell}
          >
            Confirmar venta · {money(total)}
          </button>
          {msg && <p className="feedback center">{msg}</p>}
          <p className="secure-note">
            La venta quedará registrada en el arqueo del turno.
          </p>
        </aside>
      </div>
    </AppLayout>
  );
}
