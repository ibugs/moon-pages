const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../site/index.html'), 'utf8');
const source = html.slice(html.indexOf('let contactScrollY='), html.indexOf('function updateToolbarOffset'));
const classes = new Set(), timers = new Map();
let onScroll, nextTimer = 0;
const window = {scrollY:0, addEventListener:(name, fn)=>{if(name==='scroll')onScroll=fn;}};
const context = {
  window,
  contactOpen:{classList:{add:name=>classes.add(name),remove:name=>classes.delete(name)}},
  clearTimeout:id=>timers.delete(id),
  setTimeout:(fn, delay)=>{assert.equal(delay,1000);timers.set(++nextTimer,fn);return nextTimer;},
};
vm.runInNewContext(source, context);
assert.equal(classes.size,0);
onScroll();
assert.equal(classes.size,0);
window.scrollY=200;onScroll();
assert.ok(classes.has('scroll-visible'));
window.scrollY=40;onScroll();
assert.ok(classes.has('scroll-visible'));
assert.equal(timers.size,1);
[...timers.values()][0]();
assert.equal(classes.size,0);
console.log('PASS: hidden while idle, shown for both scroll directions, hidden after scrolling stops');
