const API = window.location.port === '5500' ? 'http://127.0.0.1:8000/api' : '/api';
const state = {
  product: null,
  cart: JSON.parse(localStorage.getItem('puja-cart') || '[]'),
  session: JSON.parse(localStorage.getItem('puja-session') || 'null')
};
const cartCount = document.querySelector('#cart-count');
const toast = document.querySelector('.cart-toast');
const money = (value) => `₹${Math.round(value)}`;
const saveCart = () => { localStorage.setItem('puja-cart', JSON.stringify(state.cart)); updateCartCount(); };
const updateCartCount = () => { cartCount.textContent = state.cart.reduce((sum, item) => sum + item.quantity, 0); };
function notify(message) { toast.firstChild.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 2200); }

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (state.session?.token) headers.Authorization = `Bearer ${state.session.token}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Something went wrong');
  return data;
}

function panel(title, content) {
  document.querySelector('.commerce-panel')?.remove();
  const element = document.createElement('section');
  element.className = 'commerce-panel';
  element.innerHTML = `<div class="commerce-sheet"><button class="panel-close" aria-label="Close">×</button><p class="eyebrow">Sri Puja Mart</p><h2>${title}</h2><div class="panel-content">${content}</div></div>`;
  document.body.append(element);
  element.addEventListener('click', (event) => { if (event.target === element || event.target.closest('.panel-close')) element.remove(); });
  return element;
}

function authButton() {
  const actions = document.querySelector('.header-actions');
  let button = actions.querySelector('.account-button');
  if (!button) { button = document.createElement('button'); button.className = 'account-button'; actions.prepend(button); button.addEventListener('click', () => state.session ? showAccount() : showLogin()); }
  button.textContent = state.session ? (state.session.role === 'admin' ? 'Admin' : 'Account') : 'Login';
}
function errorText(form, message) { form.querySelector('.form-error').textContent = message; }

function showLogin() {
  const element = panel('Welcome back', `<form class="commerce-form" data-form="login"><label>Email or admin username<input name="email" autocomplete="username" required></label><label>Password<input name="password" type="password" autocomplete="current-password" required></label><p class="form-error"></p><button class="button button-dark">Login <span>→</span></button><button class="text-link form-switch" type="button">Create a customer account</button></form>`);
  element.querySelector('.form-switch').onclick = showRegister;
}
function showRegister() {
  const element = panel('Create your account', `<form class="commerce-form" data-form="register"><label>Full name<input name="full_name" required></label><label>Email<input name="email" type="email" required></label><label>Phone<input name="phone" required></label><label>Delivery address<textarea name="address" required></textarea></label><label>Password <small>8 characters minimum</small><input name="password" type="password" minlength="8" required></label><p class="form-error"></p><button class="button button-dark">Create account <span>→</span></button><button class="text-link form-switch" type="button">Already have an account?</button></form>`);
  element.querySelector('.form-switch').onclick = showLogin;
}
function showVerify(email, code) {
  panel('Verify your account', `<p class="panel-note">Enter the verification code sent to <strong>${email}</strong>.</p><p class="dev-code">Local test code: <strong>${code}</strong></p><form class="commerce-form" data-form="verify"><input name="email" type="hidden" value="${email}"><label>Verification code<input name="code" inputmode="numeric" required></label><p class="form-error"></p><button class="button button-dark">Verify account <span>✓</span></button></form>`);
}
function showAccount() {
  if (state.session.role === 'admin') return showAdmin();
  const element = panel('Your account', `<div class="account-menu"><button class="button button-dark" data-action="orders">My orders <span>→</span></button><button class="button button-light" data-action="logout">Log out <span>↗</span></button></div>`);
  element.onclick = (event) => { if (event.target.dataset.action === 'orders') showOrders(); if (event.target.dataset.action === 'logout') logout(element); };
}
function logout(element) { localStorage.removeItem('puja-session'); state.session = null; authButton(); element.remove(); notify('You are logged out'); }

async function showOrders() {
  try { const orders = await request('/orders'); const content = orders.length ? orders.map((order) => `<article class="order-card"><div><strong>Order #${order.id}</strong><small>${new Date(order.created_at).toLocaleDateString()}</small></div><span class="status-pill">${order.status}</span><strong>${money(order.total)}</strong><small>${order.items.map((item) => `${item.name} × ${item.quantity}`).join(', ')}</small></article>`).join('') : '<p class="panel-note">No orders yet.</p>'; panel('Your orders', `<div class="order-list">${content}</div>`); } catch (error) { notify(error.message); }
}
function showCart() {
  if (!state.cart.length) return panel('Your cart', '<p class="panel-note">Your cart is waiting for something auspicious.</p><a class="button button-dark" href="#shop">Browse the kit <span>→</span></a>');
  const total = state.cart.reduce((sum, item) => sum + item.quantity * item.price, 0);
  const element = panel('Your cart', `<div class="cart-lines">${state.cart.map((item) => `<div class="cart-line"><div><strong>${item.name}</strong><small>${money(item.price)} each</small></div><div class="quantity"><button data-quantity="-" data-id="${item.id}">−</button><span>${item.quantity}</span><button data-quantity="+" data-id="${item.id}">+</button></div></div>`).join('')}</div><div class="cart-total"><span>Total</span><strong>${money(total)}</strong></div><button class="button button-dark checkout-button">Continue to checkout <span>→</span></button>`);
  element.onclick = (event) => { const id = Number(event.target.dataset.id); if (event.target.dataset.quantity) { const item = state.cart.find((line) => line.id === id); item.quantity += event.target.dataset.quantity === '+' ? 1 : -1; if (item.quantity < 1) state.cart = state.cart.filter((line) => line.id !== id); saveCart(); showCart(); } if (event.target.closest('.checkout-button')) showCheckout(); };
}
function showCheckout() {
  if (!state.session) return showLogin();
  const total = state.cart.reduce((sum, item) => sum + item.quantity * item.price, 0);
  const element = panel('Place your order', `<p class="panel-note">Online payment only · Total due <strong>${money(total)}</strong></p><form class="commerce-form" data-form="checkout"><label>Recipient name<input name="shipping_name" required></label><label>Phone<input name="shipping_phone" required></label><label>Delivery address<textarea name="shipping_address" required></textarea></label><p class="form-error"></p><button class="button button-dark">Continue to online payment <span>→</span></button></form>`);
  element.querySelector('[data-form="checkout"]').onsubmit = async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.target)); try { const order = await request('/orders', { method: 'POST', body: JSON.stringify({ ...values, items: state.cart.map((item) => ({ product_id: item.id, quantity: item.quantity })) }) }); showPayment(order); } catch (error) { errorText(event.target, error.message); } };
}
function showPayment(order) {
  const element = panel(`Pay order #${order.id}`, `<p class="panel-note">Card or UPI only · Total due <strong>${money(order.total)}</strong></p><div class="payment-tabs"><button class="active" data-method="card">Card</button><button data-method="upi">UPI</button></div><form class="commerce-form" data-form="payment"><input type="hidden" name="payment_method" value="card"><label class="card-field">Card number<input name="card_number" inputmode="numeric" minlength="12" maxlength="19" required></label><label class="upi-field is-hidden">UPI ID<input name="upi_id" placeholder="name@bank"></label><p class="form-error"></p><p class="secure-note">Payment details are not stored by this store.</p><button class="button button-dark">Pay ${money(order.total)} <span>↗</span></button></form>`);
  element.querySelectorAll('[data-method]').forEach((tab) => tab.onclick = () => { element.querySelectorAll('[data-method]').forEach((item) => item.classList.remove('active')); tab.classList.add('active'); const upi = tab.dataset.method === 'upi'; element.querySelector('[name="payment_method"]').value = tab.dataset.method; element.querySelector('.card-field').classList.toggle('is-hidden', upi); element.querySelector('.upi-field').classList.toggle('is-hidden', !upi); element.querySelector('[name="card_number"]').required = !upi; element.querySelector('[name="upi_id"]').required = upi; });
  element.querySelector('[data-form="payment"]').onsubmit = async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.target)); const reference = values.payment_method === 'card' ? `card-${values.card_number.replace(/\D/g, '').slice(-4)}` : values.upi_id; try { await request(`/orders/${order.id}/pay`, { method: 'POST', body: JSON.stringify({ payment_method: values.payment_method, payment_reference: reference }) }); state.cart = []; saveCart(); element.remove(); notify('Payment received. Order confirmed.'); } catch (error) { errorText(event.target, error.message); } };
}
async function showAdmin() {
  try { const orders = await request('/orders'); const content = orders.length ? orders.map((order) => `<article class="admin-order"><div><strong>#${order.id} · ${order.shipping_name}</strong><small>${order.shipping_phone} · ${order.shipping_address}</small></div><strong>${money(order.total)}</strong><select data-order="${order.id}"><option selected>${order.status}</option><option>processing</option><option>shipped</option><option>delivered</option><option>cancelled</option></select></article>`).join('') : '<p class="panel-note">No orders have been placed.</p>'; const element = panel('Admin · All orders', `<div class="admin-toolbar"><span>${orders.length} total orders</span><button class="button button-light" data-action="logout">Log out <span>↗</span></button></div><div class="admin-list">${content}</div>`); element.onchange = async (event) => { if (!event.target.dataset.order) return; try { await request(`/admin/orders/${event.target.dataset.order}`, { method: 'PATCH', body: JSON.stringify({ status: event.target.value }) }); notify('Order status updated'); } catch (error) { notify(error.message); } }; element.onclick = (event) => { if (event.target.dataset.action === 'logout') logout(element); }; } catch (error) { notify(error.message); }
}

