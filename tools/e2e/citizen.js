// Phone-size end-to-end test of the citizen side on the local site.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const B = 'http://hr.localhost:8000';
const OUT = process.argv[2];
const MAIL = '/opt/mailcatch/mail';
const PHOTO = process.argv[3];
let fails = 0;
const ok = (cond, what, detail) => { if (!cond) fails++; console.log(cond ? 'PASS' : 'FAIL', '|', what, detail ? '| ' + detail : ''); };
const shot = (page, n) => page.screenshot({ path: `${OUT}/${n}.png` });
const overflow = page => page.evaluate(() => Math.max(document.documentElement.scrollWidth, window.innerWidth) - screen.width);
const near = { latitude: 12.92505, longitude: 77.59385, accuracy: 8 };    // ~6 m from the "Jayanagar 4th Block" spot

async function latestCode(email, after) {
	for (let i = 0; i < 40; i++) {
		const f = fs.readdirSync(MAIL).filter(x => x.includes(email) && +x.split('-')[0] > after).sort().pop();
		if (f) {
			const raw = fs.readFileSync(`${MAIL}/${f}`, 'utf8').replace(/=\r?\n/g, '');
			const m = raw.match(/>\s*(\d{6})\s*</) || raw.match(/code is[^0-9]{0,80}(\d{6})/);
			if (m) return m[1];
		}
		await new Promise(r => setTimeout(r, 250));
	}
	return null;
}

