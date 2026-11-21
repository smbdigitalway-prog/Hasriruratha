// Care log test, phone size: a volunteer logs watering for assigned trees and captures GPS for an
// imported tree; the public map then shows "watered today". Run seed_care.py with the bench Python first.
const { chromium, devices } = require('playwright');
const B = 'http://hr.localhost:8000', OUT = process.argv[2];
let fails = 0;
const ok = (c, w, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', w, d ? '| ' + d : ''); };
const overflow = p => p.evaluate(() => Math.max(document.documentElement.scrollWidth, innerWidth) - screen.width);

(async () => {
	const b = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const ctx = await b.newContext({ ...devices['iPhone 13'], geolocation: { latitude: 12.92507, longitude: 77.59391, accuracy: 6 }, permissions: ['geolocation'] });
	const p = await ctx.newPage();

	await p.goto(B + '/my-trees', { waitUntil: 'networkidle' });
	ok(p.url().includes('/volunteer-login'), 'Signed-out volunteer is sent to sign-in', p.url());
	await p.fill('#login-phone', '9555500001'); await p.fill('#login-pin', 'Water2026x'); await p.click('#login-btn');
	await p.waitForURL(/\/hasiruratha/, { timeout: 15000 }).catch(() => {});
	await p.waitForSelector('a[href="/my-trees"]', { timeout: 15000 }).catch(() => {});
	ok(await p.locator('a[href="/my-trees"]').count() >= 1, 'Volunteer app home links to "Log watering & care"');

	await p.goto(B + '/my-trees', { waitUntil: 'networkidle' }); await p.waitForTimeout(800);
	const n = await p.locator('input[data-tree]').count();
	ok(n === 2, 'My trees lists the assigned trees', n + ' trees');
	ok(await p.locator('text=Not watered yet').count() === 2, 'Trees show "Not watered yet"');
	ok(await overflow(p) <= 0, 'No sideways scroll on My trees');
	await p.screenshot({ path: `${OUT}/C1-my-trees.png` });

	// capture GPS for the imported tree
	await p.locator('[data-gps]').first().click();
	await p.waitForFunction(() => !document.querySelector('[data-gps]'), null, { timeout: 25000 }).catch(() => {});
	ok(await p.locator('[data-gps]').count() === 0, 'GPS captured for the tree that had none');

	// log watering for both
	await p.click('#sel-thirsty');
	ok(await p.locator('#panel:not(.hr-hidden)').count() === 1 && (await p.locator('#panel-title').innerText()).includes('2 trees'), 'Select "not watered for 3+ days" picks both');
	await p.fill('#hrs', '1');
	await p.screenshot({ path: `${OUT}/C2-log-panel.png` });
	await p.click('#save'); await p.waitForTimeout(1500);
	ok((await p.locator('#m').innerText()).includes('Saved for 2 trees'), 'Watering logged for 2 trees', await p.locator('#m').innerText());
	ok(await p.locator('text=Watered today').count() === 2, 'Trees now show "Watered today"');

	// someone else's tree is refused
	const r = await p.evaluate(() => fetch('/api/method/hasiruratha.care_api.log', { method: 'POST',
		headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': frappe.csrf_token },
		body: JSON.stringify({ trees: JSON.stringify(['HR-BAN-0001']), activity: 'Watering' }) }).then(r => r.status));
	ok(r === 403, 'Cannot log care for a tree that is not yours', 'HTTP ' + r);

	// public map shows it
	const g = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();
	await g.goto(B + '/trees?spot=S-JAY-001', { waitUntil: 'networkidle' }); await g.waitForTimeout(1500);
	ok((await g.locator('#sheetbody').innerText()).includes('today'), 'Public map shows "Watered today"');
	await g.screenshot({ path: `${OUT}/C3-public-watered.png` });

	console.log(fails ? fails + ' FAILED' : 'ALL PASSED');
	await b.close();
})();
