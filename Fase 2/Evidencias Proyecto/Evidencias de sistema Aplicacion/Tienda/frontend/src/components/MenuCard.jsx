import { motion } from 'framer-motion';

export function MenuCard({ title, description, icon, onClick }) {
  return (
    <motion.button
      className="menu-card"
      type="button"
      onClick={onClick}
      whileHover={{ y: -8, scale: 1.035 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: 'spring', stiffness: 320, damping: 22 }}
      aria-label={`Abrir ${title}`}
    >
      <span className="menu-card__icon-wrap">
        <img className="menu-card__icon" src={icon} alt="" />
      </span>
      <span className="menu-card__copy">
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
      <span className="menu-card__arrow" aria-hidden="true">→</span>
    </motion.button>
  );
}
