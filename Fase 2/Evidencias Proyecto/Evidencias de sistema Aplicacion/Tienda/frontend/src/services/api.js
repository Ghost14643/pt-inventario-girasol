import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8765';

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 10000 });
api.interceptors.request.use(config => {
  try {
    const session = JSON.parse(localStorage.getItem('girasol:session'));
    if (session?.token) config.headers.Authorization = `Bearer ${session.token}`;
  } catch { /* sesión inexistente o inválida */ }
  return config;
});

export const authService = { login: (rut, password) => api.post('/auth/login', { rut, password }).then(r => r.data), logout: () => api.post('/auth/logout') };
export const inventoryService = {

  list: (search = '', marca = '') => api.get('/inventory', { params: { search, marca } }).then(r => r.data),
  summary: (stockLowMax = 5) => api.get('/inventory/summary', { params: { stock_bajo_maximo: stockLowMax } }).then(r => r.data),
  categories: () => api.get('/inventory/categories').then(r => r.data),
  byBarcode: barcode => api.get(`/inventory/barcode/${barcode}`).then(r => r.data),
  create: payload => api.post('/inventory', payload).then(r => r.data),

};

export const salesService = { create: payload => api.post('/sales', payload).then(r => r.data) };
export const scannerWsUrl = () => API_BASE_URL.replace(/^http/, 'ws') + '/ws/scanner';

export const cashService = {
  status: fecha => api.get(`/cash-register/status/${fecha}`).then(r => r.data),
  open: fecha => api.post('/cash-register/open', { fecha }).then(r => r.data),
  get: fecha => api.get(`/cash-register/${fecha}`).then(r => r.data),
  close: payload => api.post('/cash-register/close', payload).then(r => r.data),
};

export const clientService = { list: (search = '') => api.get('/clients', { params: { search } }).then(r => r.data), summary: () => api.get('/clients/summary').then(r => r.data), create: payload => api.post('/clients', payload).then(r => r.data), credit: rut => api.get(`/clients/${rut}/credit`).then(r => r.data), creditSearch: search => api.get('/clients/credit-search', { params: { search } }).then(r => r.data) };

export const brandService = { list: () => api.get('/brands').then(r => r.data), create: nombre => api.post('/brands', { nombre }).then(r => r.data) };


export const adminService = {
  summary: () => api.get('/admin/summary').then(r => r.data),
  users: () => api.get('/admin/users').then(r => r.data),
  roles: () => api.get('/admin/roles').then(r => r.data),
  createEmployee: payload => api.post('/admin/users', payload).then(r => r.data),
  deleteEmployee: rut => api.delete(`/admin/users/${rut}`).then(r => r.data),
  updateRole: (rut, id_rol) => api.patch(`/admin/users/${rut}/role`, { id_rol }).then(r => r.data),
  updatePassword: (rut, nueva_clave) => api.patch(`/admin/users/${rut}/password`, { nueva_clave }).then(r => r.data),
  discounts: () => api.get('/admin/discounts').then(r => r.data),
  createDiscount: (tipo, valor) => api.post('/admin/discounts', { tipo, valor }).then(r => r.data),
  saveDiscount: (id, tipo, valor) => api.put(`/admin/discounts/${id}`, { tipo, valor }).then(r => r.data),
};
