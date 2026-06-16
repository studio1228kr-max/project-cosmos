import axios from 'axios';

const API = axios.create({ baseURL: 'https://project-cosmos-production.up.railway.app' });

API.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default API;

export async function getAmbient() {
  const token = localStorage.getItem('token');
  const res = await fetch('https://project-cosmos-production.up.railway.app/ambient', {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('ambient fetch failed');
  return res.json();
}
