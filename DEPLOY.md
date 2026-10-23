# Deploying TechBai on Vercel (free)

**Why not GitHub Pages?** Pages only hosts static files. TechBai needs a backend to store bookings and
block double bookings, so the site runs on Vercel and the bookings live in a free Postgres database.
(Vercel's disk is temporary, so the local `techbai.db` file can't be used there.)

## Steps

1. **Push the project to GitHub** (the repo must contain `vercel.json`, `api/`, `backend/`, `frontend/`).
2. **Create the Vercel project.** Sign in at vercel.com with GitHub, then *Add New > Project* and import the
   TechBai repository. Framework Preset: **Other**. Leave the build settings alone (`vercel.json` sets them).
   Press **Deploy** (the first deploy can't take bookings yet; that's fine).
3. **Add the database.** In the project, open the **Storage** tab, then *Create Database* and choose
   **Neon (Postgres)** on the free plan. Connect it to the project. This adds a `DATABASE_URL`
   environment variable automatically.
4. **Set the admin password.** *Settings > Environment Variables*, add `ADMIN_PASSWORD` with a long password
   (12+ characters, ideally a few random words). Apply it to Production.
5. **Redeploy.** *Deployments >* the latest one *> Redeploy*, because new variables only apply to new deploys.
6. **Test it.** Open your `*.vercel.app` address, make a test booking, find it under *My Booking*, then log in at
   `/admin.html`.

From then on, every `git push` to the main branch redeploys the site automatically.
The tables are created automatically the first time the site runs.

## Changing things later
- **Prices:** edit `backend/services.json`, commit, push.
- **Hours / slots / closed days of the week:** edit `backend/config.py`, commit, push.
- **Holidays:** use the admin page (no redeploy needed).

## Running locally still works
Without `DATABASE_URL` the app uses the local SQLite file, so `python main.py` behaves exactly as before.
To test against the real database from your computer, set `DATABASE_URL` to the Neon connection string first.

## If something goes wrong
- **Pages load but booking says it can't reach the server / error 500:** open *Vercel > your project > Logs*.
  The usual cause is a missing `DATABASE_URL`; check the Storage connection and redeploy.
- **Admin says "Wrong admin password":** `ADMIN_PASSWORD` wasn't set for Production, or you didn't redeploy after setting it.
- **The video or page returns 404:** in *Settings > Build & Output Settings* make sure Output Directory is `frontend`.

## Good to know
- Spam protection is kept in memory, so on Vercel it only works per server instance. It slows casual abuse
  but isn't a hard limit. Check the admin page now and then and cancel junk bookings.
- Back up your bookings from time to time (Neon's dashboard can export the database).
- The free tiers have usage limits, which a small shop is very unlikely to reach.
