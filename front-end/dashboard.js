// frontend/dashboard.js
const API = '/api';

async function api(path, opts={}) {
  const res = await fetch(`${API}${path}`, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.message || 'API error');
  return json;
}

async function loadCustomers() {
  const list = await api('/customers');
  const custBody = document.getElementById('custBody');
  const custTable = document.getElementById('custTable');
  const noCust = document.getElementById('noCust');
  custBody.innerHTML = '';
  if (list.length === 0) {
    custTable.hidden = true;
    noCust.textContent = 'No customers yet.';
    return;
  }
  custTable.hidden = false;
  noCust.textContent = '';
  list.forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${c.account_no}</td>
      <td>${c.name}</td>
      <td>${c.email}</td>
      <td>${c.mobile}</td>
      <td>${c.type}</td>
      <td>${Number(c.balance).toFixed(2)}</td>
      <td>
        <button data-acc="${c.account_no}" class="deposit">Deposit</button>
        <button data-acc="${c.account_no}" class="withdraw">Withdraw</button>
        <button data-acc="${c.account_no}" class="delete">Delete</button>
      </td>
    `;
    custBody.appendChild(tr);
  });
}

document.getElementById('custBody').addEventListener('click', async (e) => {
  const btn = e.target;
  const acc = btn.getAttribute('data-acc');
  if (!acc) return;
  try {
    if (btn.classList.contains('deposit')) {
      const amount = prompt(`Deposit amount for ${acc}`);
      if (!amount) return;
      await api(`/customers/${acc}/deposit`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({amount: Number(amount)})
      });
      await loadCustomers();
    } else if (btn.classList.contains('withdraw')) {
      const amount = prompt(`Withdraw amount for ${acc}`);
      if (!amount) return;
      await api(`/customers/${acc}/withdraw`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({amount: Number(amount)})
      });
      await loadCustomers();
    } else if (btn.classList.contains('delete')) {
      if (!confirm('Delete this customer?')) return;
      await api(`/customers/${acc}`, {method:'DELETE'});
      await loadCustomers();
    }
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById('transferForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const transferMsg = document.getElementById('transferMsg');
  transferMsg.textContent = '';
  const from = document.getElementById('fromAcc').value.trim();
  const to = document.getElementById('toAcc').value.trim();
  const amount = Number(document.getElementById('amount').value.trim());
  if (!from || !to || !amount || amount <= 0) {
    transferMsg.textContent = 'Provide valid from/to accounts and positive amount';
    return;
  }
  try {
    await api('/transfer', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({from,to,amount})});
    transferMsg.style.color = 'green';
    transferMsg.textContent = `Transferred ₹${amount.toFixed(2)}`;
    document.getElementById('transferForm').reset();
    await loadCustomers();
    loadTxns();
  } catch (err) {
    transferMsg.style.color = 'var(--danger)';
    transferMsg.textContent = err.message;
  }
});

async function loadTxns() {
  try {
    const txns = await api('/transactions?limit=20');
    const el = document.getElementById('txnList');
    if (txns.length === 0) { el.textContent = 'No transactions yet.'; return; }
    el.innerHTML = '';
    txns.forEach(t => {
      const d = document.createElement('div');
      d.textContent = `${new Date(t.timestamp).toLocaleString()} — ${t.type.toUpperCase()} — ${t.details} — ₹${Number(t.amount).toFixed(2)}`;
      el.appendChild(d);
    });
  } catch (_) {}
}

async function init() {
  await loadCustomers();
  await loadTxns();
}
init();
