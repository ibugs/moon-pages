const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../site/index.html'), 'utf8');
const resizeSource = html.slice(html.indexOf('let resizeTimer'), html.lastIndexOf('\nrefresh();'));
let onResize, pending, renders = 0;
const resizeContext = {
  innerWidth:390, innerHeight:844, snapshot:'loaded',
  window:{addEventListener:(name, fn)=>{if(name==='resize')onResize=fn;}},
  clearTimeout:()=>{pending=null;}, setTimeout:fn=>{pending=fn;return 1;},
  showPeriod:()=>{renders++;},
};
vm.runInNewContext(resizeSource, resizeContext);
resizeContext.innerHeight=784;onResize();
assert.equal(pending,undefined);
assert.equal(resizeContext.snapshot,'loaded');
resizeContext.innerWidth=844;onResize();
assert.equal(typeof pending,'function');pending();
assert.equal(renders,1);

const renderSource = html.slice(html.indexOf('function render(payload)'), html.indexOf('function showPeriod()'));
let hasContent=true, scrollTop=1504, anchorJumps=0;
const content = {querySelector:()=>hasContent?{}:null};
Object.defineProperty(content,'innerHTML',{set:()=>{scrollTop=0;}});
const renderContext = {
  content, snapshot:'', location:{hash:'#all-pro'},
  window:{get scrollY(){return scrollTop;},scrollTo:({top})=>{scrollTop=top;}},
  document:{querySelectorAll:()=>[],querySelector:()=>({hash:'#all-pro'}),
    getElementById:()=>({scrollIntoView:()=>{anchorJumps++;}})},
};
vm.runInNewContext(renderSource, renderContext);
vm.runInNewContext('render({strategies:[]})',renderContext);
assert.equal(scrollTop,1504);
assert.equal(anchorJumps,0);
hasContent=false;
vm.runInNewContext('render({strategies:[]})',renderContext);
assert.equal(anchorJumps,1);
console.log('PASS: height-only resize skips redraw; updates retain scroll position; initial deep links still work');
