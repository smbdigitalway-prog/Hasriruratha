// Access messages, phone size: visitors and signed-in citizens who open volunteer or admin pages get a
// clear "sign in / register" message instead of Frappe's "Not Permitted", and return to the page after
// signing in. Needs seed_care.py (volunteer 9555500001 and a plain citizen account).
const { chromium, devices } = require('playwright');
const B = 'http://hr.localhost:8000', OUT = process.argv[2];
let fails = 0;
const ok = (c, w, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', w, d ? '| ' + d : ''); };
const text = p => p.evaluate(() => document.body.innerText);

(async () => {
	const b = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	// visitor
	const g = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();
	await g.goto(B + '/gps-tagging', { waitUntil: 'networkidle' });
	ok(g.url().includes('/volunteer-login?redirect-to=%2Fgps-tagging'), 'Visitor on a volunteer page is sent to sign-in', g.url());
	ok((await text(g)).includes('Please sign in to open that page'), 'Sign-in page says why');
	ok(await g.locator('a[href="/volunteer-signup"]').count() >= 1, 'Sign-in page offers volunteer registration');
	await g.screenshot({ path: `${OUT}/A1-visitor.png` });
	await g.fill('#login-phone', '9555500001'); await g.fill('#login-pin', 'Water2026x'); await g.click('#login-btn');
	await g.waitForURL(/\/gps-tagging/, { timeout: 15000 }).catch(() => {});
	ok(g.url().endsWith('/gps-tagging'), 'After signing in the volunteer is back on the page they wanted', g.url());
	await g.goto(B + '/desk', { waitUntil: 'networkidle' });
	const vt = await text(g);
	if (!vt.includes('Not Permitted')) ok(g.url().includes('/sign-in-needed') ? vt.includes('This area is for admins') : true, 'A volunteer opening the admin area is pointed to the field app', g.url());
	else ok(false, 'A volunteer opening the admin area is pointed to the field app', 'Not Permitted');

	// signed-in citizen
	const c = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();
	ok((await c.request.post(B + '/api/method/login', { data: { usr: 'probe.citizen@example.com', pwd: 'Citizen2026x' } })).ok(), 'Citizen signs in');
	for (const [u, head] of [['/desk', 'This area is for the Hasiru Ratha team'], ['/app/hr-tree', 'This area is for the Hasiru Ratha team'],
		['/my-trees', 'Please register as a volunteer'], ['/hasiruratha', 'Please register as a volunteer']]) {
		await c.goto(B + u, { waitUntil: 'networkidle' });
		const t = await text(c);
		ok(c.url().includes('/sign-in-needed') && t.includes(head) && !t.includes('Not Permitted'), 'Citizen opening ' + u + ' sees: ' + head, c.url());
	}
	ok(await c.locator('#actions a[href="/volunteer-signup"]').count() === 1, 'Citizen is offered volunteer registration');
	ok(await c.locator('#actions a[href="/my-requests"]').count() === 1, 'Citizen can go to their requests');
	ok(await c.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No sideways scroll');
	await c.screenshot({ path: `${OUT}/A2-citizen.png` });
	await c.click('#switch'); await c.waitForURL(/volunteer-login/, { timeout: 15000 }).catch(() => {});
	ok(c.url().includes('/volunteer-login'), '"Sign out and sign in again" goes to volunteer sign-in', c.url());

	console.log(fails ? fails + ' FAILED' : 'ALL PASSED');
	await b.close();
})();
