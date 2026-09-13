import {
  Boxes,
  Settings,
  CircleDollarSign,
  LogOut,
  Menu,
  Moon,
  PackagePlus,
  ShoppingBag,
  Sun,
  UsersRound,
} from 'lucide-react';

const links = [
  { id: 'menu', label: 'Menú principal', icon: Menu },
  { id: 'inventario', label: 'Inventario', icon: Boxes },
  { id: 'ventas', label: 'Ventas', icon: ShoppingBag },
  { id: 'configuracion', label: 'Configuración', icon: Settings, adminOnly: true },
  { id: 'clientes', label: 'Clientas', icon: UsersRound },
  { id: 'arqueo', label: 'Facturas y arqueo', icon: CircleDollarSign },
  { id: 'ingreso-mercaderia', label: 'Ingreso mercadería', icon: PackagePlus },
];

export function Sidebar({ active = 'menu', dark, session, onNavigate, onToggleTheme, onLogout }) {
  return (
    <aside className="sidebar" aria-label="Navegación principal">
      <div className="sidebar__brand" aria-label="Girasol Boutique">G</div>
      <button className="sidebar__theme" type="button" onClick={onToggleTheme} aria-label={`Activar modo ${dark ? 'claro' : 'oscuro'}`}>
        {dark ? <Sun size={21} /> : <Moon size={21} />}
      </button>

      <nav className="sidebar__nav">
        {links.filter(link => !link.adminOnly || session?.is_admin).map(({ id, label, icon: Icon }) => (
          <button
            className={`sidebar__link ${active === id ? 'is-active' : ''}`}
            type="button"
            key={id}
            onClick={() => onNavigate(id)}
            aria-label={label}
            title={label}
          >
            <Icon size={23} strokeWidth={2.2} />
            <span className="sidebar__tooltip">{label}</span>
          </button>
        ))}
      </nav>

      <button className="sidebar__logout" type="button" onClick={onLogout} aria-label="Cerrar sesión" title="Cerrar sesión">
        <LogOut size={23} />
      </button>
    </aside>
  );
}
