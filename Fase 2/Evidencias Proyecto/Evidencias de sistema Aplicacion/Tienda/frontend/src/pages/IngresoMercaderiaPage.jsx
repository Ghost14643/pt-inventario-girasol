import React from "react";
import {
  Barcode,
  Check,
  PackagePlus,
  Plus,
  Shirt,
  Tags,
  Trash2,
  X,
} from "lucide-react";
import { AppLayout } from "../components/AppLayout.jsx";
import { brandService, inventoryService } from "../services/api.js";

const emptyNewProduct = {
  nombre: "",
  marca: "",
  precio: "",
  talla: "",
  color: "",
};

const errorText = (error) =>
  error?.response?.data?.detail || "No fue posible completar el ingreso.";

export function IngresoMercaderiaPage(props) {
  const [barcode, setBarcode] = React.useState("");
  const [mode, setMode] = React.useState("buscar");
  const [existing, setExisting] = React.useState(null);
  const [newProduct, setNewProduct] = React.useState(emptyNewProduct);
  const [quantity, setQuantity] = React.useState("1");
  const [reference, setReference] = React.useState("");
  const [brands, setBrands] = React.useState([]);
  const [brandModal, setBrandModal] = React.useState(false);
  const [newBrand, setNewBrand] = React.useState("");
  const [batch, setBatch] = React.useState([]);
  const [searching, setSearching] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [message, setMessage] = React.useState("");
  const [isError, setIsError] = React.useState(false);

  React.useEffect(() => {
    brandService
      .list()
      .then(setBrands)
      .catch(() => {
        setBrands([]);
      });
  }, []);

  const setNewField = (field, value) => {
    setNewProduct((current) => ({ ...current, [field]: value }));
  };

  async function createBrand(event) {
    event.preventDefault();

    try {
      const createdBrand = await brandService.create(newBrand.trim());

      setBrands((current) =>
        [...current, createdBrand].sort((a, b) =>
          a.nombre.localeCompare(b.nombre),
        ),
      );
      setNewField("marca", createdBrand.nombre);
      setNewBrand("");
      setBrandModal(false);
      setMessage("Marca creada correctamente.");
      setIsError(false);
    } catch (error) {
      setMessage(errorText(error));
      setIsError(true);
    }
  }

  async function lookup(event) {
    event.preventDefault();
    const code = barcode.trim();

    if (!code) {
      setMessage("Escribe o escanea un código/SKU.");
      setIsError(true);
      return;
    }

    setSearching(true);
    setMessage("");
    setIsError(false);
    setExisting(null);

    try {
      const product = await inventoryService.lookupForReceiving(code);
      setExisting(product);
      setMode("existente");
    } catch (error) {
      if (error?.response?.status === 404) {
        setNewProduct(emptyNewProduct);
        setMode("nueva");
      } else {
        setMode("buscar");
        setMessage(errorText(error));
        setIsError(true);
      }
    } finally {
      setSearching(false);
    }
  }

  function addToBatch() {
    const amount = Number(quantity);
    if (!Number.isInteger(amount) || amount < 1 || amount > 10_000) {
      setMessage("La cantidad debe ser un entero entre 1 y 10.000.");
      setIsError(true);
      return;
    }

    const cleanReference = reference.trim();
    if (cleanReference.length > 100) {
      setMessage("La referencia admite hasta 100 caracteres.");
      setIsError(true);
      return;
    }

    let item;

    if (mode === "existente" && existing) {
      if (batch.some((line) => line.id_variante === existing.id)) {
        setMessage(
          "Esta variante ya está en el ingreso. Elimina esa línea antes de agregarla otra vez.",
        );
        setIsError(true);
        return;
      }

      item = {
        tipo: "existente",
        id_variante: existing.id,
        cantidad: amount,
        referencia: cleanReference || null,
        nombre: existing.nombre,
        sku: existing.sku || existing.barcode,
        talla: existing.talla,
        color: existing.color,
        marca: existing.marca,
        stock_actual: existing.stock,
      };
    } else if (mode === "nueva") {
      const code = barcode.trim();
      const name = newProduct.nombre.trim();
      const brand = newProduct.marca.trim();
      const size = newProduct.talla.trim();
      const color = newProduct.color.trim();
      const price = Number(newProduct.precio);

      if (!code || !name || !brand || newProduct.precio === "") {
        setMessage("Completa código, nombre, marca y precio.");
        setIsError(true);
        return;
      }
      if (!Number.isInteger(price) || price < 0) {
        setMessage("El precio debe ser un entero igual o mayor que cero.");
        setIsError(true);
        return;
      }
      if (
        batch.some(
          (line) =>
            line.tipo === "nueva" &&
            line.barcode.toLowerCase() === code.toLowerCase(),
        )
      ) {
        setMessage("Ese código ya está agregado al ingreso.");
        setIsError(true);
        return;
      }

      item = {
        tipo: "nueva",
        barcode: code,
        nombre: name,
        marca: brand,
        precio: price,
        talla: size,
        color,
        cantidad: amount,
        referencia: cleanReference || null,
      };
    } else {
      setMessage("Primero busca un código/SKU.");
      setIsError(true);
      return;
    }

    setBatch((current) => [...current, item]);
    setBarcode("");
    setExisting(null);
    setNewProduct(emptyNewProduct);
    setQuantity("1");
    setReference("");
    setMode("buscar");
    setMessage("Producto agregado al resumen del ingreso.");
    setIsError(false);
  }

  async function confirmBatch() {
    if (!batch.length || saving) return;

    setSaving(true);
    setMessage("");
    setIsError(false);

    try {
      await inventoryService.confirmReceiving(
        batch.map((item) => {
          const { nombre, sku, talla, color, marca, stock_actual, ...payload } =
            item;
          return payload;
        }),
      );

      setBatch([]);
      setMessage("Ingreso confirmado correctamente.");
    } catch (error) {
      setMessage(errorText(error));
      setIsError(true);
    } finally {
      setSaving(false);
    }
  }

  function resetCurrentEntry() {
    setMode("buscar");
    setBarcode("");
    setExisting(null);
    setNewProduct(emptyNewProduct);
    setQuantity("1");
    setReference("");
    setMessage("");
    setIsError(false);
  }

  return (
    <AppLayout
      {...props}
      active="ingreso-mercaderia"
      title="Ingreso de mercadería"
      eyebrow="Recepción de productos"
    >
      <div className="entry-grid">
        <section className="data-panel form-panel">
          <div className="form-heading">
            <span>
              <PackagePlus />
            </span>
            <div>
              <h2>Agregar al ingreso</h2>
              <p>Busca una variante existente o registra una prenda nueva.</p>
            </div>
          </div>

          <form className="receiving-search" onSubmit={lookup}>
            <label className="receiving-search__label">
              Código de barra o SKU
              <div className="input-icon">
                <Barcode />
                <input
                  autoFocus
                  value={barcode}
                  onChange={(event) => {
                    setBarcode(event.target.value);
                    setMode("buscar");
                    setExisting(null);
                  }}
                  placeholder="Escanea o escribe el código"
                />
              </div>
            </label>

            <button
              type="submit"
              className="primary-button receiving-search__button"
              disabled={searching || !barcode.trim()}
            >
              {searching ? "Buscando…" : "Buscar"}
            </button>
          </form>

          {mode === "existente" && existing && (
            <div className="receiving-product">
              <div className="receiving-product__heading">
                <strong>Variante existente</strong>
                <span>Reposición</span>
              </div>
              <div className="receiving-product__details">
                <span>
                  Producto<strong>{existing.nombre}</strong>
                </span>
                <span>
                  SKU<strong>{existing.sku || existing.barcode}</strong>
                </span>
                <span>
                  Marca<strong>{existing.marca || "—"}</strong>
                </span>
                <span>
                  Talla<strong>{existing.talla || "Sin especificar"}</strong>
                </span>
                <span>
                  Color<strong>{existing.color || "Sin especificar"}</strong>
                </span>
                <span>
                  Stock actual<strong>{existing.stock} unidades</strong>
                </span>
              </div>
            </div>
          )}

          {mode === "nueva" && (
            <div className="form-grid receiving-new-product">
              <div className="receiving-product__heading wide">
                <strong>Producto nuevo</strong>
                <span>Se registrará al confirmar el ingreso</span>
              </div>
              <label className="wide">
                Nombre de la prenda
                <input
                  value={newProduct.nombre}
                  maxLength="100"
                  onChange={(event) =>
                    setNewField("nombre", event.target.value)
                  }
                  placeholder="Ej: Blusa lino manga larga"
                />
              </label>
              <label>
                Marca
                <div className="brand-select-row">
                  <select
                    value={newProduct.marca}
                    onChange={(event) =>
                      setNewField("marca", event.target.value)
                    }
                  >
                    <option value="">Seleccionar marca</option>
                    {brands.map((brand) => (
                      <option key={brand.id} value={brand.nombre}>
                        {brand.nombre}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => {
                      setNewBrand("");
                      setBrandModal(true);
                    }}
                    title="Crear nueva marca"
                    aria-label="Crear nueva marca"
                  >
                    <Plus />
                  </button>
                </div>
              </label>
              <label>
                Precio de venta
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={newProduct.precio}
                  onChange={(event) =>
                    setNewField("precio", event.target.value)
                  }
                  placeholder="0"
                />
              </label>
              <label>
                Talla
                <input
                  maxLength="10"
                  value={newProduct.talla}
                  onChange={(event) => setNewField("talla", event.target.value)}
                  placeholder="Ej: M"
                />
              </label>
              <label>
                Color
                <input
                  maxLength="30"
                  value={newProduct.color}
                  onChange={(event) => setNewField("color", event.target.value)}
                  placeholder="Ej: Azul"
                />
              </label>
            </div>
          )}

          {(mode === "existente" || mode === "nueva") && (
            <>
              <div className="form-grid receiving-quantity">
                <label>
                  Cantidad a ingresar
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    step="1"
                    value={quantity}
                    onChange={(event) => setQuantity(event.target.value)}
                  />
                </label>
                <label>
                  Referencia (opcional)
                  <input
                    maxLength="100"
                    value={reference}
                    onChange={(event) => setReference(event.target.value)}
                    placeholder="Compra proveedor"
                  />
                </label>
              </div>
              {mode === "existente" && existing && (
                <p className="receiving-result">
                  Stock resultante:{" "}
                  <strong>
                    {Number(existing.stock) + Number(quantity || 0)} unidades
                  </strong>
                </p>
              )}
              <div className="receiving-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={resetCurrentEntry}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="primary-button"
                  onClick={addToBatch}
                >
                  <Plus /> Agregar al ingreso
                </button>
              </div>
            </>
          )}

          {message && (
            <p
              className={
                isError ? "receiving-message error" : "receiving-message"
              }
            >
              {message}
            </p>
          )}
        </section>

        <aside className="batch-panel">
          <div className="batch-head">
            <div>
              <h2>Resumen del ingreso</h2>
              <p>Productos por confirmar</p>
            </div>
            <span>{batch.length}</span>
          </div>

          {batch.length ? (
            <div className="batch-list">
              {batch.map((item, index) => (
                <div key={`${item.tipo}-${item.id_variante || item.barcode}`}>
                  <span>
                    <Shirt />
                  </span>
                  <p>
                    <strong>{item.nombre}</strong>
                    <small>
                      {item.tipo === "existente"
                        ? "Reposición"
                        : "Nueva prenda"}
                      {" · "}
                      {item.talla || "Sin talla"}
                      {" · "}
                      {item.color || "Sin color"}
                      {" · "}
                      {item.cantidad} un.
                      {item.tipo === "existente" &&
                        ` · Stock ${item.stock_actual} → ${item.stock_actual + item.cantidad}`}
                    </small>
                  </p>
                  <button
                    type="button"
                    aria-label={`Quitar ${item.nombre}`}
                    disabled={saving}
                    onClick={() =>
                      setBatch((current) =>
                        current.filter((_, i) => i !== index),
                      )
                    }
                  >
                    <Trash2 />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state compact">
              <Tags />
              <strong>Aún no hay productos</strong>
              <span>Busca un código para agregarlo al ingreso.</span>
            </div>
          )}

          <button
            className="primary-button full"
            disabled={!batch.length || saving}
            onClick={confirmBatch}
          >
            <Check />
            {saving ? "Confirmando…" : "Confirmar ingreso"}
          </button>
        </aside>
      </div>
      {brandModal && (
        <div className="modal-backdrop">
          <form
            className="brand-modal"
            onSubmit={createBrand}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <span>
                  <Tags />
                </span>
                <div>
                  <h2>Nueva marca</h2>
                  <p>Se guardará para futuros ingresos.</p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setBrandModal(false)}
                aria-label="Cerrar"
              >
                <X />
              </button>
            </div>

            <label>
              Nombre de la marca
              <input
                autoFocus
                value={newBrand}
                onChange={(event) => setNewBrand(event.target.value)}
                maxLength="100"
                placeholder="Ej: Girasol Collection"
                required
              />
            </label>

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setBrandModal(false)}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="primary-button"
                disabled={!newBrand.trim()}
              >
                Crear marca
              </button>
            </div>
          </form>
        </div>
      )}
    </AppLayout>
  );
}
