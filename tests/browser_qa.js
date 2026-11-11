await page.setViewportSize({width: 1366, height: 900});
await page.goto("http://127.0.0.1:8010", {waitUntil: "networkidle"});
await page.waitForFunction(() => document.querySelector("#soil").textContent !== "--");
assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
assert.equal(await page.evaluate(() => !!Chart.getChart(document.querySelector("canvas"))), true);
return await page.screenshot({fullPage: true});
