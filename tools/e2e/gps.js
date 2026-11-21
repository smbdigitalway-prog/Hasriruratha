// GPS tagging test, phone size: an admin tags an imported tree (GPS pending) on /gps-tagging, assigns
// another to the care volunteer, and the volunteer then sees only that tree. Needs the watering-sheet
// import and seed_care.py (volunteer 9555500001) on the local site.
const { chromium, devices } = require('playwright');
const B = 'http://hr.localhost:8000', OUT = process.argv[2];
let fails = 0;
const ok = (c, w, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', w, d ? '| ' + d : ''); };
const overflow = p => p.evaluate(() => Math.max(document.documentElement.scrollWidth, innerWidth) - screen.width);
const phone = { ...devices['iPhone 13'], geolocation: { latitude: 12.9301, longitude: 77.5832, accuracy: 7 }, permissions: ['geolocation'] };
const api = (p, m, args) => p.evaluate(([m, args]) => fetch('/api/method/' + m, { method: 'POST',
	headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Frappe-CSRF-Token': frappe.csrf_token },
	body: JSON.stringify(args) }).then(r => r.json()), [m, args]);

(async () => {
	const b = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const g = await (await b.newContext(phone)).newPage();
	await g.goto(B + '/gps-tagging', { waitUntil: 'networkidle' });
	ok(g.url().includes('/volunteer-login'), 'Signed-out visitor is sent to sign-in', g.url());

	// admin
	const a = await (await b.newContext(phone)).newPage();
	ok((await a.request.post(B + '/api/method/login', { data: { usr: 'boss@example.com', pwd: 'Admin2026pass' } })).ok(), 'Admin signs in');
	await a.goto(B + '/gps-tagging', { waitUntil: 'networkidle' }); await a.waitForTimeout(800);
	const sub = await a.locator('#sub').innerText();
	ok(/\d+ trees have GPS, \d+ still waiting/.test(sub), 'Admin sees overall progress', sub);
	await a.selectOption('#area', 'Hanumanth Nagar'); await a.waitForTimeout(300);
	const rows = await a.locator('[data-tag]').count();
	ok(rows >= 15, 'Area filter shows the Hanumanth Nagar saplings', rows + ' saplings');
	ok((await a.locator('#list').innerText()).includes('Subhash leadership'), 'Saplings are grouped under their spot');
	ok((await a.locator('#list').innerText()).includes('of 15'), 'Each sapling shows its place in the stretch');
	ok(await overflow(a) <= 0, 'No sideways scroll on GPS tagging');
	await a.screenshot({ path: `${OUT}/G1-admin-list.png` });
	const first = await a.locator('[data-tag]').first().getAttribute('data-tag');
	await a.locator('[data-tag]').first().click();
	await a.waitForSelector('#m:not(.hr-hidden)', { timeout: 20000 }).catch(() => {});
	ok((await a.locator('#m').innerText()).includes('Tagged ' + first), 'Admin tags a sapling', await a.locator('#m').innerText());
	ok((await a.locator('.hr-done').count()) === 1, 'The sapling shows ✓ Tagged');
	await a.screenshot({ path: `${OUT}/G2-admin-tagged.png` });
	const t = (await api(a, 'frappe.client.get_value', { doctype: 'HR Tree', filters: first, fieldname: ['gps_status', 'gps_lat'] })).message;
	ok(t.gps_status === 'Captured' && Math.abs(t.gps_lat - 12.9301) < 1e-4, 'Tree is saved with GPS captured', JSON.stringify(t));

	// admin assigns another pending tree to the care volunteer
	const vol = (await api(a, 'frappe.client.get_value', { doctype: 'HR Volunteer', filters: { phone: '9555500001' }, fieldname: 'name' })).message.name;
	const second = await a.locator('[data-tag]').first().getAttribute('data-tag');
	await api(a, 'frappe.client.set_value', { doctype: 'HR Tree', name: second, fieldname: 'owner_volunteer_id', value: vol });

	// volunteer
	const v = await (await b.newContext(phone)).newPage();
	await v.goto(B + '/volunteer-login', { waitUntil: 'networkidle' });
	await v.fill('#login-phone', '9555500001'); await v.fill('#login-pin', 'Water2026x'); await v.click('#login-btn');
	await v.waitForURL(/\/hasiruratha/, { timeout: 15000 }).catch(() => {});
	await v.goto(B + '/gps-tagging', { waitUntil: 'networkidle' }); await v.waitForTimeout(800);
	const mine = await v.locator('[data-tag]').evaluateAll(x => x.map(e => e.dataset.tag));
	ok(mine.includes(second) && !mine.includes(first), 'Volunteer sees the tree assigned to them', mine.join(', '));
	const r = await api(v, 'hasiruratha.care_api.set_gps', { tree: 'HR-BAN-0001', lat: 12.93, lng: 77.58, accuracy: 5 });
	ok(!!r.exc_type, 'Volunteer cannot tag a tree that is not theirs', r.exc_type);
	await v.locator(`[data-tag="${second}"]`).click();
	await v.waitForSelector('#m:not(.hr-hidden)', { timeout: 20000 }).catch(() => {});
	const msg = await v.locator('#m').innerText();
	ok(msg.includes('Tagged ' + second), 'Volunteer tags their tree', msg);
	ok(!msg.includes('m away'), 'Saplings of the same stretch are not flagged as duplicates of each other', msg);
	await v.screenshot({ path: `${OUT}/G3-volunteer-tagged.png` });

	console.log(fails ? fails + ' FAILED' : 'ALL PASSED');
	await b.close();
})();