(async () => {
	const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const mk = (geo) => browser.newContext({ ...devices['iPhone 13'], geolocation: geo || near, permissions: ['geolocation'] });

	// ---------------- A. guest map ----------------
	let ctx = await mk(), page = await ctx.newPage();
	const apiBodies = [];
	page.on('response', async r => { if (r.url().includes('public_api')) apiBodies.push(await r.text().catch(() => '')); });
	await page.goto(B + '/trees?spot=S-JAY-001', { waitUntil: 'networkidle' });
	await page.waitForSelector('#sheet.open', { timeout: 8000 }).catch(() => {});
	await page.waitForTimeout(1500);
	ok(await page.locator('#sheet.open').count() === 1, 'A guest: /trees?spot=… opens the spot details (QR-style link)');
	ok((await page.locator('.leaflet-tile-loaded').count()) > 0, 'A guest: map tiles load');
	ok((await page.locator('#sheetbody').innerText()).includes('Neem'), 'A guest: spot shows tree type');
	await shot(page, 'A1-guest-spot');
	await page.click('#sheet .close');
	await page.goto(B + '/trees', { waitUntil: 'networkidle' }); await page.waitForTimeout(2000);
	await page.evaluate(() => {});                                     // default view is South Bengaluru
	const markers = await page.locator('.leaflet-marker-icon').count();
	ok(markers > 0, 'A guest: tree markers shown on the public map', markers + ' markers');
	ok(await overflow(page) <= 0, 'A guest: no sideways scroll on /trees');
	await shot(page, 'A2-guest-map');
	const leak = apiBodies.join(' ');
	ok(!/Test Volunteer|9845012345|owner_volunteer_id|phone|email/i.test(leak), 'A guest: no volunteer names, phones or emails in public data');
	await ctx.close();

	// ---------------- B. citizen sign-in with OTP ----------------
	ctx = await mk(); page = await ctx.newPage();
	const email = 'asha.' + Date.now() + '@example.com', mobile = '9' + String(Date.now()).slice(-9);
	await page.goto(B + '/request?type=new', { waitUntil: 'networkidle' });
	ok(page.url().includes('/citizen-login'), 'B: guest is sent to sign-in before a request', page.url());
	await page.fill('#mob', mobile); await page.fill('#eml', email); await page.click('#send');
	await page.waitForSelector('#namewrap:not(.hr-hidden)');
	ok(true, 'B: first time asks for a name');
	await page.fill('#nm', 'Asha Test');
	const t0 = Date.now() * 1e6;
	await page.click('#send');
	await page.waitForSelector('#step2:not(.hr-hidden)', { timeout: 10000 });
	await shot(page, 'B1-otp-sent');
	ok(await overflow(page) <= 0, 'B: no sideways scroll on sign-in');
	const code = await latestCode(email, t0);
	ok(!!code, 'B: 6-digit code arrives by email', code ? 'code received' : 'no email');
	await page.fill('#code', '000000'); await page.click('#verify'); await page.waitForTimeout(800);
	ok((await page.locator('#m2').innerText()).includes('not correct'), 'B: a wrong code is refused');
	await page.fill('#code', code); await page.click('#verify');
	await page.waitForURL(u => new URL(u).pathname === '/request', { timeout: 10000 }).catch(() => {});
	ok(page.url().includes('/request?type=new'), 'B: signed in and returned to the request page', page.url());

	// ---------------- B. new location request ----------------
	await page.waitForTimeout(800);
	ok(await page.locator('[data-type="New location"].on').count() === 1, 'B: "Plant a sapling" pre-selected from the link');
	await page.click('#gps');
	await page.waitForSelector('#nearcard:not(.hr-hidden)', { timeout: 15000 }).catch(() => {});
	await page.waitForTimeout(1500);
	ok((await page.locator('#gtext').innerText()).includes('8 m'), 'B: shows GPS accuracy', await page.locator('#gtext').innerText());
	ok((await page.locator('#nearlist .hr-item').count()) >= 1, 'B: shows the already-registered spot nearby');
	const road = await page.inputValue('#road'), area = await page.inputValue('#area'), pin = await page.inputValue('#pin');
	ok(road && area, 'B: road and area filled from the map', `${road} / ${area} / pin ${pin}`);
	if (!/^\d{6}$/.test(pin)) await page.fill('#pin', '560011');
	await shot(page, 'B2-new-request-nearby');
	await page.fill('#addr', '#12, 4th Cross, 9th Main');
	await page.click('#send'); await page.waitForTimeout(500);
	ok((await page.locator('#m').innerText()).includes('already registered right here'), 'B: cannot send until the citizen says whether it is the same spot');
	await page.click('#notlisted');
	await page.check('#consent');
	await page.setInputFiles('#photo', PHOTO);
	await page.waitForFunction(() => document.querySelector('#m').innerText.includes('Photo added'), null, { timeout: 15000 }).catch(() => {});
	const kb = (await page.locator('#m').innerText()).match(/(\d+) KB/);
	ok(kb && +kb[1] < 600, 'B: 1.5 MB phone photo shrunk before upload', kb ? kb[0] : 'no size');
	await page.click('#send');
	await page.waitForSelector('#done:not(.hr-hidden)', { timeout: 15000 }).catch(() => {});
	ok(await page.locator('#done:not(.hr-hidden)').count() === 1, 'B: new-location request sent', await page.locator('#dname').innerText().catch(() => ''));
	ok((await page.locator('#dnote').innerText()).includes('very close'), 'B: told it will be checked as a possible duplicate');
	await shot(page, 'B3-request-sent');

	// ---------------- B. maintenance request ----------------
	await page.goto(B + '/request?type=maintenance', { waitUntil: 'networkidle' });
	await page.click('#gps');
	await page.waitForSelector('#nearlist .hr-item', { timeout: 15000 }).catch(() => {});
	ok((await page.locator('#neartitle').innerText()).includes('Which tree'), 'B: maintenance asks which tree');
	await page.locator('#nearlist .hr-item').first().click();
	await page.selectOption('#issue', 'Watering');
	await page.click('#send'); await page.waitForTimeout(400);
	ok((await page.locator('#m').innerText()).includes('photo'), 'B: maintenance needs a photo');
	await page.setInputFiles('#photo', PHOTO);
	await page.waitForFunction(() => document.querySelector('#m').innerText.includes('Photo added'), null, { timeout: 15000 }).catch(() => {});
	if (!/^\d{6}$/.test(await page.inputValue('#pin'))) await page.fill('#pin', '560011');
	await page.check('#consent');
	await shot(page, 'B4-maintenance-form');
	await page.click('#send');
	await page.waitForSelector('#done:not(.hr-hidden)', { timeout: 15000 }).catch(() => {});
	ok(await page.locator('#done:not(.hr-hidden)').count() === 1, 'B: maintenance request sent');
	ok(await overflow(page) <= 0, 'B: no sideways scroll on /request');

	// ---------------- B. pin away from the spot ----------------
	await page.goto(B + '/request?type=new', { waitUntil: 'networkidle' });
	await page.locator('#map').scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
	const box = await page.locator('#map').boundingBox();
	await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.6);
	await page.waitForTimeout(2500);
	ok((await page.locator('#gtext').innerText()).includes('Pin placed'), 'B: can place a pin without being there');
	ok((await page.inputValue('#area')).length > 0, 'B: address resolved for the pin', await page.inputValue('#area'));

	await page.goto(B + '/my-requests', { waitUntil: 'networkidle' }); await page.waitForTimeout(800);
	const cards = await page.locator('#list .hr-card').count();
	ok(cards === 2, 'B: My requests lists both requests', cards + ' shown');
	await shot(page, 'B5-my-requests');
	ok(await overflow(page) <= 0, 'B: no sideways scroll on My requests');

	// ---------------- B. stays signed in ----------------
	const cookies = (await ctx.cookies()).filter(c => c.name !== 'sid');
	ok(cookies.some(c => c.name === 'hr_device'), 'B: "keep me signed in" cookie set');
	const ctx2 = await mk(); await ctx2.addCookies(cookies);
	const p2 = await ctx2.newPage();
	await p2.goto(B + '/my-requests', { waitUntil: 'networkidle' });
	await p2.waitForURL(/my-requests$/, { timeout: 8000 }).catch(() => {});
	ok(p2.url().endsWith('/my-requests'), 'B: after the session ends the phone signs in again without a code', p2.url());
	await ctx2.close(); await ctx.close();

	console.log(fails ? `\n${fails} FAILED` : '\nALL PASSED');
	await browser.close();
})();
