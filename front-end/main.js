// frontend/main.js
const API = '/api'; // assumed backend serves under same origin at /api

document.getElementById('regForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('msg');
  msg.textContent = '';
  const name = document.getElementById('name').value.trim();
  const email = document.getElementById('email').value.trim();
  const mobile = document.getElementById('mobile').value.trim();
  const pin = document.getElementById('pin').value.trim();
  const acctType = document.getElementById('acctType').value;

  // client-side validation
  if (!/^\S+@gmail\.com$/i.test(email)) { msg.textContent = 'Email must end with @gmail.com'; return; }
  if (!/^[6789]\d{9}$/.test(mobile)) { msg.textContent = 'Mobile must start with 6/7/8/9 and be 10 digits'; return; }
  if (!/^\d{4}$/.test(pin)) { msg.textContent = 'PIN must be exactly 4 digits'; return; }
  if (!acctType) { msg.textContent = 'Choose account type'; return; }

  try {
    document.getElementById('addBtn').disabled = true;
    const res = await fetch(`${API}/customers`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name,email,mobile,pin,type:acctType})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Server error');
    msg.style.color = 'green';
    msg.textContent = `Customer created. Account: ${data.account_no}`;
    e.target.reset();
  } catch (err) {
    msg.style.color = 'var(--danger)';
    msg.textContent = err.message;
  } finally {
    document.getElementById('addBtn').disabled = false;
  }
});