async function loadProduct() {
  try { const products = await request('/products'); const product = products.find((item) => item.featured) || products[0]; state.product = product; document.querySelector('#product-name').textContent = product.name; document.querySelector('#product-description').textContent = product.description; document.querySelector('#item-count').textContent = product.items.length; document.querySelector('#product-price').textContent = money(product.price); document.querySelector('#product-stock').innerHTML = `<span></span> In stock · ${product.stock} available`; document.querySelector('#item-summary').textContent = product.items.slice(0, 4).map((item) => item.name).join(', '); document.querySelector('.add-to-cart').onclick = () => { const existing = state.cart.find((item) => item.id === product.id); if (existing) existing.quantity += 1; else state.cart.push({ id: product.id, name: product.name, price: product.price, quantity: 1 }); saveCart(); notify('Kit added to your cart'); }; } catch (error) { notify('Product service unavailable'); }
}

document.querySelector('.cart-button').onclick = showCart;
document.querySelector('.main-nav').insertAdjacentHTML('beforeend', '<a href="#account" data-account-link>Account</a>');
document.querySelector('[data-account-link]').onclick = (event) => { event.preventDefault(); state.session ? showAccount() : showLogin(); };
document.querySelector('.menu-toggle').onclick = () => { const nav = document.querySelector('.main-nav'); const open = nav.classList.toggle('open'); document.querySelector('.menu-toggle').setAttribute('aria-expanded', String(open)); };
authButton(); updateCartCount(); loadProduct();

document.addEventListener('submit', async (event) => {
  const form = event.target; if (!['login', 'register', 'verify'].includes(form.dataset.form)) return; event.preventDefault(); const values = Object.fromEntries(new FormData(form));
  try { if (form.dataset.form === 'register') { const result = await request('/auth/register', { method: 'POST', body: JSON.stringify(values) }); showVerify(values.email, result.verification_code); } if (form.dataset.form === 'verify') { await request('/auth/verify', { method: 'POST', body: JSON.stringify(values) }); showLogin(); notify('Account verified. Log in to continue.'); } if (form.dataset.form === 'login') { state.session = await request('/auth/login', { method: 'POST', body: JSON.stringify(values) }); localStorage.setItem('puja-session', JSON.stringify(state.session)); authButton(); document.querySelector('.commerce-panel')?.remove(); notify(`Welcome, ${state.session.name}`); } } catch (error) { errorText(form, error.message); }
});
