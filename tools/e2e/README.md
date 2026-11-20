# Phone-size end-to-end tests (citizen + volunteer)

They drive a local site at `http://hr.localhost:8000` in an iPhone 13 sized browser (Playwright).

Setup once:
1. A local bench with the app and demo data (`bench --site hr.localhost execute hasiruratha.install.make_demo_data`).
2. A local mail catcher so the tests can read the one-time codes:
   `python mailcatch.py` (needs `pip install aiosmtpd`; saves mail to `/opt/mailcatch/mail`), and an
   Email Account on the site with SMTP server `127.0.0.1`, port `1025`, no authentication, default outgoing.
3. Copy `approve.py` and `add_volunteer.py` to `/home/frappe/` (the volunteer test runs them with the bench Python).

Run:

    node citizen.js <screenshot-folder> <a-large-photo.jpg>
    node volunteer.js <screenshot-folder>
    node admin.js <screenshot-folder>      # after running seed_admin.py with the bench Python

Sign-in endpoints are rate limited; clear the local Redis cache between repeated runs.
