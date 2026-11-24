# job-scout template

A daily job scout for senior tech roles in Israel, built with [Claude Code](https://claude.com/claude-code). Every morning a scheduled Claude routine reads public job sources, scores new roles against your profile, keeps a shortlist, and sends the good ones to your phone on Telegram.

It only reads. It never applies, signs in, signs up, or sends anything on your behalf.

## What it reads
- 14 VC job boards on Getro (Israel filter), Team8, Drushim, AllJobs, startupjobs.co.il, Secret Tel Aviv, and Hacker News "Who is hiring" (Israel posts), through `collect.py` (Python standard library only, no logins).
- LinkedIn job pages, found through web search, plus your LinkedIn job-alert emails in Gmail (read only).
- A funding radar: Israeli startups that just raised and have no technical leader named, as outreach ideas.
- GotFriends executive listings (they block cloud servers, so a small job on your own computer can fetch them).

## Set it up
1. Install [Claude Code](https://claude.com/claude-code).
2. Open Claude Code in an empty folder and paste the whole of [PROMPT.md](PROMPT.md).
3. Answer its questions. It interviews you, writes your `profile.md` (see `profile.example.md`), creates a private repo, wires up Telegram, and schedules the daily run. About an hour, most of it the interview.

Edit `TERMS` and `SENIOR` in `collect.py` if your target roles aren't CTO / VP / Head of R&D level.

## Privacy
Your profile, leads and seen list live in your own private repo. Secrets (the Telegram bot token) go only into GitHub secrets from your own terminal, never into files or chat.

## License
MIT
