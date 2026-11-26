const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../site/index.html'), 'utf8');
const source = html.slice(html.indexOf('const escape ='), html.indexOf('function monthly('));
const baseline = {date:'20261125', net_value:1, drawdown:0};
const firstDay = {date:'20261126', net_value:1.01, drawdown:0};
const secondDay = {date:'20261127', net_value:1.02, drawdown:0};
function annual(curve, period = 'since_launch') {
  const strategy = {view:'all-pro', title:'TEST', launch_date:'20261126', equity_curve:curve};
  const chart = vm.runInNewContext(source + '\nchart(strategy)', {strategy, period, innerWidth:390});
  return chart.match(/年化收益<strong[^>]*>(.*?)<\/strong>/)[1];
}
assert.equal(annual([baseline, firstDay]), '—');
assert.equal(annual([baseline, firstDay, {...firstDay, net_value:1.015}]), '—');
assert.notEqual(annual([baseline, firstDay, secondDay]), '—');
assert.notEqual(annual([baseline, firstDay], 'ytd'), '—');
console.log('PASS: first launch day and duplicate dates hide annualization; later launch days and existing ranges retain it');
