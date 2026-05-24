const state = {
  current: '0',
  previous: null,
  operator: null,
  waitingForOperand: false,
};

const currentEl = document.getElementById('current');
const historyEl = document.getElementById('history');

const opSymbol = { '+': '+', '-': '−', '*': '×', '/': '÷' };

function formatNumber(value) {
  if (value === 'Error') return value;
  const num = Number(value);
  if (!isFinite(num)) return 'Error';
  const str = String(value);
  if (str.length > 12) {
    return num.toPrecision(10).replace(/\.?0+($|e)/, '$1');
  }
  return str;
}

function render() {
  currentEl.textContent = formatNumber(state.current);
  if (state.previous !== null && state.operator) {
    historyEl.textContent = `${formatNumber(state.previous)} ${opSymbol[state.operator]}`;
  } else {
    historyEl.textContent = '';
  }
  document.querySelectorAll('.btn.op').forEach((b) => b.classList.remove('active'));
  if (state.operator && state.waitingForOperand) {
    const active = document.querySelector(`.btn.op[data-value="${state.operator}"]`);
    if (active) active.classList.add('active');
  }
}

function inputDigit(d) {
  if (state.current === 'Error') resetAll();
  if (state.waitingForOperand) {
    state.current = d;
    state.waitingForOperand = false;
  } else {
    state.current = state.current === '0' ? d : state.current + d;
  }
}

function inputDot() {
  if (state.current === 'Error') resetAll();
  if (state.waitingForOperand) {
    state.current = '0.';
    state.waitingForOperand = false;
    return;
  }
  if (!state.current.includes('.')) {
    state.current += '.';
  }
}

function resetAll() {
  state.current = '0';
  state.previous = null;
  state.operator = null;
  state.waitingForOperand = false;
}

function toggleSign() {
  if (state.current === '0' || state.current === 'Error') return;
  state.current = state.current.startsWith('-')
    ? state.current.slice(1)
    : '-' + state.current;
}

function percent() {
  if (state.current === 'Error') return;
  state.current = String(Number(state.current) / 100);
}

function compute(a, b, op) {
  switch (op) {
    case '+': return a + b;
    case '-': return a - b;
    case '*': return a * b;
    case '/': return b === 0 ? 'Error' : a / b;
  }
}

function handleOperator(nextOp) {
  if (state.current === 'Error') return;
  const inputValue = Number(state.current);

  if (state.previous === null) {
    state.previous = inputValue;
  } else if (state.operator && !state.waitingForOperand) {
    const result = compute(state.previous, inputValue, state.operator);
    state.current = String(result);
    state.previous = result === 'Error' ? null : result;
  }

  state.operator = nextOp;
  state.waitingForOperand = true;
}

function equals() {
  if (state.operator === null || state.previous === null) return;
  const inputValue = Number(state.current);
  const result = compute(state.previous, inputValue, state.operator);
  state.current = String(result);
  state.previous = null;
  state.operator = null;
  state.waitingForOperand = true;
}

document.querySelectorAll('.btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const action = btn.dataset.action;
    const value = btn.dataset.value;
    switch (action) {
      case 'num': inputDigit(value); break;
      case 'dot': inputDot(); break;
      case 'clear': resetAll(); break;
      case 'sign': toggleSign(); break;
      case 'percent': percent(); break;
      case 'op': handleOperator(value); break;
      case 'equals': equals(); break;
    }
    render();
  });
});

document.addEventListener('keydown', (e) => {
  if (e.key >= '0' && e.key <= '9') inputDigit(e.key);
  else if (e.key === '.' || e.key === ',') inputDot();
  else if (['+', '-', '*', '/'].includes(e.key)) handleOperator(e.key);
  else if (e.key === 'Enter' || e.key === '=') { e.preventDefault(); equals(); }
  else if (e.key === 'Escape') resetAll();
  else if (e.key === 'Backspace') {
    if (state.current === 'Error' || state.waitingForOperand) return;
    state.current = state.current.length > 1 ? state.current.slice(0, -1) : '0';
  } else if (e.key === '%') percent();
  else return;
  render();
});

render();
