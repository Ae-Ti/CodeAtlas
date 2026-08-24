import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { BookOpen, Cpu, GitBranch, LayoutDashboard, Menu, Sparkles, X, UploadCloud, MessageCircle } from 'lucide-react';

const navItems = [
  { to: '/', end: true, icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/papers', end: false, icon: BookOpen, label: 'Papers' },
  { to: '/agent', end: false, icon: Sparkles, label: 'AI Agent' },
  { to: '/graph', end: false, icon: GitBranch, label: 'Graph' },
  { to: '/chat', end: false, icon: MessageCircle, label: 'Chat' },
  { to: '/upload', end: false, icon: UploadCloud, label: 'Upload' },
];

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="header">
      <div className="header-inner">
        <NavLink to="/" className="header-logo" onClick={() => setMenuOpen(false)}>
          <div className="header-logo-icon">
            <Cpu size={18} color="white" />
          </div>
          <span>Code<span className="gradient-text">Atlas</span></span>
        </NavLink>

        <nav className="header-nav">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => isActive ? 'active' : ''}>
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button
          className="header-menu-btn"
          onClick={() => setMenuOpen(o => !o)}
          aria-label={menuOpen ? '메뉴 닫기' : '메뉴 열기'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="header-nav-mobile">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setMenuOpen(false)}
            >
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}
