import { ClockWidget } from '../components/ClockWidget.jsx';
import { MenuCard } from '../components/MenuCard.jsx';
import { Sidebar } from '../components/Sidebar.jsx';

// Ilustración decorativa del menú. Para sustituirla por un arte nuevo,
// coloque bg-boutique.png en assets/ y actualice solamente esta importación.
import boutiqueBackground from '../../assets/fondo_venta5.png';
import facturasIcon from '../../assets/FacturasIcono.png';
import configuracionIcon from '../../assets/InformesIcono.png';
import inventarioIcon from '../../assets/InventarioIcono.png';
import mercaderiaIcon from '../../assets/Mercaderia.png';
import clientasIcon from '../../assets/Usuarias.png';
import ventasIcon from '../../assets/VentasIcono.png';

const modules = [
  { id: 'inventario', title: 'Inventario', description: 'Stock, prendas y categorías', icon: inventarioIcon },
  { id: 'ventas', title: 'Ventas', description: 'Registrar una nueva venta', icon: ventasIcon },
  { id: 'configuracion', title: 'Configuración', description: 'Usuarios, claves y descuentos', icon: configuracionIcon, adminOnly: true },
  { id: 'clientes', title: 'Clientas', description: 'Agenda y datos de contacto', icon: clientasIcon },
  { id: 'arqueo', title: 'Facturas y arqueo', description: 'Cierre y documentos de caja', icon: facturasIcon },
  { id: 'ingreso-mercaderia', title: 'Ingreso de mercadería', description: 'Recepción de nuevas prendas', icon: mercaderiaIcon },
];

export function MainMenu({ session, dark = false, onToggleTheme, onNavigate, onLogout }) {
  return (
    <div className={`boutique-shell ${dark ? 'theme-dark' : ''}`}>
      <Sidebar active="menu" dark={dark} onToggleTheme={onToggleTheme} onNavigate={onNavigate} onLogout={onLogout} />

      <main className="main-menu" style={{ '--boutique-background': `url(${boutiqueBackground})` }}>
        <header className="main-menu__header">
          <div>
            <p className="main-menu__eyebrow">Sistema de ventas</p>
            <h1>Girasol <em>Boutique</em></h1>
            <p className="main-menu__welcome">Todo tu negocio, en un solo lugar.</p>
          </div>
          <ClockWidget />
        </header>

        <section className="module-panel" aria-labelledby="modules-title">
          <div className="module-panel__heading">
            <div>
              <p>Accesos directos</p>
              <h2 id="modules-title">¿Qué deseas hacer?</h2>
            </div>
            <span>6 módulos</span>
          </div>
          <div className="module-grid">
            {modules.filter(module => !module.adminOnly || session?.is_admin).map((module) => (
              <MenuCard key={module.id} {...module} onClick={() => onNavigate(module.id)} />
            ))}
          </div>
        </section>

        <footer className="main-menu__footer">Girasol Boutique · Panel administrativo</footer>
      </main>
    </div>
  );
}
