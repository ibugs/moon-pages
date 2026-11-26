const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../site/index.html'), 'utf8');
const source = html.slice(html.indexOf('const escape ='), html.indexOf('function monthly('));
const baseline = {date:'20261125', net_value:1, drawdown:0};
const firstDay = {date:'20261126', net_value:1.01, drawdown:0};
const secondDay = {date:'20261127', net_value:1.02, drawdown:0};
function render(curve, period = 'since_launch', launchDate = '20261126') {
  const strategy = {view:'all-pro', title:'TEST', launch_date:launchDate, equity_curve:curve};
  return vm.runInNewContext(source + '\nchart(strategy)', {strategy, period, innerWidth:390});
}
function annual(curve, period = 'since_launch') {
  return render(curve, period).match(/年化收益<strong[^>]*>(.*?)<\/strong>/)[1];
}
assert.equal(annual([baseline, firstDay]), '—');
assert.equal(annual([baseline, firstDay, {...firstDay, net_value:1.015}]), '—');
assert.notEqual(annual([baseline, firstDay, secondDay]), '—');
assert.notEqual(annual([baseline, firstDay], 'ytd'), '—');
const marked = render([baseline, firstDay, secondDay]);
assert.equal((marked.match(/class="launch-marker"/g) || []).length, 2);
assert.match(marked, /class="launch-marker" x1="352"/);
assert.doesNotMatch(marked, /class="launch-marker-label"/);
assert.match(marked, /stroke="#eb0029" stroke-width="1.5" stroke-dasharray="6 5"/);
assert.doesNotMatch(render([baseline, firstDay], '3y', '20261124'), /class="launch-marker"/);
assert.doesNotMatch(render([baseline, firstDay], '3y', '20261127'), /class="launch-marker"/);
const weekend = render([
  {date:'20260924',net_value:1,drawdown:0},
  {date:'20260928',net_value:1.01,drawdown:0},
], 'since_launch', '20260927');
assert.match(weekend, /class="launch-marker" x1="484"/);
console.log('PASS: launch-day annualization, exact-date markers, out-of-range dates and weekend interpolation');
