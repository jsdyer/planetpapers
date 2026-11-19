import test from "node:test";
import assert from "node:assert/strict";
import {describe,groupSolutions,range} from "../web/model.mjs";
test("missing, one-sided bounds and asymmetric uncertainty remain distinct", () => {
  assert.equal(describe(null),"Not reported");
  assert.equal(describe([2,null,null,1]),"< 2 (upper limit)");
  assert.equal(describe([2,null,null,-1]),"> 2 (lower limit)");
  assert.equal(describe([16.17,.64,-.64,-1]),"> 16.17 ± 0.64 (lower limit)");
  assert.equal(describe([0.772,.079,-.075,0]),"0.772 +0.079 / −0.075");
  assert.equal(describe([.62,.58,-.58,0]),"0.62 ± 0.58");
});
test("identical same-paper estimates group, alternate solutions and other papers survive", () => {
  const a = [2,.2,-.1,0], b = [3,.2,-.1,0];
  const rows = [[0,"2009",0,a],[0,"2009",1,a],[0,"2009",0,b],[1,"2010",0,a]];
  const result = groupSolutions(rows,[["A","https://a"],["B","https://b"]],0);
  assert.equal(result.length,3);assert.equal(result[0].count,2);assert.ok(result[0].preferred);
  assert.ok(range(result)[1] > 3.2);
  assert.equal(range([{measure:null}]),null);
});
